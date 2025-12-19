"""
Task utilities for reusable business logic
"""

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import timedelta
import random

from .models import LockTask, OvertimeAction, TaskTimelineEvent, PinnedUser
from store.models import Item
from users.models import Notification


def add_overtime_to_task(task, user, minutes=None):
    """
    为进行中的带锁任务随机加时

    Args:
        task: LockTask instance or task ID
        user: User instance who is adding overtime
        minutes: Optional specific minutes to add, if None will be random based on difficulty

    Returns:
        dict: {
            'success': bool,
            'message': str,
            'overtime_minutes': int,
            'new_end_time': datetime,
            'task': LockTask
        }
    """
    # If task is an ID, get the task object
    if isinstance(task, (str, int)):
        try:
            task = LockTask.objects.get(id=task)
        except LockTask.DoesNotExist:
            return {
                'success': False,
                'message': '任务不存在',
                'overtime_minutes': 0,
                'new_end_time': None,
                'task': None
            }

    # 检查是否是带锁任务
    if task.task_type != 'lock':
        return {
            'success': False,
            'message': '只能为带锁任务加时',
            'overtime_minutes': 0,
            'new_end_time': None,
            'task': task
        }

    # 检查任务状态 - 允许对活跃状态和投票状态的任务加时
    if task.status not in ['active', 'voting']:
        return {
            'success': False,
            'message': '只能为进行中的任务（包括投票期）加时',
            'overtime_minutes': 0,
            'new_end_time': None,
            'task': task
        }

    # 检查是否是自己的任务（不能为自己的任务加时）
    if task.user == user:
        return {
            'success': False,
            'message': '不能为自己的任务加时',
            'overtime_minutes': 0,
            'new_end_time': None,
            'task': task
        }

    # 检查两小时内是否已经为同一个发布者的任务加过时
    two_hours_ago = timezone.now() - timedelta(hours=2)
    recent_overtime = OvertimeAction.objects.filter(
        user=user,
        task_publisher=task.user,
        created_at__gte=two_hours_ago
    ).exists()

    if recent_overtime:
        return {
            'success': False,
            'message': '两小时内只能对同一个发布者的带锁任务随机加时一次',
            'overtime_minutes': 0,
            'new_end_time': None,
            'task': task
        }

    # 检查任务是否可以加时
    # 对于投票状态的任务，只要投票期未结束就可以加时
    if task.status == 'voting':
        if task.voting_end_time and timezone.now() >= task.voting_end_time:
            return {
                'success': False,
                'message': '投票期已结束，无法加时',
                'overtime_minutes': 0,
                'new_end_time': None,
                'task': task
            }

    # 计算加时分钟数
    if minutes is None:
        # 根据难度等级确定加时范围（分钟）
        difficulty_overtime_map = {
            'easy': 10,     # 简单：10分钟
            'normal': 20,   # 普通：20分钟
            'hard': 30,     # 困难：30分钟
            'hell': 60      # 地狱：60分钟
        }

        base_overtime = difficulty_overtime_map.get(task.difficulty, 20)  # 默认20分钟

        # 随机加时（在基础时间的50%-150%之间）
        min_overtime = int(base_overtime * 0.5)
        max_overtime = int(base_overtime * 1.5)
        overtime_minutes = random.randint(min_overtime, max_overtime)
    else:
        # 使用指定的分钟数
        overtime_minutes = max(1, int(minutes))  # 确保至少1分钟

    # 检查任务创建者是否被置顶，如果是则应用10倍加时效果
    is_pinned = PinnedUser.objects.filter(
        pinned_user=task.user,  # 任务创建者被置顶
        is_active=True,
        position__isnull=False  # 必须在活跃位置（不是排队中）
    ).exists()

    original_overtime = overtime_minutes
    if is_pinned:
        overtime_minutes *= 10  # 10倍惩罚效果

    # 记录时间变化前的状态
    previous_end_time = task.end_time

    # 更新任务结束时间
    now = timezone.now()
    if task.end_time:
        # 如果倒计时已经结束，从现在开始加时；否则从原结束时间加时
        if now >= task.end_time:
            # 倒计时已结束，从现在开始延长
            task.end_time = now + timezone.timedelta(minutes=overtime_minutes)
        else:
            # 倒计时未结束，从原结束时间延长
            task.end_time = task.end_time + timezone.timedelta(minutes=overtime_minutes)
    else:
        # 如果没有结束时间，从现在开始加时
        task.end_time = now + timezone.timedelta(minutes=overtime_minutes)

    task.save()

    # 记录加时操作
    OvertimeAction.objects.create(
        task=task,
        user=user,
        task_publisher=task.user,
        overtime_minutes=overtime_minutes
    )

    # 创建时间线事件
    description = f'{user.username} 为任务随机加时 {overtime_minutes} 分钟'
    if is_pinned:
        description += f'（置顶惩罚：{original_overtime}×10）'

    TaskTimelineEvent.objects.create(
        task=task,
        event_type='overtime_added',
        user=user,
        time_change_minutes=overtime_minutes,
        previous_end_time=previous_end_time,
        new_end_time=task.end_time,
        description=description,
        metadata={
            'difficulty': task.difficulty,
            'overtime_minutes': overtime_minutes,
            'original_overtime': original_overtime,
            'is_pinned': is_pinned,
            'pinning_multiplier': 10 if is_pinned else 1,
            'source': 'telegram_bot' if hasattr(user, '_telegram_bot_source') else 'web'
        }
    )

    # 创建加时通知
    notification_extra_data = {
        'overtime_minutes': overtime_minutes,
        'difficulty': task.difficulty,
        'new_end_time': task.end_time.isoformat() if task.end_time else None
    }

    if is_pinned:
        notification_extra_data.update({
            'is_pinned': True,
            'original_overtime': original_overtime,
            'pinning_multiplier': 10
        })

    Notification.create_notification(
        recipient=task.user,
        notification_type='task_overtime_added',
        actor=user,
        related_object_type='task',
        related_object_id=task.id,
        extra_data=notification_extra_data
    )

    return {
        'success': True,
        'message': f'成功为任务加时 {overtime_minutes} 分钟',
        'overtime_minutes': overtime_minutes,
        'new_end_time': task.end_time,
        'task': task
    }


