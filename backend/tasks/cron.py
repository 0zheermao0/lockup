"""
临时开锁超时检测定时任务
"""
from django.utils import timezone
from datetime import timedelta
from .models import TemporaryUnlockRecord, LockTask, PinnedUser, TaskTimelineEvent
from users.models import Notification


def check_temporary_unlock_timeouts():
    """检查临时开锁超时"""
    # 获取所有超时的记录
    timeout_records = TemporaryUnlockRecord.objects.filter(
        status='active',
        max_end_time__lt=timezone.now()
    )

    for record in timeout_records:
        task = record.task

        # 标记为超时
        record.status = 'timeout'
        record.ended_at = timezone.now()
        record.penalty_applied = True
        record.save()

        # 解冻任务并调整时间
        # 优先使用 task.frozen_end_time 以获取最新的时间（包含加时）
        original_end_time = task.frozen_end_time or record.task_frozen_end_time or task.end_time
        frozen_duration = record.ended_at - record.started_at
        new_end_time = original_end_time + frozen_duration

        # 手动解冻并设置新的结束时间
        if task.is_frozen:
            task.is_frozen = False
            task.total_frozen_duration += frozen_duration
            task.frozen_at = None
            task.frozen_end_time = None

        task.end_time = new_end_time
        task.save(update_fields=[
            'is_frozen', 'end_time', 'total_frozen_duration',
            'frozen_at', 'frozen_end_time'
        ])

        # 创建时间线事件 - 临时开锁超时
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='temporary_unlock_timeout',
            user=None,  # 系统事件
            description=f'临时开锁超时自动结束，持续 {record.duration_minutes} 分钟，已应用30分钟置顶惩罚',
            metadata={
                'record_id': str(record.id),
                'duration_minutes': record.duration_minutes,
                'max_duration': task.temporary_unlock_max_duration,
                'penalty_minutes': 30,
                'timeout_at': timezone.now().isoformat()
            }
        )

        # 创建时间线事件 - 任务解冻
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='task_unfrozen',
            user=None,  # 系统事件
            description='临时开锁超时，任务恢复计时',
            metadata={
                'reason': 'temporary_unlock_timeout',
                'unfrozen_at': timezone.now().isoformat(),
                'frozen_duration_minutes': int(frozen_duration.total_seconds() / 60)
            }
        )

        # 创建时间线事件 - 用户被置顶（惩罚）
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='user_pinned',
            user=None,  # 系统事件
            description='临时开锁超时惩罚：用户被系统自动置顶30分钟',
            metadata={
                'reason': 'temporary_unlock_timeout_penalty',
                'duration_minutes': 30,
                'is_system_action': True
            }
        )

        # 自动置顶惩罚（30分钟）
        pin_end_time = timezone.now() + timedelta(minutes=30)

        PinnedUser.objects.create(
            task=task,
            pinned_user=task.user,
            key_holder=None,  # 系统自动置顶
            duration_minutes=30,
            is_active=True,
            position=None,  # 加入队列
            expires_at=pin_end_time
        )

        # 发送通知
        Notification.create_notification(
            recipient=record.user,
            notification_type='temporary_unlock_timeout',
            title='临时开锁已超时',
            message=f'任务《{task.title}》的临时开锁已超时，已自动结束并应用30分钟置顶惩罚',
            related_object_type='temporary_unlock',
            related_object_id=str(record.id),
            extra_data={
                'task_id': str(task.id),
                'task_title': task.title,
                'penalty_minutes': 30,
            },
            priority='high'
        )

    return len(timeout_records)
