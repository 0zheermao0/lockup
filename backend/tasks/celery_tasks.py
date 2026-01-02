#!/usr/bin/env python3
"""
Celery Tasks for Lockup Backend

This module contains Celery tasks for asynchronous processing in the Lockup application.
Currently focused on hourly rewards processing for lock tasks.

Author: Claude Code
Created: 2024-12-19
"""

import logging
import math
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import LockTask, HourlyReward, TaskTimelineEvent, TaskParticipant, PinnedUser, TaskDeadlineReminder
from users.models import Notification

# Configure logger for Celery tasks
logger = logging.getLogger('tasks.celery_tasks')

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_hourly_rewards(self):
    """
    处理带锁任务的每小时积分奖励

    这是从 process_rewards.py 中重构的小时奖励处理逻辑，
    转换为 Celery 任务以提供更好的错误处理和重试机制。

    Returns:
        dict: 包含处理结果的字典
    """
    try:
        logger.info("Starting hourly rewards processing...")

        with transaction.atomic():
            now = timezone.now()
            processed_rewards = []

            # 找到所有活跃状态的带锁任务
            active_lock_tasks = LockTask.objects.select_for_update().filter(
                task_type='lock',
                status__in=['active', 'voting']  # 活跃状态和投票期都算活跃
            )

            logger.info(f"Found {active_lock_tasks.count()} active lock tasks to process")

            for task in active_lock_tasks:
                if not task.start_time:
                    continue

                # 计算任务已运行的总时间（小时）
                elapsed_time = now - task.start_time
                elapsed_hours = int(elapsed_time.total_seconds() // 3600)

                if elapsed_hours < 1:
                    # 任务运行不满一小时，跳过
                    continue

                # 检查上次奖励时间
                if task.last_hourly_reward_at:
                    # 如果已经有奖励记录，检查是否需要新的奖励
                    time_since_last_reward = now - task.last_hourly_reward_at
                    hours_since_last_reward = int(time_since_last_reward.total_seconds() // 3600)

                    if hours_since_last_reward < 1:
                        # 距离上次奖励不足一小时，跳过
                        continue

                    # 计算需要补发的奖励小时数
                    next_reward_hour = task.total_hourly_rewards + 1
                else:
                    # 第一次发放奖励，从第1小时开始
                    next_reward_hour = 1

                # 发放所有应该获得但还没有获得的小时奖励
                rewards_to_give = elapsed_hours - task.total_hourly_rewards

                if rewards_to_give > 0:
                    logger.info(f"Processing {rewards_to_give} hourly rewards for task {task.id} (user: {task.user.username})")

                    # 处理每个小时的奖励
                    task_rewards = _process_task_hourly_rewards(
                        task, now, next_reward_hour, rewards_to_give, processed_rewards
                    )

                    # 更新任务的奖励记录
                    task.total_hourly_rewards += rewards_to_give
                    task.last_hourly_reward_at = now
                    task.save()

                    logger.info(f"Completed {rewards_to_give} hourly rewards for {task.user.username}: {task.title}")

        logger.info(f"Successfully processed {len(processed_rewards)} hourly rewards")

        return {
            'status': 'success',
            'processed_count': len(processed_rewards),
            'processed_rewards': processed_rewards,
            'timestamp': now.isoformat()
        }

    except Exception as exc:
        logger.error(f"Hourly rewards processing failed: {exc}", exc_info=True)

        # Retry the task with exponential backoff
        raise self.retry(
            exc=exc,
            countdown=min(60 * (2 ** self.request.retries), 300)  # Max 5 minutes
        )

def _process_task_hourly_rewards(task, now, next_reward_hour, rewards_to_give, processed_rewards):
    """
    处理单个任务的小时奖励

    Args:
        task: LockTask 实例
        now: 当前时间
        next_reward_hour: 下一个奖励小时数
        rewards_to_give: 需要发放的奖励数量
        processed_rewards: 处理结果列表（用于累积结果）
    """
    for hour_num in range(next_reward_hour, next_reward_hour + rewards_to_give):
        try:
            # 给用户增加1积分（coins）
            task.user.coins += 1
            task.user.save()

            # 创建奖励记录
            hourly_reward = HourlyReward.objects.create(
                task=task,
                user=task.user,
                reward_amount=1,
                hour_count=hour_num
            )

            # 记录到时间线
            TaskTimelineEvent.objects.create(
                task=task,
                event_type='hourly_reward',
                user=None,  # 系统事件
                description=f'第{hour_num}小时奖励：{task.user.username}获得1积分',
                metadata={
                    'reward_amount': 1,
                    'hour_count': hour_num,
                    'total_coins': task.user.coins,
                    'auto_processed': True,
                    'processed_by': 'celery_task'
                }
            )

            # 减少通知频率：只在特定小时数时发送批量通知，减轻视觉负担
            should_notify = (
                hour_num == 1 or  # 第一小时
                hour_num % 3 == 0  # 每3小时
            )

            if should_notify:
                # 计算当前批次的奖励总数
                batch_rewards = min(3, hour_num) if hour_num % 3 == 0 else 1

                try:
                    Notification.create_notification(
                        recipient=task.user,
                        notification_type='coins_earned_hourly_batch',
                        actor=None,  # 系统通知
                        related_object_type='task',
                        related_object_id=task.id,
                        extra_data={
                            'task_title': task.title,
                            'current_hour': hour_num,
                            'batch_rewards': batch_rewards,
                            'total_hourly_rewards': task.total_hourly_rewards + 1,
                            'notification_type': 'batched',  # 标记为批量通知
                            'processed_by': 'celery_task'
                        },
                        priority='low'  # 低优先级，减少视觉干扰
                    )
                    logger.info(f"Sent hourly reward notification for task {task.id}, hour {hour_num}")
                except Exception as e:
                    logger.warning(f"Failed to send notification for task {task.id}, hour {hour_num}: {e}")

            processed_rewards.append({
                'task_id': str(task.id),
                'task_title': task.title,
                'user': task.user.username,
                'hour_count': hour_num,
                'reward_amount': 1
            })

            logger.debug(f"Processed hour {hour_num} reward for task {task.id}")

        except Exception as e:
            logger.error(f"Failed to process hour {hour_num} reward for task {task.id}: {e}")
            raise  # Re-raise to trigger transaction rollback

@shared_task(bind=True)
def health_check_hourly_rewards(self):
    """
    小时奖励系统健康检查任务

    检查系统状态和数据一致性

    Returns:
        dict: 健康检查结果
    """
    try:
        logger.info("Starting hourly rewards health check...")

        now = timezone.now()

        # 统计活跃任务数量
        active_tasks_count = LockTask.objects.filter(
            task_type='lock',
            status__in=['active', 'voting']
        ).count()

        # 统计今天发放的奖励数量
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_rewards_count = HourlyReward.objects.filter(
            created_at__gte=today_start
        ).count()

        # 检查是否有长时间未处理的任务
        one_hour_ago = now - timezone.timedelta(hours=1)
        stale_tasks = LockTask.objects.filter(
            task_type='lock',
            status__in=['active', 'voting'],
            start_time__lt=one_hour_ago,
            last_hourly_reward_at__lt=one_hour_ago
        )

        stale_tasks_count = stale_tasks.count()

        health_status = {
            'status': 'healthy' if stale_tasks_count == 0 else 'warning',
            'timestamp': now.isoformat(),
            'active_tasks_count': active_tasks_count,
            'today_rewards_count': today_rewards_count,
            'stale_tasks_count': stale_tasks_count,
            'stale_tasks': [
                {
                    'id': str(task.id),
                    'title': task.title,
                    'user': task.user.username,
                    'start_time': task.start_time.isoformat() if task.start_time else None,
                    'last_reward_at': task.last_hourly_reward_at.isoformat() if task.last_hourly_reward_at else None
                }
                for task in stale_tasks[:5]  # 只返回前5个
            ]
        }

        if stale_tasks_count > 0:
            logger.warning(f"Found {stale_tasks_count} stale tasks that may need attention")
        else:
            logger.info("All tasks are up to date with hourly rewards")

        return health_status

    except Exception as exc:
        logger.error(f"Health check failed: {exc}", exc_info=True)
        return {
            'status': 'error',
            'timestamp': timezone.now().isoformat(),
            'error': str(exc)
        }

@shared_task(bind=True)
def debug_task(self):
    """
    调试任务，用于测试 Celery 设置

    Returns:
        dict: 调试信息
    """
    logger.info(f"Debug task executed with request: {self.request}")

    return {
        'status': 'success',
        'message': 'Celery is working correctly!',
        'task_id': self.request.id,
        'timestamp': timezone.now().isoformat()
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def auto_settle_expired_board_task(self, task_id):
    """
    自动结算过期的任务板任务 - Celery延时任务版本

    Args:
        task_id (str): 任务ID

    Returns:
        dict: 结算结果
    """
    try:
        logger.info(f"Starting auto settlement for task {task_id}")

        with transaction.atomic():
            # 获取任务
            try:
                task = LockTask.objects.select_for_update().get(id=task_id, task_type='board')
            except LockTask.DoesNotExist:
                logger.warning(f"Task {task_id} not found or not a board task")
                return {
                    'status': 'error',
                    'message': 'Task not found or not a board task',
                    'task_id': task_id
                }

            # 检查任务是否需要结算
            current_time = timezone.now()
            if not task.deadline:
                logger.warning(f"Task {task_id} has no deadline set")
                return {
                    'status': 'error',
                    'message': 'Task has no deadline',
                    'task_id': task_id
                }

            if task.deadline > current_time:
                logger.warning(f"Task {task_id} deadline has not passed yet")
                return {
                    'status': 'error',
                    'message': 'Task deadline has not passed',
                    'task_id': task_id,
                    'deadline': task.deadline.isoformat(),
                    'current_time': current_time.isoformat()
                }

            if task.status not in ['taken', 'submitted']:
                logger.warning(f"Task {task_id} is not in a settleable status: {task.status}")
                return {
                    'status': 'error',
                    'message': f'Task is not in a settleable status: {task.status}',
                    'task_id': task_id
                }

            # 执行自动结算
            result = _auto_settle_expired_task_internal(task, current_time)

            logger.info(f"Successfully auto-settled task {task_id}: {result['action']}")
            return {
                'status': 'success',
                'task_id': task_id,
                'settlement_result': result,
                'timestamp': current_time.isoformat()
            }

    except Exception as exc:
        logger.error(f"Auto settlement failed for task {task_id}: {exc}", exc_info=True)

        # Retry the task with exponential backoff
        raise self.retry(
            exc=exc,
            countdown=min(60 * (2 ** self.request.retries), 300)  # Max 5 minutes
        )


@shared_task(bind=True)
def schedule_board_task_auto_settlement(self, task_id, deadline_timestamp):
    """
    调度任务板自动结算 - 在任务创建/接取时调用

    Args:
        task_id (str): 任务ID
        deadline_timestamp (float): deadline的Unix时间戳（UTC时间戳）

    Returns:
        dict: 调度结果
    """
    try:
        # 正确处理时间戳：从UTC时间戳转换为带时区的datetime对象
        deadline_datetime = timezone.datetime.fromtimestamp(deadline_timestamp, tz=timezone.utc)
        current_time = timezone.now()

        # 计算延时时间（秒）
        delay_seconds = (deadline_datetime - current_time).total_seconds()

        logger.info(f"Task {task_id} scheduling: deadline={deadline_datetime}, current={current_time}, delay={delay_seconds}s")

        if delay_seconds <= 0:
            logger.warning(f"Task {task_id} deadline has already passed, executing immediately")
            # 立即执行
            return auto_settle_expired_board_task.delay(task_id).get()

        # 调度延时任务 - 使用UTC时间作为ETA
        eta = deadline_datetime
        result = auto_settle_expired_board_task.apply_async(
            args=[task_id],
            eta=eta
        )

        logger.info(f"Scheduled auto settlement for task {task_id} at {eta} (UTC)")

        return {
            'status': 'scheduled',
            'task_id': task_id,
            'celery_task_id': result.task_id,
            'scheduled_for': eta.isoformat(),
            'delay_seconds': delay_seconds
        }

    except Exception as exc:
        logger.error(f"Failed to schedule auto settlement for task {task_id}: {exc}", exc_info=True)
        return {
            'status': 'error',
            'task_id': task_id,
            'error': str(exc)
        }


def _auto_settle_expired_task_internal(task, current_time):
    """
    内部自动结算逻辑 - 从views.py中的逻辑移植过来

    Args:
        task: LockTask实例
        current_time: 当前时间

    Returns:
        dict: 结算结果
    """
    # 检查是否为多人任务
    is_multi_person = task.max_participants and task.max_participants > 1

    if is_multi_person:
        return _auto_settle_multi_person_expired_task_internal(task, current_time)
    else:
        return _auto_settle_single_person_expired_task_internal(task, current_time)


def _auto_settle_single_person_expired_task_internal(task, current_time):
    """自动结算单人过期任务 - 内部版本"""

    if task.status == 'submitted':
        # 已提交证明但未审核，自动通过
        task.status = 'completed'
        task.completed_at = current_time
        task.save()

        # 给接取者发放奖励
        if task.taker and task.reward:
            task.taker.coins += task.reward
            task.taker.save()

            # 通知接取者
            Notification.create_notification(
                recipient=task.taker,
                notification_type='task_board_approved',
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'reward_amount': task.reward,
                    'auto_approved': True,
                    'reason': 'deadline_expired'
                }
            )

        # 通知发布者
        Notification.create_notification(
            recipient=task.user,
            notification_type='task_board_ended',
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'auto_settled': True,
                'final_status': 'completed',
                'taker_username': task.taker.username if task.taker else None
            }
        )

        # 记录时间线事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='task_completed',
            description=f'任务已到期，已提交证明自动审核通过',
            metadata={
                'auto_settled': True,
                'deadline_expired': True,
                'reward_amount': task.reward,
                'processed_by': 'celery_task'
            }
        )

        return {
            'task_id': str(task.id),
            'action': 'auto_approved',
            'reward_given': task.reward or 0,
            'recipient': task.taker.username if task.taker else None
        }

    elif task.status == 'taken':
        # 已接取但未提交证明，任务失败
        task.status = 'failed'
        task.completed_at = current_time
        task.save()

        # 退还奖励给发布者
        if task.reward:
            task.user.coins += task.reward
            task.user.save()

            # 通知发布者
            Notification.create_notification(
                recipient=task.user,
                notification_type='task_board_ended',
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'auto_settled': True,
                    'final_status': 'failed',
                    'refund_amount': task.reward,
                    'reason': '无人提交完成证明'
                }
            )

        # 通知接取者
        if task.taker:
            Notification.create_notification(
                recipient=task.taker,
                notification_type='task_board_ended',
                related_object_type='task',
                related_object_id=task.id,
                extra_data={
                    'task_title': task.title,
                    'auto_settled': True,
                    'final_status': 'failed',
                    'reason': '未在截止时间前提交完成证明'
                }
            )

        # 记录时间线事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='task_failed',
            description=f'任务已到期，无人提交完成证明，自动标记为失败',
            metadata={
                'auto_settled': True,
                'deadline_expired': True,
                'refund_amount': task.reward,
                'processed_by': 'celery_task'
            }
        )

        return {
            'task_id': str(task.id),
            'action': 'failed_no_submission',
            'refund_amount': task.reward or 0
        }

    return {
        'task_id': str(task.id),
        'action': 'no_action_needed',
        'status': task.status
    }


