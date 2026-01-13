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


def calculate_weighted_vote_counts(task):
    """
    计算带有影响力皇冠效果的加权投票统计

    Args:
        task: LockTask实例

    Returns:
        dict: 包含total_votes和agree_votes的字典，已应用影响力皇冠倍数
    """
    from store.models import UserEffect

    votes = task.votes.all()
    total_weighted_votes = 0
    agree_weighted_votes = 0

    for vote in votes:
        # 检查投票者是否有活跃的影响力皇冠效果
        crown_effect = UserEffect.objects.filter(
            user=vote.voter,
            effect_type='influence_crown',
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()

        # 计算投票权重
        vote_weight = 1
        if crown_effect:
            vote_weight = crown_effect.properties.get('vote_multiplier', 3)

        total_weighted_votes += vote_weight
        if vote.agree:
            agree_weighted_votes += vote_weight

    return {
        'total_votes': total_weighted_votes,
        'agree_votes': agree_weighted_votes
    }


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

    # 检查任务状态 - 允许对活跃状态、投票状态和投票已通过状态的任务加时
    if task.status not in ['active', 'voting', 'voting_passed']:
        return {
            'success': False,
            'message': '只能为进行中的任务（包括投票期和投票已通过）加时',
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

    # 处理投票已通过状态的任务加时
    if task.status == 'voting_passed':
        # 投票已通过的任务被加时后，保持voting_passed状态和投票记录
        # 一次投票通过后，无论被加时多少次，都不需要重新投票
        pass  # 保持状态和投票记录不变

    # 记录时间变化前的状态
    previous_end_time = task.end_time
    previous_frozen_end_time = task.frozen_end_time

    # 更新任务结束时间 - 需要考虑冻结状态
    now = timezone.now()

    if task.is_frozen:
        # 冻结状态：修改 frozen_end_time
        if task.frozen_end_time:
            # 从冻结的结束时间延长
            task.frozen_end_time = task.frozen_end_time + timezone.timedelta(minutes=overtime_minutes)
        else:
            # 如果没有冻结结束时间，使用原结束时间作为基础
            if task.end_time:
                task.frozen_end_time = task.end_time + timezone.timedelta(minutes=overtime_minutes)
            else:
                # 如果都没有，从现在开始加时
                task.frozen_end_time = now + timezone.timedelta(minutes=overtime_minutes)
    else:
        # 非冻结状态：修改 end_time（原有逻辑）
        if task.end_time:
            # 如果倒计时已经结束，从现在开始加时；否则从原结束时间加时
            if now >= task.end_time:
                # 倒计时已结束
                if task.strict_mode:
                    # 严格模式下，加时后任务立即结束
                    task.end_time = now + timezone.timedelta(minutes=overtime_minutes)
                else:
                    # 普通模式下，从原结束时间延长
                    task.end_time = task.end_time + timezone.timedelta(minutes=overtime_minutes)
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
    if task.is_frozen:
        description += '（冻结状态下）'

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
            'is_frozen': task.is_frozen,
            'previous_frozen_end_time': previous_frozen_end_time.isoformat() if previous_frozen_end_time else None,
            'new_frozen_end_time': task.frozen_end_time.isoformat() if task.frozen_end_time else None,
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
        'is_frozen': task.is_frozen,
        'frozen_end_time': task.frozen_end_time,
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


def get_revertible_events(task, rollback_time):
    """
    获取可回退的时间线事件（30分钟内）

    Args:
        task: LockTask 实例
        rollback_time: 回退操作的时间点

    Returns:
        QuerySet: 可回退的 TaskTimelineEvent 对象列表，按时间倒序
    """
    cutoff_time = rollback_time - timedelta(minutes=30)

    # 可回退的事件类型
    revertible_event_types = [
        'time_wheel_increase',      # 时间转盘加时（也包括手动加时）
        'time_wheel_decrease',      # 时间转盘减时（也包括手动减时）
        'overtime_added',           # 他人加时
        'task_frozen',              # 任务冻结
        'task_unfrozen',            # 任务解冻
        'vote_failed',              # 投票失败加时
        'system_freeze',            # 系统冻结（暴雪瓶）
    ]

    # 获取30分钟内的可回退事件，按时间倒序
    events = TaskTimelineEvent.objects.filter(
        task=task,
        event_type__in=revertible_event_types,
        created_at__gte=cutoff_time,
        created_at__lte=rollback_time
    ).order_by('-created_at')

    return events


def get_task_state_at_time(task, target_time):
    """
    获取任务在指定时间点的状态

    Args:
        task: LockTask 实例
        target_time: 目标时间点

    Returns:
        dict: 包含任务状态信息的字典
    """
    from .models import TaskTimelineEvent
    from django.utils import timezone

    # 获取目标时间之前的最后一个状态快照事件
    # 如果没有状态快照，则使用任务创建时的状态

    # 首先尝试从任务创建时的状态开始
    if task.created_at <= target_time:
        # 任务在目标时间之前就存在
        initial_state = {
            'end_time': task.end_time,  # 使用当前结束时间作为基准
            'is_frozen': False,
            'frozen_at': None,
            'frozen_end_time': None
        }

        # 获取目标时间之前的所有事件，按时间正序
        events = TaskTimelineEvent.objects.filter(
            task=task,
            created_at__lte=target_time
        ).order_by('created_at')

        # 逆向计算：从当前状态回推到目标时间的状态
        current_time = timezone.now()

        # 获取目标时间之后的所有可回退事件，按时间倒序
        future_events = TaskTimelineEvent.objects.filter(
            task=task,
            created_at__gt=target_time,
            created_at__lte=current_time,
            event_type__in=[
                'time_wheel_increase',
                'time_wheel_decrease',
                'overtime_added',
                'task_frozen',
                'task_unfrozen',
                'vote_failed',
                'system_freeze'
            ]
        ).order_by('-created_at')

        # 从当前状态开始，逆向应用事件
        result_state = {
            'end_time': task.end_time,
            'is_frozen': task.is_frozen,
            'frozen_at': task.frozen_at,
            'frozen_end_time': task.frozen_end_time
        }

        # 逆向应用每个事件
        for event in future_events:
            result_state = _reverse_apply_event(result_state, event)

        return result_state
    else:
        # 任务在目标时间之后才创建，返回None表示任务不存在
        return None


def _reverse_apply_event(state, event):
    """
    逆向应用单个事件到状态

    Args:
        state: 当前状态字典
        event: TaskTimelineEvent 实例

    Returns:
        dict: 应用事件后的状态
    """
    metadata = event.metadata or {}

    if event.event_type in ['time_wheel_increase', 'overtime_added']:
        # 逆向加时：减去之前增加的时间
        if event.time_change_minutes:
            time_delta = timedelta(minutes=event.time_change_minutes)

            if state['is_frozen'] and state['frozen_end_time']:
                state['frozen_end_time'] = state['frozen_end_time'] - time_delta
            elif state['end_time']:
                state['end_time'] = state['end_time'] - time_delta

    elif event.event_type == 'time_wheel_decrease':
        # 逆向减时：加回之前减少的时间
        if event.time_change_minutes:
            time_delta = timedelta(minutes=abs(event.time_change_minutes))

            if state['is_frozen'] and state['frozen_end_time']:
                state['frozen_end_time'] = state['frozen_end_time'] + time_delta
            elif state['end_time']:
                state['end_time'] = state['end_time'] + time_delta

    elif event.event_type == 'task_frozen':
        # 逆向冻结：恢复到未冻结状态
        state['is_frozen'] = False
        state['frozen_at'] = None
        state['frozen_end_time'] = None

    elif event.event_type == 'task_unfrozen':
        # 逆向解冻：恢复到冻结状态
        state['is_frozen'] = True
        if 'frozen_at' in metadata:
            try:
                from datetime import datetime
                state['frozen_at'] = datetime.fromisoformat(metadata['frozen_at'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                state['frozen_at'] = None

        if 'frozen_end_time' in metadata:
            try:
                from datetime import datetime
                state['frozen_end_time'] = datetime.fromisoformat(metadata['frozen_end_time'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                state['frozen_end_time'] = None

    elif event.event_type == 'vote_failed':
        # 逆向投票失败加时：减去失败惩罚时间
        if event.time_change_minutes:
            time_delta = timedelta(minutes=event.time_change_minutes)

            if state['is_frozen'] and state['frozen_end_time']:
                state['frozen_end_time'] = state['frozen_end_time'] - time_delta
            elif state['end_time']:
                state['end_time'] = state['end_time'] - time_delta

    return state


def calculate_rollback_state(task, events_to_revert):
    """
    计算回退后的任务状态

    Args:
        task: LockTask 实例
        events_to_revert: 需要回退的 TaskTimelineEvent 对象列表

    Returns:
        dict: 回退后的状态信息
    """
    # 从当前状态开始，逆向应用每个事件的反向操作
    current_end_time = task.end_time
    current_is_frozen = task.is_frozen
    current_frozen_at = task.frozen_at
    current_frozen_end_time = task.frozen_end_time

    for event in events_to_revert:
        metadata = event.metadata or {}

        if event.event_type in ['time_wheel_increase', 'overtime_added']:
            # 回退加时：减去之前增加的时间
            if event.time_change_minutes:
                time_delta = timedelta(minutes=event.time_change_minutes)

                if current_is_frozen and current_frozen_end_time:
                    current_frozen_end_time = current_frozen_end_time - time_delta
                elif current_end_time:
                    current_end_time = current_end_time - time_delta

        elif event.event_type == 'time_wheel_decrease':
            # 回退减时：加回之前减少的时间
            if event.time_change_minutes:
                # time_change_minutes 对于减时是负数，所以要取绝对值
                time_delta = timedelta(minutes=abs(event.time_change_minutes))

                if current_is_frozen and current_frozen_end_time:
                    current_frozen_end_time = current_frozen_end_time + time_delta
                elif current_end_time:
                    current_end_time = current_end_time + time_delta

        elif event.event_type == 'task_frozen':
            # 回退冻结：恢复到未冻结状态
            current_is_frozen = False
            current_frozen_at = None
            current_frozen_end_time = None

        elif event.event_type in ['task_unfrozen', 'system_freeze']:
            # 回退解冻或系统冻结：恢复到冻结状态
            current_is_frozen = True

            # 从元数据中恢复冻结状态信息
            if 'frozen_at' in metadata:
                try:
                    from datetime import datetime
                    current_frozen_at = datetime.fromisoformat(metadata['frozen_at'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    current_frozen_at = None

            if 'frozen_end_time' in metadata:
                try:
                    from datetime import datetime
                    current_frozen_end_time = datetime.fromisoformat(metadata['frozen_end_time'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    current_frozen_end_time = None

        elif event.event_type == 'vote_failed':
            # 回退投票失败加时：减去失败惩罚时间
            if event.time_change_minutes:
                time_delta = timedelta(minutes=event.time_change_minutes)

                if current_is_frozen and current_frozen_end_time:
                    current_frozen_end_time = current_frozen_end_time - time_delta
                elif current_end_time:
                    current_end_time = current_end_time - time_delta

    return {
        'end_time': current_end_time,
        'is_frozen': current_is_frozen,
        'frozen_at': current_frozen_at,
        'frozen_end_time': current_frozen_end_time
    }


def calculate_penalty_overtime(task, user):
    """
    计算时间隐藏违规的惩罚性加时时长

    Args:
        task: LockTask 实例
        user: 违规用户

    Returns:
        int: 惩罚加时分钟数
    """
    from .models import TaskViolationAttempt
    from django.conf import settings

    # 获取配置参数
    violation_settings = getattr(settings, 'HIDDEN_TIME_VIOLATION_SETTINGS', {})
    base_penalty = violation_settings.get('BASE_PENALTY_MINUTES', 30)
    max_penalty = violation_settings.get('MAX_PENALTY_MINUTES', 180)
    violation_multiplier_factor = violation_settings.get('VIOLATION_MULTIPLIER', 0.5)
    time_ratio_factor = violation_settings.get('TIME_RATIO_FACTOR', 0.2)
    max_violation_multiplier = violation_settings.get('MAX_VIOLATION_MULTIPLIER', 2.0)
    max_time_ratio_penalty = violation_settings.get('MAX_TIME_RATIO_PENALTY', 60)

    # 检查是否启用惩罚机制
    if not violation_settings.get('ENABLE_PENALTY', True):
        return 0

    # 获取该用户对此任务的历史违规次数
    violation_count = TaskViolationAttempt.objects.filter(
        task=task,
        user=user,
        violation_type='premature_completion_hidden_time'
    ).count()

    # 计算剩余时间（分钟）
    remaining_seconds = (task.end_time - timezone.now()).total_seconds()
    remaining_minutes = max(1, int(remaining_seconds / 60))

    # 递增惩罚公式：基础惩罚 + 违规次数加成 + 剩余时间比例
    violation_multiplier = min(violation_count * violation_multiplier_factor, max_violation_multiplier)
    time_ratio_penalty = min(remaining_minutes * time_ratio_factor, max_time_ratio_penalty)

    total_penalty = int(base_penalty * (1 + violation_multiplier) + time_ratio_penalty)

    # 限制惩罚上限，避免过度惩罚
    return min(total_penalty, max_penalty)


def apply_penalty_overtime(task, user, penalty_minutes):
    """
    应用惩罚性加时

    Args:
        task: LockTask 实例
        user: 违规用户
        penalty_minutes: 惩罚加时分钟数
    """
    # 记录时间变化前的状态
    old_end_time = task.end_time
    old_frozen_end_time = task.frozen_end_time

    # 应用惩罚加时 - 需要考虑冻结状态
    if task.is_frozen:
        # 冻结状态：修改 frozen_end_time
        if task.frozen_end_time:
            task.frozen_end_time += timedelta(minutes=penalty_minutes)
        else:
            # 如果没有冻结结束时间，使用原结束时间作为基础
            if task.end_time:
                task.frozen_end_time = task.end_time + timedelta(minutes=penalty_minutes)
            else:
                # 如果都没有，从现在开始加时
                task.frozen_end_time = timezone.now() + timedelta(minutes=penalty_minutes)
    else:
        # 非冻结状态：修改 end_time
        task.end_time += timedelta(minutes=penalty_minutes)

    task.save(update_fields=['end_time', 'frozen_end_time'])

    # 创建时间线事件
    TaskTimelineEvent.objects.create(
        task=task,
        event_type='overtime_added',  # 使用现有的加时事件类型
        user=user,
        time_change_minutes=penalty_minutes,
        previous_end_time=old_end_time,
        new_end_time=task.end_time,
        description=f'{user.username} 违规尝试提前完成任务，系统自动加时 {penalty_minutes} 分钟作为惩罚',
        metadata={
            'penalty_type': 'hidden_time_violation',
            'automatic': True,
            'penalty_minutes': penalty_minutes,
            'is_frozen': task.is_frozen,
            'previous_frozen_end_time': old_frozen_end_time.isoformat() if old_frozen_end_time else None,
            'new_frozen_end_time': task.frozen_end_time.isoformat() if task.frozen_end_time else None,
        }
    )


def record_violation_attempt(task, user, violation_type, request=None):
    """
    记录违规尝试

    Args:
        task: LockTask 实例
        user: 违规用户
        violation_type: 违规类型
        request: HTTP请求对象（可选，用于获取IP和User-Agent）

    Returns:
        TaskViolationAttempt: 创建的违规记录实例或None（如果日志记录被禁用）
    """
    from .models import TaskViolationAttempt
    from django.conf import settings

    # 获取配置参数
    violation_settings = getattr(settings, 'HIDDEN_TIME_VIOLATION_SETTINGS', {})

    # 检查是否启用违规日志记录
    if not violation_settings.get('LOG_VIOLATIONS', True):
        return None

    time_remaining = (task.end_time - timezone.now()).total_seconds()

    # 获取用户IP和User-Agent
    user_ip = None
    user_agent = None
    if request:
        user_ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

    # 计算将要应用的惩罚时间
    penalty_minutes = calculate_penalty_overtime(task, user)

    violation_record = TaskViolationAttempt.objects.create(
        task=task,
        user=user,
        violation_type=violation_type,
        actual_end_time=task.end_time,
        attempted_completion_time=timezone.now(),
        time_remaining_seconds=int(time_remaining),
        penalty_applied=violation_settings.get('ENABLE_PENALTY', True),
        penalty_minutes=penalty_minutes if violation_settings.get('ENABLE_PENALTY', True) else 0,
        user_ip=user_ip,
        user_agent=user_agent,
        metadata={
            'task_status': task.status,
            'time_display_hidden': task.time_display_hidden,
            'is_frozen': task.is_frozen,
            'violation_count_before': TaskViolationAttempt.objects.filter(
                task=task, user=user, violation_type=violation_type
            ).count(),
            'settings_used': {
                'base_penalty': violation_settings.get('BASE_PENALTY_MINUTES', 30),
                'max_penalty': violation_settings.get('MAX_PENALTY_MINUTES', 180),
                'violation_multiplier': violation_settings.get('VIOLATION_MULTIPLIER', 0.5),
                'penalty_enabled': violation_settings.get('ENABLE_PENALTY', True)
            }
        }
    )

    return violation_record


def get_client_ip(request):
    """
    获取客户端真实IP地址

    Args:
        request: HTTP请求对象

    Returns:
        str: 客户端IP地址
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip