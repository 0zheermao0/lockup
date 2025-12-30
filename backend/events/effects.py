#!/usr/bin/env python3
"""
Event Effect Execution Engine

This module contains the effect execution engine for the Event System.
It provides a plugin-based architecture for executing different types of event effects.

Author: Claude Code
Created: 2024-12-30
"""

import logging
import math
from abc import ABC, abstractmethod
from typing import Dict, List, Any, TYPE_CHECKING
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser as User
else:
    User = get_user_model()

logger = logging.getLogger('events.effects')


class BaseEffectExecutor(ABC):
    """事件效果执行器基类"""

    def __init__(self, effect: 'EventEffect'):
        self.effect = effect

    @abstractmethod
    def get_target_users(self) -> List[User]:
        """获取目标用户列表"""
        pass

    @abstractmethod
    def execute_for_user(self, user: User) -> Dict[str, Any]:
        """为单个用户执行效果"""
        pass

    def can_rollback(self) -> bool:
        """是否支持回滚"""
        return False

    def rollback_for_user(self, user: User, execution_data: Dict[str, Any]) -> bool:
        """回滚用户效果"""
        return False

    def _get_target_users_by_type(self) -> List[User]:
        """根据目标类型获取用户列表"""
        User = get_user_model()
        target_type = self.effect.target_type
        target_params = self.effect.target_parameters

        if target_type == 'all_users':
            return list(User.objects.filter(is_active=True))

        elif target_type == 'random_percentage':
            percentage = target_params.get('percentage', 10)
            all_users = User.objects.filter(is_active=True)
            count = int(all_users.count() * percentage / 100)
            return list(all_users.order_by('?')[:count])

        elif target_type == 'level_based':
            levels = target_params.get('levels', [1])
            return list(User.objects.filter(is_active=True, level__in=levels))

        elif target_type == 'active_task_users':
            from tasks.models import LockTask
            active_task_users = LockTask.objects.filter(
                task_type='lock',
                status__in=['active', 'voting']
            ).values_list('user', flat=True).distinct()
            return list(User.objects.filter(id__in=active_task_users, is_active=True))

        elif target_type == 'recent_active_users':
            days = target_params.get('days', 7)
            cutoff_date = timezone.now() - timedelta(days=days)
            return list(User.objects.filter(
                is_active=True,
                last_active__gte=cutoff_date
            ))

        return []


class CoinsEffectExecutor(BaseEffectExecutor):
    """积分效果执行器"""

    def get_target_users(self) -> List[User]:
        return self._get_target_users_by_type()

    def execute_for_user(self, user: User) -> Dict[str, Any]:
        effect_params = self.effect.effect_parameters
        amount = effect_params.get('amount', 0)

        old_coins = user.coins
        if self.effect.effect_type == 'coins_add':
            user.coins += amount
        elif self.effect.effect_type == 'coins_subtract':
            user.coins = max(0, user.coins - amount)

        user.save(update_fields=['coins'])

        # 更新用户活跃度
        user.update_activity(1)

        logger.info(f"Coins effect: {user.username} {old_coins} -> {user.coins} ({amount:+d})")

        return {
            'old_coins': old_coins,
            'new_coins': user.coins,
            'amount_changed': user.coins - old_coins
        }

    def can_rollback(self) -> bool:
        return True

    def rollback_for_user(self, user: User, execution_data: Dict[str, Any]) -> bool:
        old_coins = execution_data.get('old_coins')
        if old_coins is not None:
            user.coins = old_coins
            user.save(update_fields=['coins'])
            logger.info(f"Rolled back coins for {user.username} to {old_coins}")
            return True
        return False