def _auto_settle_multi_person_expired_task_internal(task, current_time):
    """自动结算多人过期任务 - 内部版本"""

    # 获取所有参与者
    participants = task.participants.all()
    approved_participants = participants.filter(status='approved')
    submitted_participants = participants.filter(status='submitted')

    # 自动审核通过所有已提交的参与者
    auto_approved_count = 0
    for participant in submitted_participants:
        participant.status = 'approved'
        participant.reviewed_at = current_time
        participant.review_comment = '任务到期自动审核通过'
        participant.save()
        auto_approved_count += 1

    # 重新获取已通过审核的参与者（包括新自动通过的）
    all_approved_participants = participants.filter(status='approved')

    if all_approved_participants.count() > 0:
        # 有通过审核的参与者，任务完成
        task.status = 'completed'
        task.completed_at = current_time

        # 分配奖励
        if task.reward:
            reward_per_person = math.ceil(task.reward / all_approved_participants.count())

            for participant in all_approved_participants:
                participant.reward_amount = reward_per_person
                participant.save()

                # 给参与者分配积分
                participant.participant.coins += reward_per_person
                participant.participant.save()

                # 通知参与者
                Notification.create_notification(
                    recipient=participant.participant,
                    notification_type='task_board_approved',
                    related_object_type='task',
                    related_object_id=task.id,
                    extra_data={
                        'task_title': task.title,
                        'reward_amount': reward_per_person,
                        'auto_approved': participant.review_comment == '任务到期自动审核通过'
                    }
                )

        action_msg = f'completed_with_{all_approved_participants.count()}_participants'

        # 记录时间线事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='task_completed',
            description=f'任务已到期，{auto_approved_count}位参与者自动审核通过，任务完成',
            metadata={
                'auto_settled': True,
                'deadline_expired': True,
                'auto_approved_count': auto_approved_count,
                'total_approved': all_approved_participants.count(),
                'reward_distributed': task.reward or 0,
                'processed_by': 'celery_task'
            }
        )

    else:
        # 无人通过审核，任务失败
        task.status = 'failed'
        task.completed_at = current_time

        # 退还奖励给发布者
        if task.reward:
            task.user.coins += task.reward
            task.user.save()

        action_msg = 'failed_no_approved_participants'

        # 记录时间线事件
        TaskTimelineEvent.objects.create(
            task=task,
            event_type='task_failed',
            description=f'任务已到期，无人通过审核，自动标记为失败',
            metadata={
                'auto_settled': True,
                'deadline_expired': True,
                'refund_amount': task.reward,
                'processed_by': 'celery_task'
            }
        )

    task.save()

    # 通知发布者
    Notification.create_notification(
        recipient=task.user,
        notification_type='task_board_ended',
        related_object_type='task',
        related_object_id=task.id,
        extra_data={
            'task_title': task.title,
            'auto_settled': True,
            'final_status': task.status,
            'approved_count': all_approved_participants.count(),
            'total_participants': participants.count()
        }
    )

    # 通知所有未通过审核的参与者
    for participant in participants.exclude(status='approved'):
        Notification.create_notification(
            recipient=participant.participant,
            notification_type='task_board_ended',
            related_object_type='task',
            related_object_id=task.id,
            extra_data={
                'task_title': task.title,
                'auto_settled': True,
                'final_status': task.status,
                'participant_status': participant.status
            }
        )

    return {
        'task_id': str(task.id),
        'action': action_msg,
        'auto_approved_count': auto_approved_count,
        'total_approved': all_approved_participants.count(),
        'reward_distributed': task.reward if task.status == 'completed' else 0,
        'refund_amount': task.reward if task.status == 'failed' else 0
    }


