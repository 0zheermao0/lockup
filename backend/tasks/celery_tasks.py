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
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import LockTask, HourlyReward, TaskTimelineEvent, TaskParticipant
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
                        priority='very_low'  # 更低优先级，减少视觉干扰
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