class ItemDistributeEffectExecutor(BaseEffectExecutor):
    """道具分发效果执行器"""

    def get_target_users(self) -> List[User]:
        # 检查背包容量，只返回有空间的用户
        from store.models import Item
        target_users = self._get_target_users_by_type()

        result = []
        for user in target_users:
            current_items = Item.objects.filter(owner=user, status='available').count()
            max_capacity = 20  # 默认背包容量，可以从用户模型获取
            if hasattr(user, 'get_inventory_capacity'):
                max_capacity = user.get_inventory_capacity()

            if current_items < max_capacity:
                result.append(user)

        return result

    def execute_for_user(self, user: User) -> Dict[str, Any]:
        from store.models import Item, ItemType

        effect_params = self.effect.effect_parameters
        item_type_name = effect_params.get('item_type', 'photo_paper')
        quantity = effect_params.get('quantity', 1)

        try:
            item_type = ItemType.objects.get(name=item_type_name)
            created_items = []

            for _ in range(quantity):
                item = Item.objects.create(
                    item_type=item_type,
                    owner=user,
                    original_owner=user,
                    status='available',
                    properties={'source': 'event', 'event_id': str(self.effect.event_definition.id)}
                )
                created_items.append(str(item.id))

            logger.info(f"Distributed {len(created_items)} {item_type_name} to {user.username}")

            return {
                'item_type': item_type_name,
                'quantity': len(created_items),
                'item_ids': created_items
            }
        except ItemType.DoesNotExist:
            logger.error(f"ItemType {item_type_name} not found")
            return {'error': f'ItemType {item_type_name} not found'}

    def can_rollback(self) -> bool:
        return True

    def rollback_for_user(self, user: User, execution_data: Dict[str, Any]) -> bool:
        from store.models import Item

        item_ids = execution_data.get('item_ids', [])
        if item_ids:
            # 删除分发的道具
            deleted_count = Item.objects.filter(
                id__in=item_ids,
                owner=user,
                status='available'
            ).delete()[0]

            logger.info(f"Rolled back {deleted_count} items for {user.username}")
            return deleted_count > 0
        return False


class TaskFreezeEffectExecutor(BaseEffectExecutor):
    """任务冻结效果执行器"""

    def get_target_users(self) -> List[User]:
        # 获取有活跃任务的用户
        User = get_user_model()
        from tasks.models import LockTask

        if self.effect.effect_type == 'task_freeze_all':
            active_task_users = LockTask.objects.filter(
                task_type='lock',
                status__in=['active', 'voting'],
                is_frozen=False
            ).values_list('user', flat=True).distinct()
        else:  # task_unfreeze_all
            active_task_users = LockTask.objects.filter(
                task_type='lock',
                status__in=['active', 'voting'],
                is_frozen=True
            ).values_list('user', flat=True).distinct()

        return list(User.objects.filter(id__in=active_task_users, is_active=True))

    def execute_for_user(self, user: User) -> Dict[str, Any]:
        from tasks.models import LockTask, TaskTimelineEvent

        if self.effect.effect_type == 'task_freeze_all':
            return self._freeze_user_tasks(user)
        elif self.effect.effect_type == 'task_unfreeze_all':
            return self._unfreeze_user_tasks(user)

        return {'error': 'Unknown task effect type'}

    def _freeze_user_tasks(self, user: User) -> Dict[str, Any]:
        from tasks.models import LockTask, TaskTimelineEvent

        active_tasks = LockTask.objects.filter(
            user=user,
            task_type='lock',
            status__in=['active', 'voting'],
            is_frozen=False
        )

        frozen_tasks = []
        for task in active_tasks:
            task.is_frozen = True
            task.frozen_at = timezone.now()
            task.frozen_end_time = task.end_time
            task.save()

            # 记录时间线事件
            TaskTimelineEvent.objects.create(
                task=task,
                event_type='system_freeze',
                description=f'系统事件冻结任务: {self.effect.event_definition.title}',
                metadata={
                    'event_id': str(self.effect.event_definition.id),
                    'frozen_by': 'event_system'
                }
            )

            frozen_tasks.append(str(task.id))

        logger.info(f"Froze {len(frozen_tasks)} tasks for {user.username}")

        return {
            'action': 'freeze',
            'frozen_task_count': len(frozen_tasks),
            'frozen_task_ids': frozen_tasks
        }

    def _unfreeze_user_tasks(self, user: User) -> Dict[str, Any]:
        from tasks.models import LockTask, TaskTimelineEvent

        frozen_tasks = LockTask.objects.filter(
            user=user,
            task_type='lock',
            status__in=['active', 'voting'],
            is_frozen=True
        )

        unfrozen_tasks = []
        for task in frozen_tasks:
            # 计算冻结持续时间
            if task.frozen_at:
                frozen_duration = timezone.now() - task.frozen_at
                task.total_frozen_duration += frozen_duration

            # 恢复任务
            task.is_frozen = False
            if task.frozen_end_time:
                # 延长结束时间
                extension = timezone.now() - task.frozen_at if task.frozen_at else timedelta(0)
                task.end_time = task.frozen_end_time + extension

            task.frozen_at = None
            task.frozen_end_time = None
            task.save()

            # 记录时间线事件
            TaskTimelineEvent.objects.create(
                task=task,
                event_type='task_unfrozen',
                description=f'系统事件解冻任务: {self.effect.event_definition.title}',
                metadata={
                    'event_id': str(self.effect.event_definition.id),
                    'unfrozen_by': 'event_system'
                }
            )

            unfrozen_tasks.append(str(task.id))

        logger.info(f"Unfroze {len(unfrozen_tasks)} tasks for {user.username}")

        return {
            'action': 'unfreeze',
            'unfrozen_task_count': len(unfrozen_tasks),
            'unfrozen_task_ids': unfrozen_tasks
        }

    def can_rollback(self) -> bool:
        return True

    def rollback_for_user(self, user: User, execution_data: Dict[str, Any]) -> bool:
        from tasks.models import LockTask

        action = execution_data.get('action')
        if action == 'freeze':
            # 回滚冻结：解冻任务
            task_ids = execution_data.get('frozen_task_ids', [])
            unfrozen_count = 0
            for task_id in task_ids:
                try:
                    task = LockTask.objects.get(id=task_id, user=user)
                    if task.is_frozen:
                        task.is_frozen = False
                        task.frozen_at = None
                        task.frozen_end_time = None
                        task.save()
                        unfrozen_count += 1
                except LockTask.DoesNotExist:
                    continue

            logger.info(f"Rolled back freeze: unfroze {unfrozen_count} tasks for {user.username}")
            return unfrozen_count > 0

        elif action == 'unfreeze':
            # 回滚解冻：重新冻结任务
            task_ids = execution_data.get('unfrozen_task_ids', [])
            refrozen_count = 0
            for task_id in task_ids:
                try:
                    task = LockTask.objects.get(id=task_id, user=user)
                    if not task.is_frozen:
                        task.is_frozen = True
                        task.frozen_at = timezone.now()
                        task.frozen_end_time = task.end_time
                        task.save()
                        refrozen_count += 1
                except LockTask.DoesNotExist:
                    continue

            logger.info(f"Rolled back unfreeze: refroze {refrozen_count} tasks for {user.username}")
            return refrozen_count > 0

        return False