# ============================================================================
# 置顶队列管理 Celery 任务 - Pinning Queue Management Tasks
# ============================================================================

@shared_task(bind=True)
def process_pinning_queue(self):
    """
    定期处理置顶队列，移除过期用户，激活等待中的用户

    This task should be run every minute to ensure timely queue processing
    """
    try:
        logger.info("Starting pinning queue processing...")

        from .pinning_service import PinningQueueManager

        # 更新队列状态
        result = PinningQueueManager.update_queue()

        if result['success']:
            logger.info(f"Pinning queue processed successfully: "
                       f"{result['expired_count']} expired, "
                       f"{len(result['position_changes'])} position changes, "
                       f"{result['active_positions']} active positions, "
                       f"{result['queue_count']} in queue")

            return {
                'status': 'success',
                'expired_count': result['expired_count'],
                'position_changes': result['position_changes'],
                'active_positions': result['active_positions'],
                'queue_count': result['queue_count'],
                'timestamp': timezone.now().isoformat()
            }
        else:
            logger.error(f"Pinning queue processing failed: {result.get('error', 'Unknown error')}")
            return {
                'status': 'error',
                'error': result.get('error', 'Unknown error'),
                'timestamp': timezone.now().isoformat()
            }

    except Exception as exc:
        logger.error(f"Pinning queue processing failed: {exc}", exc_info=True)
        return {
            'status': 'error',
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True)
def expire_pinned_users(self):
    """
    处理过期的置顶用户（备用任务，主要处理在 process_pinning_queue 中完成）

    This is a backup task that specifically handles expiration
    """
    try:
        logger.info("Starting pinned users expiration check...")

        now = timezone.now()

        with transaction.atomic():
            # 查找过期的置顶记录
            expired_pins = PinnedUser.objects.select_for_update().filter(
                is_active=True,
                expires_at__lt=now
            )

            expired_count = 0
            for pin in expired_pins:
                # 设置为非活跃状态
                pin.is_active = False
                pin.position = None
                pin.save()

                # 创建过期事件
                TaskTimelineEvent.objects.create(
                    task=pin.task,
                    event_type='user_unpinned',
                    user=None,  # 系统事件
                    description=f'{pin.pinned_user.username} 的置顶时间已到期',
                    metadata={
                        'expired': True,
                        'duration_minutes': pin.duration_minutes,
                        'pinned_user_id': str(pin.pinned_user.id),
                        'key_holder_id': str(pin.key_holder.id),
                        'expired_at': now.isoformat()
                    }
                )

                # 发送过期通知
                Notification.create_notification(
                    recipient=pin.pinned_user,
                    notification_type='user_unpinned',
                    actor=None,
                    related_object_type='task',
                    related_object_id=pin.task.id,
                    extra_data={
                        'task_title': pin.task.title,
                        'expired': True,
                        'duration_minutes': pin.duration_minutes
                    },
                    priority='low'
                )

                expired_count += 1

        logger.info(f"Expired {expired_count} pinned users")

        return {
            'status': 'success',
            'expired_count': expired_count,
            'timestamp': now.isoformat()
        }

    except Exception as exc:
        logger.error(f"Pinned users expiration failed: {exc}", exc_info=True)
        return {
            'status': 'error',
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True)
def pinning_health_check(self):
    """
    置顶系统健康检查任务

    Checks the health of the pinning system and reports any issues
    """
    try:
        logger.info("Starting pinning system health check...")

        now = timezone.now()

        # 统计当前状态
        active_pins_count = PinnedUser.objects.filter(
            is_active=True,
            position__isnull=False
        ).count()

        queued_pins_count = PinnedUser.objects.filter(
            is_active=True,
            position__isnull=True
        ).count()

        # 检查是否有过期但仍活跃的记录
        overdue_pins = PinnedUser.objects.filter(
            is_active=True,
            expires_at__lt=now - timezone.timedelta(minutes=5)  # 超过5分钟还未处理
        )

        overdue_count = overdue_pins.count()

        # 检查位置分配是否正确
        position_issues = []
        expected_positions = set(range(1, min(active_pins_count + 1, 4)))  # 1, 2, 3
        actual_positions = set(
            PinnedUser.objects.filter(
                is_active=True,
                position__isnull=False
            ).values_list('position', flat=True)
        )

        if expected_positions != actual_positions:
            position_issues.append({
                'issue': 'position_mismatch',
                'expected': list(expected_positions),
                'actual': list(actual_positions)
            })

        # 检查是否有重复位置
        position_counts = {}
        for pin in PinnedUser.objects.filter(is_active=True, position__isnull=False):
            position_counts[pin.position] = position_counts.get(pin.position, 0) + 1

        duplicate_positions = {pos: count for pos, count in position_counts.items() if count > 1}

        if duplicate_positions:
            position_issues.append({
                'issue': 'duplicate_positions',
                'duplicates': duplicate_positions
            })

        # 确定健康状态
        health_status = 'healthy'
        if overdue_count > 0 or position_issues:
            health_status = 'warning'

        health_report = {
            'status': health_status,
            'timestamp': now.isoformat(),
            'active_pins_count': active_pins_count,
            'queued_pins_count': queued_pins_count,
            'overdue_pins_count': overdue_count,
            'position_issues': position_issues,
            'overdue_pins': [
                {
                    'id': str(pin.id),
                    'pinned_user': pin.pinned_user.username,
                    'expires_at': pin.expires_at.isoformat(),
                    'overdue_minutes': (now - pin.expires_at).total_seconds() / 60
                }
                for pin in overdue_pins[:5]  # 只返回前5个
            ]
        }

        if health_status == 'warning':
            logger.warning(f"Pinning system health issues detected: {health_report}")
        else:
            logger.info("Pinning system is healthy")

        return health_report

    except Exception as exc:
        logger.error(f"Pinning health check failed: {exc}", exc_info=True)
        return {
            'status': 'error',
            'timestamp': timezone.now().isoformat(),
            'error': str(exc)
        }