def destroy_task_keys(task, reason="task_ended", user=None, metadata=None):
    """
    销毁任务相关的所有钥匙道具

    Args:
        task: LockTask 实例
        reason: 销毁原因 (task_ended, task_deleted, task_stopped, universal_key_used)
        user: 执行操作的用户 (可选)
        metadata: 额外的元数据 (可选)

    Returns:
        dict: 包含销毁结果的字典
    """
    if task.task_type != 'lock':
        return {
            'success': False,
            'message': '非带锁任务无需销毁钥匙',
            'keys_destroyed': 0
        }

    destroyed_keys = []

    with transaction.atomic():
        # 查找所有与此任务相关的钥匙道具（无论在谁手中）
        task_keys = Item.objects.filter(
            item_type__name='key',
            status='available',
            properties__task_id=str(task.id)
        )

        for key_item in task_keys:
            # 记录钥匙信息
            key_info = {
                'id': str(key_item.id),
                'owner': key_item.owner.username,
                'original_owner': key_item.original_owner.username if key_item.original_owner else None,
                'is_original_owner': key_item.owner == task.user
            }

            # 销毁钥匙
            key_item.status = 'used'
            key_item.used_at = timezone.now()
            key_item.inventory = None  # 从背包中移除
            key_item.save()

            destroyed_keys.append(key_info)

        # 创建时间线事件记录钥匙销毁
        if destroyed_keys:
            event_metadata = {
                'reason': reason,
                'keys_destroyed': len(destroyed_keys),
                'key_details': destroyed_keys
            }

            # 合并额外的元数据
            if metadata:
                event_metadata.update(metadata)

            TaskTimelineEvent.objects.create(
                task=task,
                event_type='task_keys_destroyed',
                user=user,
                description=f'任务钥匙销毁：{reason}，共销毁 {len(destroyed_keys)} 个钥匙',
                metadata=event_metadata
            )

    return {
        'success': True,
        'message': f'成功销毁 {len(destroyed_keys)} 个任务钥匙',
        'keys_destroyed': len(destroyed_keys),
        'destroyed_keys': destroyed_keys
    }