class TemporaryCoinsMultiplierExecutor(BaseEffectExecutor):
    """临时积分倍数效果执行器"""

    def get_target_users(self) -> List[User]:
        return self._get_target_users_by_type()

    def execute_for_user(self, user: User) -> Dict[str, Any]:
        from .models import UserCoinsMultiplier

        effect_params = self.effect.effect_parameters
        multiplier = effect_params.get('multiplier', 1.5)
        duration_minutes = self.effect.duration_minutes or 60

        expires_at = timezone.now() + timedelta(minutes=duration_minutes)

        # 创建积分倍数记录
        coins_multiplier = UserCoinsMultiplier.objects.create(
            user=user,
            multiplier=multiplier,
            expires_at=expires_at,
            is_active=True
        )

        logger.info(f"Applied coins multiplier x{multiplier} for {user.username} until {expires_at}")

        return {
            'multiplier': multiplier,
            'duration_minutes': duration_minutes,
            'expires_at': expires_at.isoformat(),
            'multiplier_id': str(coins_multiplier.id)
        }

    def can_rollback(self) -> bool:
        return True

    def rollback_for_user(self, user: User, execution_data: Dict[str, Any]) -> bool:
        from .models import UserCoinsMultiplier

        multiplier_id = execution_data.get('multiplier_id')
        if multiplier_id:
            try:
                multiplier = UserCoinsMultiplier.objects.get(id=multiplier_id, user=user)
                multiplier.is_active = False
                multiplier.save()
                logger.info(f"Rolled back coins multiplier for {user.username}")
                return True
            except UserCoinsMultiplier.DoesNotExist:
                pass
        return False