# ============================================================================
# 打卡投票系统 Celery 任务 - Check-in Voting System Tasks
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_checkin_voting_results(self):
    """
    处理所有过期的打卡投票结果（每天凌晨4点执行）

    优化版本：使用小批次处理，避免SQLite数据库锁定问题

    对于每个过期的投票会话：
    - 如果拒绝票 > 通过票：冻结用户活跃任务或标记最近任务失败
    - 如果通过票 >= 拒绝票：将收集的积分平分给通过投票者

    Returns:
        dict: 处理结果
    """
    try:
        import time
        logger.info("Starting check-in voting results processing...")

        now = timezone.now()
        from posts.models import CheckinVotingSession

        # 获取需要处理的会话ID列表（只查询ID，避免锁定）
        pending_session_ids = list(CheckinVotingSession.objects.filter(
            voting_deadline__lte=now,
            is_processed=False
        ).values_list('id', flat=True))

        total_sessions = len(pending_session_ids)
        logger.info(f"Found {total_sessions} voting sessions to process")

        if total_sessions == 0:
            return {
                'status': 'success',
                'processed_count': 0,
                'processed_sessions': [],
                'message': 'No sessions to process',
                'timestamp': now.isoformat()
            }

        # 分批处理，避免长时间锁定数据库
        BATCH_SIZE = 10  # 每批处理10个会话
        processed_sessions = []
        failed_count = 0

        # 分批处理会话
        for i in range(0, total_sessions, BATCH_SIZE):
            batch_ids = pending_session_ids[i:i + BATCH_SIZE]
            batch_number = i // BATCH_SIZE + 1
            total_batches = (total_sessions + BATCH_SIZE - 1) // BATCH_SIZE

            try:
                # 使用独立的事务处理每个批次
                with transaction.atomic():
                    batch_sessions = CheckinVotingSession.objects.select_for_update().filter(
                        id__in=batch_ids,
                        is_processed=False  # 再次检查避免重复处理
                    )

                    for session in batch_sessions:
                        try:
                            result = _process_single_voting_session(session, now)
                            processed_sessions.append(result)
                            logger.debug(f"Processed voting session for post {session.post.id}: {result['result']}")
                        except Exception as e:
                            logger.error(f"Failed to process voting session {session.id}: {e}")
                            failed_count += 1
                            # 继续处理其他会话，不让单个失败影响整体处理
                            processed_sessions.append({
                                'session_id': str(session.id),
                                'post_id': str(session.post.id) if hasattr(session, 'post') else 'unknown',
                                'result': 'error',
                                'error': str(e)
                            })

                logger.info(f"Completed batch {batch_number}/{total_batches}: processed {len(batch_ids)} sessions")

                # 批次间短暂休息，释放数据库锁，让其他操作有机会执行
                if i + BATCH_SIZE < total_sessions:  # 不是最后一批
                    time.sleep(0.1)  # 100ms休息

            except Exception as batch_error:
                logger.error(f"Error processing batch {batch_number}: {batch_error}")
                failed_count += len(batch_ids)
                # 继续处理下一批次，不中断整个流程
                continue

        result = {
            'status': 'success',
            'processed_count': len(processed_sessions),
            'failed_count': failed_count,
            'total_sessions': total_sessions,
            'batches_processed': total_batches,
            'processed_sessions': processed_sessions,
            'timestamp': now.isoformat()
        }

        logger.info(f"Check-in voting results processing completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Check-in voting results processing failed: {exc}", exc_info=True)

        # Retry with longer delay for SQLite
        if self.request.retries < self.max_retries:
            retry_countdown = 60 + (self.request.retries * 60)  # 1min, 2min, 3min
            logger.info(f"Retrying check-in voting results processing in {retry_countdown} seconds")
            raise self.retry(countdown=retry_countdown, exc=exc)

        # Final failure notification
        logger.error("Check-in voting results processing failed after all retries")
        raise exc


