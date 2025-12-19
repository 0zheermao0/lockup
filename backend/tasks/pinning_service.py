"""
置顶队列管理服务
Pinning Queue Management Service

处理钥匙持有者置顶惩罚系统的队列管理逻辑
"""

from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from .models import PinnedUser, LockTask, TaskTimelineEvent
from store.models import Item
import logging

logger = logging.getLogger(__name__)


class PinningQueueManager:
    """置顶队列管理器"""

    MAX_ACTIVE_POSITIONS = 3  # 最多3个活跃置顶位置

    @classmethod
    def add_to_queue(cls, task, key_holder, coins_spent=60, duration_minutes=30):
        """
        添加用户到置顶队列

        Args:
            task: LockTask 实例
            key_holder: 钥匙持有者用户
            coins_spent: 消费的金币数
            duration_minutes: 置顶持续时间（分钟）

        Returns:
            dict: 包含成功状态和相关信息的字典
        """
        try:
            with transaction.atomic():
                # 验证钥匙持有者权限
                if not cls._verify_key_holder(task, key_holder):
                    return {
                        'success': False,
                        'message': '您不是该任务的钥匙持有者',
                        'error_code': 'INVALID_KEY_HOLDER'
                    }

                # 检查用户积分是否足够
                if key_holder.coins < coins_spent:
                    return {
                        'success': False,
                        'message': f'积分不足，需要{coins_spent}积分，当前{key_holder.coins}积分',
                        'error_code': 'INSUFFICIENT_COINS'
                    }

                # 检查是否已经置顶了该用户
                existing_pin = PinnedUser.objects.filter(
                    task=task,
                    pinned_user=task.user,
                    is_active=True
                ).first()

                if existing_pin:
                    return {
                        'success': False,
                        'message': '该用户已被置顶',
                        'error_code': 'ALREADY_PINNED'
                    }

                # 计算过期时间
                now = timezone.now()
                expires_at = now + timezone.timedelta(minutes=duration_minutes)

                # 创建置顶记录
                pinned_user = PinnedUser.objects.create(
                    task=task,
                    pinned_user=task.user,
                    key_holder=key_holder,
                    coins_spent=coins_spent,
                    duration_minutes=duration_minutes,
                    expires_at=expires_at
                )

                # 扣除积分
                key_holder.coins -= coins_spent
                key_holder.save()

                # 更新队列状态
                logger.info(f"Before queue update - pinned_user.position: {pinned_user.position}")
                queue_result = cls.update_queue()

                # 刷新置顶用户对象以获取最新的位置信息
                pinned_user.refresh_from_db()
                logger.info(f"After queue update - pinned_user.position: {pinned_user.position}, queue_result: {queue_result}")

                # 创建时间线事件
                TaskTimelineEvent.objects.create(
                    task=task,
                    event_type='user_pinned',
                    user=key_holder,
                    description=f'{key_holder.username} 消费{coins_spent}积分置顶 {task.user.username}',
                    metadata={
                        'coins_spent': coins_spent,
                        'duration_minutes': duration_minutes,
                        'pinned_user_id': str(task.user.id),
                        'key_holder_id': str(key_holder.id),
                        'queue_position': pinned_user.position
                    }
                )

                return {
                    'success': True,
                    'message': f'成功置顶 {task.user.username}',
                    'pinned_user': pinned_user,
                    'queue_status': queue_result,
                    'position': pinned_user.position
                }

        except Exception as e:
            logger.error(f"Failed to add user to pinning queue: {e}")
            return {
                'success': False,
                'message': '置顶操作失败，请稍后重试',
                'error_code': 'INTERNAL_ERROR'
            }

    @classmethod
    def update_queue(cls):
        """
        更新置顶队列，处理过期和位置分配

        Returns:
            dict: 队列更新结果
        """
        try:
            with transaction.atomic():
                now = timezone.now()

                # 1. 移除过期的置顶记录
                expired_pins = PinnedUser.objects.filter(
                    is_active=True,
                    expires_at__lt=now
                )

                expired_count = 0
                for pin in expired_pins:
                    pin.is_active = False
                    pin.position = None
                    pin.save()

                    # 创建置顶结束事件
                    TaskTimelineEvent.objects.create(
                        task=pin.task,
                        event_type='user_unpinned',
                        user=None,  # 系统事件
                        description=f'{pin.pinned_user.username} 的置顶时间已到期',
                        metadata={
                            'expired': True,
                            'duration_minutes': pin.duration_minutes,
                            'pinned_user_id': str(pin.pinned_user.id),
                            'key_holder_id': str(pin.key_holder.id)
                        }
                    )
                    expired_count += 1

                # 2. 获取所有活跃的置顶记录，按创建时间排序
                active_pins = PinnedUser.objects.filter(
                    is_active=True
                ).order_by('created_at')

                logger.info(f"Active pins count: {active_pins.count()}, MAX_ACTIVE_POSITIONS: {cls.MAX_ACTIVE_POSITIONS}")

                # 3. 重新分配位置
                position_changes = []
                for i, pin in enumerate(active_pins):
                    new_position = i + 1 if i < cls.MAX_ACTIVE_POSITIONS else None
                    old_position = pin.position

                    logger.info(f"Pin {pin.id} - Index: {i}, Old position: {old_position}, New position: {new_position}")

                    if new_position != old_position:
                        pin.position = new_position
                        if new_position is not None and old_position is None:
                            # 从队列中激活
                            pin.activated_at = now
                        pin.save()

                        position_changes.append({
                            'pin_id': str(pin.id),
                            'pinned_user': pin.pinned_user.username,
                            'old_position': old_position,
                            'new_position': new_position
                        })
                        logger.info(f"Position changed for pin {pin.id}: {old_position} -> {new_position}")

                # 4. 获取当前状态
                active_positions = active_pins.filter(position__isnull=False).count()
                queue_count = active_pins.filter(position__isnull=True).count()

                # 5. Log position changes (no timeline event for system-level operations)
                if position_changes:
                    logger.info(f"置顶队列已更新：{len(position_changes)}个位置变更, "
                               f"活跃位置: {active_positions}, 排队: {queue_count}, "
                               f"过期: {expired_count}")
                    for change in position_changes:
                        logger.info(f"位置变更: {change['pinned_user']} "
                                   f"{change['old_position']} -> {change['new_position']}")

                return {
                    'success': True,
                    'expired_count': expired_count,
                    'position_changes': position_changes,
                    'active_positions': active_positions,
                    'queue_count': queue_count
                }

        except Exception as e:
            logger.error(f"Failed to update pinning queue: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @classmethod
    def get_active_pinned_users(cls):
        """
        获取当前活跃的置顶用户（最多3个）

        Returns:
            QuerySet: 当前活跃的置顶用户记录
        """
        return PinnedUser.objects.filter(
            is_active=True,
            position__isnull=False
        ).order_by('position').select_related('pinned_user', 'task', 'key_holder')

    @classmethod
    def get_queue_status(cls):
        """
        获取置顶队列状态

        Returns:
            dict: 队列状态信息
        """
        now = timezone.now()

        # 活跃的置顶用户
        active_pins = cls.get_active_pinned_users()

        # 排队中的用户
        queued_pins = PinnedUser.objects.filter(
            is_active=True,
            position__isnull=True
        ).order_by('created_at').select_related('pinned_user', 'task', 'key_holder')

        return {
            'active_pins': [
                {
                    'id': str(pin.id),
                    'position': pin.position,
                    'pinned_user': {
                        'id': str(pin.pinned_user.id),
                        'username': pin.pinned_user.username
                    },
                    'task': {
                        'id': str(pin.task.id),
                        'title': pin.task.title,
                        'description': pin.task.description,
                        'task_type': pin.task.task_type,
                        'status': pin.task.status,
                        'difficulty': pin.task.difficulty,
                        'unlock_type': pin.task.unlock_type,
                        'duration_type': pin.task.duration_type,
                        'duration_value': pin.task.duration_value,
                        'duration_max': pin.task.duration_max,
                        'start_time': pin.task.start_time.isoformat() if pin.task.start_time else None,
                        'end_time': pin.task.end_time.isoformat() if pin.task.end_time else None,
                        'created_at': pin.task.created_at.isoformat(),
                        'updated_at': pin.task.updated_at.isoformat(),
                        'vote_threshold': pin.task.vote_threshold,
                        'vote_agreement_ratio': pin.task.vote_agreement_ratio,
                        'voting_start_time': pin.task.voting_start_time.isoformat() if pin.task.voting_start_time else None,
                        'voting_end_time': pin.task.voting_end_time.isoformat() if pin.task.voting_end_time else None,
                        'voting_duration': pin.task.voting_duration,
                        'vote_failed_penalty_minutes': pin.task.vote_failed_penalty_minutes,
                        'overtime_multiplier': pin.task.overtime_multiplier,
                        'overtime_duration': pin.task.overtime_duration,
                        'time_display_hidden': pin.task.time_display_hidden,
                        'completion_proof': pin.task.completion_proof,
                    },
                    'key_holder': {
                        'id': str(pin.key_holder.id),
                        'username': pin.key_holder.username
                    },
                    'expires_at': pin.expires_at.isoformat(),
                    'time_remaining': max(0, (pin.expires_at - now).total_seconds())
                }
                for pin in active_pins
            ],
            'queued_pins': [
                {
                    'id': str(pin.id),
                    'pinned_user': {
                        'id': str(pin.pinned_user.id),
                        'username': pin.pinned_user.username
                    },
                    'task': {
                        'id': str(pin.task.id),
                        'title': pin.task.title,
                        'description': pin.task.description,
                        'task_type': pin.task.task_type,
                        'status': pin.task.status,
                        'difficulty': pin.task.difficulty,
                        'unlock_type': pin.task.unlock_type,
                        'duration_type': pin.task.duration_type,
                        'duration_value': pin.task.duration_value,
                        'duration_max': pin.task.duration_max,
                        'start_time': pin.task.start_time.isoformat() if pin.task.start_time else None,
                        'end_time': pin.task.end_time.isoformat() if pin.task.end_time else None,
                        'created_at': pin.task.created_at.isoformat(),
                        'updated_at': pin.task.updated_at.isoformat(),
                        'vote_threshold': pin.task.vote_threshold,
                        'vote_agreement_ratio': pin.task.vote_agreement_ratio,
                        'voting_start_time': pin.task.voting_start_time.isoformat() if pin.task.voting_start_time else None,
                        'voting_end_time': pin.task.voting_end_time.isoformat() if pin.task.voting_end_time else None,
                        'voting_duration': pin.task.voting_duration,
                        'vote_failed_penalty_minutes': pin.task.vote_failed_penalty_minutes,
                        'overtime_multiplier': pin.task.overtime_multiplier,
                        'overtime_duration': pin.task.overtime_duration,
                        'time_display_hidden': pin.task.time_display_hidden,
                        'completion_proof': pin.task.completion_proof,
                    },
                    'key_holder': {
                        'id': str(pin.key_holder.id),
                        'username': pin.key_holder.username
                    },
                    'created_at': pin.created_at.isoformat(),
                    'queue_time': (now - pin.created_at).total_seconds()
                }
                for pin in queued_pins
            ],
            'active_count': len(active_pins),
            'queue_count': len(queued_pins),
            'max_positions': cls.MAX_ACTIVE_POSITIONS
        }

    @classmethod
    def is_user_pinned(cls, user):
        """
        检查用户是否当前被置顶

        Args:
            user: User 实例

        Returns:
            bool: 是否被置顶
        """
        return PinnedUser.objects.filter(
            pinned_user=user,
            is_active=True,
            position__isnull=False
        ).exists()

    @classmethod
    def _verify_key_holder(cls, task, user):
        """
        验证用户是否为任务的钥匙持有者

        Args:
            task: LockTask 实例
            user: User 实例

        Returns:
            bool: 是否为钥匙持有者
        """
        return Item.objects.filter(
            item_type__name='key',
            owner=user,
            status='available',
            properties__task_id=str(task.id)
        ).exists()