class TemporaryGameEnhancementExecutor(BaseEffectExecutor):
    """临时游戏增强效果执行器"""

    def get_target_users(self) -> List[User]:
        return self._get_target_users_by_type()

    def execute_for_user(self, user: User) -> Dict[str, Any]:
        from .models import UserGameEffect

        effect_params = self.effect.effect_parameters
        multiplier = effect_params.get('multiplier', 2.0)
        effect_type = effect_params.get('effect_type', 'multiplier')
        duration_minutes = self.effect.duration_minutes or 60

        expires_at = timezone.now() + timedelta(minutes=duration_minutes)

        # 创建游戏效果记录
        game_effect = UserGameEffect.objects.create(
            user=user,
            effect_type=effect_type,
            multiplier=multiplier,
            expires_at=expires_at,
            is_active=True
        )

        logger.info(f"Applied game enhancement x{multiplier} for {user.username} until {expires_at}")

        return {
            'effect_type': effect_type,
            'multiplier': multiplier,
            'duration_minutes': duration_minutes,
            'expires_at': expires_at.isoformat(),
            'game_effect_id': str(game_effect.id)
        }

    def can_rollback(self) -> bool:
        return True

    def rollback_for_user(self, user: User, execution_data: Dict[str, Any]) -> bool:
        from .models import UserGameEffect

        game_effect_id = execution_data.get('game_effect_id')
        if game_effect_id:
            try:
                game_effect = UserGameEffect.objects.get(id=game_effect_id, user=user)
                game_effect.is_active = False
                game_effect.save()
                logger.info(f"Rolled back game enhancement for {user.username}")
                return True
            except UserGameEffect.DoesNotExist:
                pass
        return False


class StoreDiscountEffectExecutor(BaseEffectExecutor):
    """商店折扣效果执行器"""

    def get_target_users(self) -> List[User]:
        # 商店折扣是全局效果，返回空列表，在执行时特殊处理
        return []

    def execute_for_user(self, user: User) -> Dict[str, Any]:
        # 商店折扣不针对单个用户，这个方法不会被调用
        # 实际的折扣逻辑会在商店系统中检查全局折扣状态
        return {}

    def execute_global_effect(self) -> Dict[str, Any]:
        """执行全局商店折扣效果"""
        from store.models import StoreItem

        effect_params = self.effect.effect_parameters
        discount_percentage = effect_params.get('discount_percentage', 20)  # 默认8折
        duration_minutes = self.effect.duration_minutes or 60

        # 这里可以设置全局折扣状态，或者修改商店价格
        # 具体实现取决于商店系统的设计

        logger.info(f"Applied global store discount: {discount_percentage}% off for {duration_minutes} minutes")

        return {
            'discount_percentage': discount_percentage,
            'duration_minutes': duration_minutes,
            'affected_items': 'all'
        }


# 效果执行器注册表
EFFECT_EXECUTORS = {
    'coins_add': CoinsEffectExecutor,
    'coins_subtract': CoinsEffectExecutor,
    'item_distribute': ItemDistributeEffectExecutor,
    'item_remove': ItemDistributeEffectExecutor,  # 可以重用，通过参数区分
    'task_freeze_all': TaskFreezeEffectExecutor,
    'task_unfreeze_all': TaskFreezeEffectExecutor,
    'temporary_coins_multiplier': TemporaryCoinsMultiplierExecutor,
    'temporary_game_enhancement': TemporaryGameEnhancementExecutor,
    'store_discount': StoreDiscountEffectExecutor,
    'store_price_increase': StoreDiscountEffectExecutor,  # 可以重用，通过参数区分
}


def get_effect_executor(effect: 'EventEffect') -> BaseEffectExecutor:
    """获取效果执行器实例"""
    executor_class = EFFECT_EXECUTORS.get(effect.effect_type)
    if not executor_class:
        raise ValueError(f"Unknown effect type: {effect.effect_type}")

    return executor_class(effect)


def apply_coins_multiplier(user: User, base_coins: int) -> int:
    """应用积分倍数 - 在现有积分增加函数中调用"""
    from .models import UserCoinsMultiplier

    active_multiplier = UserCoinsMultiplier.objects.filter(
        user=user,
        is_active=True,
        expires_at__gt=timezone.now()
    ).first()

    if active_multiplier and active_multiplier.is_valid:
        multiplied_coins = int(base_coins * active_multiplier.multiplier)
        logger.info(f"Applied coins multiplier for {user.username}: {base_coins} -> {multiplied_coins}")
        return multiplied_coins

    return base_coins


def apply_game_result_modifiers(user: User, base_reward: int) -> int:
    """应用游戏结果修改器 - 在游戏结算函数中调用"""
    from .models import UserGameEffect

    active_effect = UserGameEffect.objects.filter(
        user=user,
        is_active=True,
        expires_at__gt=timezone.now()
    ).first()

    if active_effect and active_effect.is_valid:
        modified_reward = int(base_reward * active_effect.multiplier)
        logger.info(f"Applied game modifier for {user.username}: {base_reward} -> {modified_reward}")
        return modified_reward

    return base_reward