def _process_single_voting_session(session, current_time):
    """
    处理单个投票会话的结果

    Args:
        session: CheckinVotingSession实例
        current_time: 当前时间

    Returns:
        dict: 处理结果
    """
    from posts.models import CheckinVote

    post = session.post
    votes = CheckinVote.objects.filter(post=post)

    pass_votes = votes.filter(vote_type='pass')
    reject_votes = votes.filter(vote_type='reject')

    pass_count = pass_votes.count()
    reject_count = reject_votes.count()

    # 判断结果：拒绝票必须大于通过票才算拒绝（不是大于等于）
    if reject_count > pass_count:
        session.result = 'rejected'
        _handle_voting_rejected(post, session, current_time)
        result_action = 'rejected'
    else:
        session.result = 'passed'
        _handle_voting_passed(post, session, pass_votes, current_time)
        result_action = 'passed'

    # 标记会话为已处理
    session.is_processed = True
    session.processed_at = current_time
    session.save()

    return {
        'session_id': str(session.id),
        'post_id': str(post.id),
        'post_author': post.user.username,
        'result': result_action,
        'pass_votes': pass_count,
        'reject_votes': reject_count,
        'total_coins_collected': session.total_coins_collected
    }


def _handle_voting_rejected(post, session, current_time):
    """
    处理投票被拒绝的情况：冻结活跃任务或标记最近任务失败

    Args:
        post: Post实例
        session: CheckinVotingSession实例
        current_time: 当前时间
    """
    from posts.models import CheckinVote

    user = post.user

    # 查找用户的活跃带锁任务
    active_task = LockTask.objects.filter(
        user=user,
        task_type='lock',
        status__in=['active', 'voting']
    ).first()

    if active_task:
        # 有活跃任务，冻结它
        active_task.is_frozen = True
        active_task.frozen_at = current_time
        active_task.frozen_end_time = active_task.end_time
        active_task.save()

        # 创建时间线事件
        TaskTimelineEvent.objects.create(
            task=active_task,
            event_type='task_frozen',
            user=None,  # 系统事件
            description='因打卡投票被拒绝而冻结任务',
            metadata={
                'frozen_by': 'checkin_vote_rejection',
                'post_id': str(post.id),
                'reject_votes': CheckinVote.objects.filter(post=post, vote_type='reject').count(),
                'pass_votes': CheckinVote.objects.filter(post=post, vote_type='pass').count(),
                'total_coins_collected': session.total_coins_collected,
                'processed_by': 'celery_task'
            }
        )

        # 通知用户任务被冻结
        Notification.create_notification(
            recipient=user,
            notification_type='task_frozen_by_vote',
            related_object_type='post',
            related_object_id=post.id,
            extra_data={
                'task_title': active_task.title,
                'task_id': str(active_task.id),
                'post_content_preview': post.content[:50] + '...' if len(post.content) > 50 else post.content
            },
            priority='high'
        )

        logger.info(f"Froze active task {active_task.id} for user {user.username} due to rejected check-in vote")

    else:
        # 没有活跃任务，标记最近的带锁任务为失败
        recent_task = LockTask.objects.filter(
            user=user,
            task_type='lock'
        ).order_by('-created_at').first()

        if recent_task:
            recent_task.status = 'failed'
            recent_task.save()

            # 创建时间线事件
            TaskTimelineEvent.objects.create(
                task=recent_task,
                event_type='task_failed',
                user=None,  # 系统事件
                description='因打卡投票被拒绝而标记任务失败（无活跃任务）',
                metadata={
                    'failed_by': 'checkin_vote_rejection',
                    'post_id': str(post.id),
                    'no_active_task': True,
                    'processed_by': 'celery_task'
                }
            )

            # 通知用户任务失败
            Notification.create_notification(
                recipient=user,
                notification_type='task_failed_by_vote',
                related_object_type='post',
                related_object_id=post.id,
                extra_data={
                    'task_title': recent_task.title,
                    'task_id': str(recent_task.id),
                    'reason': 'no_active_task',
                    'post_content_preview': post.content[:50] + '...' if len(post.content) > 50 else post.content
                },
                priority='high'
            )

            logger.info(f"Marked recent task {recent_task.id} as failed for user {user.username} due to rejected check-in vote")
        else:
            logger.warning(f"User {user.username} has no lock tasks to freeze or fail after rejected check-in vote")

    # 通知动态作者投票被拒绝
    Notification.create_notification(
        recipient=user,
        notification_type='checkin_vote_rejected',
        related_object_type='post',
        related_object_id=post.id,
        extra_data={
            'reject_votes': CheckinVote.objects.filter(post=post, vote_type='reject').count(),
            'pass_votes': CheckinVote.objects.filter(post=post, vote_type='pass').count(),
            'total_coins_collected': session.total_coins_collected,
            'post_content_preview': post.content[:50] + '...' if len(post.content) > 50 else post.content,
            'has_active_task': active_task is not None
        },
        priority='high'
    )


def _handle_voting_passed(post, session, pass_votes, current_time):
    """
    处理投票通过的情况：将全部收集的积分奖励给被投票的用户（打卡者）

    Args:
        post: Post实例
        session: CheckinVotingSession实例
        pass_votes: 通过投票的QuerySet
        current_time: 当前时间
    """
    from posts.models import CheckinVote

    user = post.user
    pass_count = pass_votes.count()

    if session.total_coins_collected > 0:
        # 将全部收集的积分奖励给被投票的用户（打卡者）
        user.coins += session.total_coins_collected
        user.save()

        # 通知被投票用户获得奖励
        Notification.create_notification(
            recipient=user,
            notification_type='checkin_vote_reward',
            related_object_type='post',
            related_object_id=post.id,
            extra_data={
                'reward_amount': session.total_coins_collected,
                'total_pass_votes': pass_count,
                'total_reject_votes': CheckinVote.objects.filter(post=post, vote_type='reject').count(),
                'post_content_preview': post.content[:50] + '...' if len(post.content) > 50 else post.content,
                'reward_reason': 'voting_passed'
            },
            priority='normal'
        )

        logger.info(f"Distributed {session.total_coins_collected} coins to post author {user.username} for passed check-in vote")

        # 通知所有投通过票的用户，投票成功但他们不获得积分奖励
        for vote in pass_votes:
            Notification.create_notification(
                recipient=vote.voter,
                notification_type='checkin_vote_passed_voter',
                related_object_type='post',
                related_object_id=post.id,
                extra_data={
                    'post_author': user.username,
                    'total_coins_rewarded': session.total_coins_collected,
                    'total_pass_votes': pass_count,
                    'post_content_preview': post.content[:50] + '...' if len(post.content) > 50 else post.content
                },
                priority='low'
            )

        logger.info(f"Notified {pass_count} voters about successful voting for post {post.id}")

    # 通知动态作者投票通过
    Notification.create_notification(
        recipient=user,
        notification_type='checkin_vote_passed',
        related_object_type='post',
        related_object_id=post.id,
        extra_data={
            'pass_votes': CheckinVote.objects.filter(post=post, vote_type='pass').count(),
            'reject_votes': CheckinVote.objects.filter(post=post, vote_type='reject').count(),
            'total_coins_distributed': session.total_coins_collected,
            'post_content_preview': post.content[:50] + '...' if len(post.content) > 50 else post.content
        },
        priority='normal'
    )


def _update_strict_mode_verification_codes(current_time):
    """
    为所有活跃的严格模式带锁任务更新验证码

    Args:
        current_time: 当前时间

    Returns:
        dict: 更新结果统计
    """
    try:
        logger.info("Starting daily strict mode verification code update...")

        # 查找所有活跃的严格模式带锁任务
        active_strict_tasks = LockTask.objects.select_for_update().filter(
            task_type='lock',
            status__in=['active', 'voting'],  # 活跃状态和投票期
            strict_mode=True
        )

        updated_count = 0
        updated_tasks = []

        for task in active_strict_tasks:
            old_code = task.strict_code

            # 生成新的验证码
            new_code = _generate_strict_code()
            task.strict_code = new_code
            task.save(update_fields=['strict_code'])

            # 记录时间线事件
            TaskTimelineEvent.objects.create(
                task=task,
                event_type='verification_code_updated',
                user=None,  # 系统事件
                description=f'每日验证码更新：{old_code} → {new_code}',
                metadata={
                    'old_code': old_code,
                    'new_code': new_code,
                    'update_reason': 'daily_auto_update',
                    'update_time': current_time.isoformat(),
                    'processed_by': 'celery_task'
                }
            )

            updated_tasks.append({
                'task_id': str(task.id),
                'task_title': task.title,
                'user': task.user.username,
                'old_code': old_code,
                'new_code': new_code
            })

            updated_count += 1
            logger.info(f"Updated verification code for task {task.id} (user: {task.user.username}): {old_code} → {new_code}")

        result = {
            'status': 'success',
            'updated_count': updated_count,
            'total_active_strict_tasks': active_strict_tasks.count(),
            'updated_tasks': updated_tasks,
            'timestamp': current_time.isoformat()
        }

        logger.info(f"Verification code update completed: {updated_count} tasks updated")
        return result

    except Exception as exc:
        logger.error(f"Verification code update failed: {exc}", exc_info=True)
        return {
            'status': 'error',
            'error': str(exc),
            'timestamp': current_time.isoformat()
        }


def _generate_strict_code():
    """
    生成4位严格模式验证码（格式：字母数字字母数字，如A1B2）

    Returns:
        str: 4位验证码
    """
    import random
    import string
    letters = random.choices(string.ascii_uppercase, k=2)
    digits = random.choices(string.digits, k=2)
    return f"{letters[0]}{digits[0]}{letters[1]}{digits[1]}"


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def process_level_promotions(self):
    """
    Weekly task to process user level promotions
    Runs every Wednesday at 4:30 AM

    优化版本：使用小批次处理，避免SQLite数据库锁定问题
    """
    try:
        logger.info("Starting weekly level promotion task")

        from users.services.level_promotion import LevelPromotionService

        # Process all eligible users with optimized batch processing
        result = LevelPromotionService.bulk_process_level_promotions(batch_size=50)

        logger.info(f"Level promotion task completed successfully: {result}")
        return result

    except Exception as exc:
        logger.error(f"Level promotion task failed: {str(exc)}")

        # Retry with longer delay for SQLite
        if self.request.retries < self.max_retries:
            retry_countdown = 300 + (self.request.retries * 300)  # 5min, 10min, 15min
            logger.info(f"Retrying level promotion task in {retry_countdown} seconds")
            raise self.retry(countdown=retry_countdown, exc=exc)

        # Final failure notification
        logger.error("Level promotion task failed after all retries")
        raise exc


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def auto_freeze_strict_mode_tasks(self):
    """
    Daily task to automatically freeze strict mode lock tasks without check-in posts
    Runs daily at 4:00 AM to check for tasks that need to be frozen

    优化版本：使用小批次处理，避免SQLite数据库锁定问题
    """
    try:
        import time
        logger.info("Starting auto-freeze strict mode tasks check")

        from posts.models import Post
        from datetime import timedelta

        now = timezone.now()
        yesterday_4am = now.replace(hour=4, minute=0, second=0, microsecond=0) - timedelta(days=1)

        # 获取需要检查的严格模式任务ID列表（只查询ID，避免锁定）
        strict_task_ids = list(LockTask.objects.filter(
            task_type='lock',
            status='active',
            strict_mode=True,
            is_frozen=False,
            start_time__lt=yesterday_4am  # Task must have been started before yesterday 4 AM
        ).values_list('id', flat=True))

        total_tasks = len(strict_task_ids)
        logger.info(f"Found {total_tasks} strict mode tasks to check")

        if total_tasks == 0:
            return {
                'status': 'success',
                'total_checked': 0,
                'total_frozen': 0,
                'frozen_tasks': [],
                'message': 'No tasks to check',
                'check_time': now.isoformat(),
                'check_period_start': yesterday_4am.isoformat()
            }

        # 分批处理，避免长时间锁定数据库
        BATCH_SIZE = 20  # 每批处理20个任务
        frozen_tasks = []
        failed_count = 0

        # 分批处理任务
        for i in range(0, total_tasks, BATCH_SIZE):
            batch_ids = strict_task_ids[i:i + BATCH_SIZE]
            batch_number = i // BATCH_SIZE + 1
            total_batches = (total_tasks + BATCH_SIZE - 1) // BATCH_SIZE

            try:
                # 使用独立的事务处理每个批次
                with transaction.atomic():
                    batch_tasks = LockTask.objects.select_for_update().filter(
                        id__in=batch_ids,
                        status='active',  # 再次检查避免状态变化
                        is_frozen=False
                    )

                    for task in batch_tasks:
                        try:
                            # Check if user made any check-in post since yesterday 4 AM
                            checkin_posts = Post.objects.filter(
                                user=task.user,
                                post_type='checkin',
                                created_at__gte=yesterday_4am,
                                created_at__lt=now
                            ).exists()

                            if not checkin_posts:
                                # No check-in post found, auto-freeze the task
                                logger.info(f"Auto-freezing task {task.id} for user {task.user.username} - no check-in post found")

                                # Freeze the task (similar to manual freeze but without key/coin requirements)
                                task.is_frozen = True
                                task.frozen_at = now
                                task.frozen_end_time = task.end_time
                                task.save()

                                # Create timeline event
                                TaskTimelineEvent.objects.create(
                                    task=task,
                                    event_type='task_frozen',
                                    user=None,  # System action
                                    description='系统自动冻结任务（严格模式未打卡）',
                                    metadata={
                                        'action': 'auto_freeze',
                                        'reason': 'strict_mode_no_checkin',
                                        'check_period_start': yesterday_4am.isoformat(),
                                        'check_period_end': now.isoformat(),
                                        'frozen_at': task.frozen_at.isoformat(),
                                        'frozen_end_time': task.frozen_end_time.isoformat() if task.frozen_end_time else None,
                                        'system_action': True
                                    }
                                )

                                # Create notification for user
                                Notification.create_notification(
                                    recipient=task.user,
                                    notification_type='task_frozen_auto_strict',
                                    related_object_type='task',
                                    related_object_id=task.id,
                                    extra_data={
                                        'task_title': task.title,
                                        'task_id': str(task.id),
                                        'freeze_reason': 'strict_mode_no_checkin',
                                        'check_period_hours': 24,
                                        'frozen_at': task.frozen_at.isoformat()
                                    },
                                    priority='high'
                                )

                                frozen_tasks.append({
                                    'task_id': str(task.id),
                                    'task_title': task.title,
                                    'user_id': task.user.id,
                                    'username': task.user.username
                                })
                            else:
                                logger.debug(f"Task {task.id} for user {task.user.username} has check-in post, skipping freeze")

                        except Exception as e:
                            logger.error(f"Failed to process task {task.id}: {e}")
                            failed_count += 1
                            continue

                logger.info(f"Completed batch {batch_number}/{total_batches}: processed {len(batch_ids)} tasks")

                # 批次间短暂休息，释放数据库锁，让其他操作有机会执行
                if i + BATCH_SIZE < total_tasks:  # 不是最后一批
                    time.sleep(0.1)  # 100ms休息

            except Exception as batch_error:
                logger.error(f"Error processing batch {batch_number}: {batch_error}")
                failed_count += len(batch_ids)
                # 继续处理下一批次，不中断整个流程
                continue

        result = {
            'status': 'success',
            'total_checked': total_tasks,
            'total_frozen': len(frozen_tasks),
            'failed_count': failed_count,
            'frozen_tasks': frozen_tasks,
            'batches_processed': total_batches,
            'check_time': now.isoformat(),
            'check_period_start': yesterday_4am.isoformat()
        }

        logger.info(f"Auto-freeze task completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Auto-freeze strict mode tasks failed: {str(exc)}")

        # Retry with longer delay for SQLite
        if self.request.retries < self.max_retries:
            retry_countdown = 300 + (self.request.retries * 300)  # 5min, 10min, 15min
            logger.info(f"Retrying auto-freeze task in {retry_countdown} seconds")
            raise self.retry(countdown=retry_countdown, exc=exc)

        # Final failure notification
        logger.error("Auto-freeze strict mode tasks failed after all retries")
        raise exc


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def process_activity_decay(self):
    """
    处理用户活跃度时间衰减 - 每日凌晨4:45执行

    优化版本：使用小批次处理，避免SQLite数据库锁定问题

    基于用户最后活跃时间，按斐波那契数列衰减活跃度：
    - 1天未活跃: -1分
    - 2天未活跃: -1分
    - 3天未活跃: -2分
    - 4天未活跃: -3分
    - 5天未活跃: -5分
    - 以此类推...

    活跃度不会低于0分。
    """
    try:
        import time
        from users.models import User
        from datetime import timedelta

        logger.info("Starting daily activity decay processing")

        # 获取需要处理衰减的用户ID列表（只查询ID，避免锁定）
        yesterday = timezone.now() - timedelta(days=1)
        eligible_user_ids = list(User.objects.filter(
            last_active__lt=yesterday,
            activity_score__gt=0
        ).exclude(
            last_decay_processed__date=timezone.now().date()
        ).values_list('id', flat=True))

        total_users = len(eligible_user_ids)
        logger.info(f"Found {total_users} users eligible for activity decay")

        if total_users == 0:
            return {
                'processed_users': 0,
                'total_decay_applied': 0,
                'eligible_users': 0,
                'process_time': timezone.now().isoformat()
            }

        # 分批处理，避免长时间锁定数据库
        BATCH_SIZE = 20  # 每批处理20个用户
        processed_count = 0
        total_decay = 0
        failed_count = 0

        # 分批处理用户
        for i in range(0, total_users, BATCH_SIZE):
            batch_ids = eligible_user_ids[i:i + BATCH_SIZE]
            batch_number = i // BATCH_SIZE + 1
            total_batches = (total_users + BATCH_SIZE - 1) // BATCH_SIZE

            try:
                # 使用独立的事务处理每个批次
                with transaction.atomic():
                    batch_users = User.objects.select_for_update().filter(id__in=batch_ids)

                    for user in batch_users:
                        try:
                            old_score = user.activity_score

                            # 应用衰减
                            user.apply_time_decay()

                            if user.activity_score != old_score:
                                processed_count += 1
                                decay_amount = old_score - user.activity_score
                                total_decay += decay_amount

                                logger.debug(f"User {user.username}: {old_score} -> {user.activity_score} (-{decay_amount})")

                        except Exception as user_error:
                            logger.error(f"Error processing user {user.id}: {user_error}")
                            failed_count += 1
                            continue

                logger.info(f"Completed batch {batch_number}/{total_batches}: processed {len(batch_ids)} users")

                # 批次间短暂休息，释放数据库锁，让其他操作有机会执行
                if i + BATCH_SIZE < total_users:  # 不是最后一批
                    time.sleep(0.2)  # 200ms休息

            except Exception as batch_error:
                logger.error(f"Error processing batch {batch_number}: {batch_error}")
                failed_count += len(batch_ids)
                # 继续处理下一批次，不中断整个流程
                continue

        result = {
            'processed_users': processed_count,
            'total_decay_applied': total_decay,
            'eligible_users': total_users,
            'failed_users': failed_count,
            'batches_processed': total_batches,
            'process_time': timezone.now().isoformat()
        }

        logger.info(f"Activity decay processing completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Activity decay processing failed: {str(exc)}")

        # Retry with longer delay for SQLite
        if self.request.retries < self.max_retries:
            retry_countdown = 300 + (self.request.retries * 300)  # 5min, 10min, 15min
            logger.info(f"Retrying activity decay processing in {retry_countdown} seconds")
            raise self.retry(countdown=retry_countdown, exc=exc)

        # Final failure notification
        logger.error("Activity decay processing failed after all retries")
        raise exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_expired_board_tasks(self):
    """
    处理过期的任务板任务自动结算 - 每5分钟执行一次

    查找所有过期但未结算的任务板任务，并自动进行结算：
    - 已提交未审核的参与者自动通过
    - 未提交的参与者标记为失败
    - 发放奖励或退还积分给发布者

    Returns:
        dict: 处理结果
    """
    try:
        logger.info("Starting expired board tasks settlement processing...")

        with transaction.atomic():
            now = timezone.now()

            # 查找所有过期但未结算的任务板任务
            expired_tasks = LockTask.objects.select_for_update().filter(
                task_type='board',
                deadline__isnull=False,
                deadline__lt=now,
                status__in=['open', 'taken', 'submitted']
            ).order_by('deadline')

            if not expired_tasks.exists():
                logger.info("No expired board tasks found that need settlement")
                return {
                    'status': 'success',
                    'processed_count': 0,
                    'message': 'No expired tasks to process',
                    'timestamp': now.isoformat()
                }

            logger.info(f"Found {expired_tasks.count()} expired board tasks to settle")

            settled_tasks = []
            failed_tasks = []

            for task in expired_tasks:
                try:
                    logger.info(f"Processing expired task: {task.title} (ID: {task.id})")

                    # 调用现有的自动结算逻辑
                    result = _auto_settle_expired_task_internal(task, now)

                    settled_tasks.append({
                        'task_id': str(task.id),
                        'task_title': task.title,
                        'action': result.get('action', 'unknown'),
                        'deadline': task.deadline.isoformat(),
                        'settlement_result': result
                    })

                    logger.info(f"Successfully settled task {task.id}: {result.get('action', 'unknown')}")

                except Exception as e:
                    logger.error(f"Failed to settle expired task {task.id}: {e}")
                    failed_tasks.append({
                        'task_id': str(task.id),
                        'task_title': task.title,
                        'error': str(e)
                    })

            result = {
                'status': 'success',
                'processed_count': len(settled_tasks),
                'failed_count': len(failed_tasks),
                'settled_tasks': settled_tasks,
                'failed_tasks': failed_tasks,
                'timestamp': now.isoformat()
            }

            logger.info(f"Expired board tasks settlement completed: {result}")
            return result

    except Exception as exc:
        logger.error(f"Expired board tasks settlement failed: {exc}", exc_info=True)

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_countdown = 2 ** self.request.retries * 60  # 1min, 2min, 4min
            logger.info(f"Retrying expired board tasks settlement in {retry_countdown} seconds")
            raise self.retry(countdown=retry_countdown, exc=exc)

        # Final failure notification
        logger.error("Expired board tasks settlement failed after all retries")
        raise exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_deadline_reminders_8h(self):
    """
    处理8小时截止提醒 - 每30分钟运行
    查找7.5-8.5小时内到期的任务，向未提交参与者发送提醒
    """
    logger.info("Starting 8h deadline reminders processing")

    try:
        with transaction.atomic():
            now = timezone.now()
            start_window = now + timedelta(hours=7.5)
            end_window = now + timedelta(hours=8.5)

            # 查找即将到期的任务板任务
            expiring_tasks = LockTask.objects.filter(
                task_type='board',
                status__in=['taken', 'submitted'],
                deadline__gte=start_window,
                deadline__lte=end_window
            ).select_related('user').prefetch_related('participants__participant')

            logger.info(f"Found {len(expiring_tasks)} tasks expiring between {start_window} and {end_window}")

            reminder_count = 0
            tasks_processed = 0

            for task in expiring_tasks:
                tasks_processed += 1
                logger.info(f"Processing task {task.id} ({task.title}) - deadline: {task.deadline}")

                # 获取未提交的参与者
                unsubmitted_participants = task.participants.filter(
                    status='joined'  # 仅joined状态，未提交
                ).select_related('participant')

                logger.info(f"Task {task.id} has {len(unsubmitted_participants)} unsubmitted participants")

                for participant_obj in unsubmitted_participants:
                    participant_user = participant_obj.participant

                    # 使用get_or_create防止重复提醒
                    reminder, created = TaskDeadlineReminder.objects.get_or_create(
                        task=task,
                        participant=participant_user,
                        reminder_type='8h'
                    )

                    if created:
                        # 计算剩余时间
                        time_remaining = task.deadline - now
                        hours_remaining = int(time_remaining.total_seconds() // 3600)

                        logger.info(f"Sending 8h reminder to {participant_user.username} for task {task.id}")

                        # 创建通知
                        Notification.create_notification(
                            recipient=participant_user,
                            notification_type='task_deadline_reminder_8h',
                            actor=None,  # 系统通知
                            related_object_type='task',
                            related_object_id=task.id,
                            extra_data={
                                'task_title': task.title,
                                'task_id': str(task.id),
                                'deadline': task.deadline.isoformat(),
                                'hours_remaining': hours_remaining,
                                'task_reward': task.reward,
                                'reminder_type': '8h_before_deadline',
                                'participant_status': participant_obj.status
                            },
                            priority='high'
                        )

                        reminder_count += 1
                        logger.info(f"Successfully sent reminder to {participant_user.username}")
                    else:
                        logger.info(f"Reminder already sent to {participant_user.username} for task {task.id}")

            result = {
                'status': 'success',
                'reminders_sent': reminder_count,
                'tasks_processed': tasks_processed,
                'timestamp': now.isoformat()
            }

            logger.info(f"8h deadline reminders processing completed: {result}")
            return result

    except Exception as exc:
        logger.error(f"Failed to process 8h deadline reminders: {exc}", exc_info=True)
        raise self.retry(
            exc=exc,
            countdown=min(60 * (2 ** self.request.retries), 300)
        )