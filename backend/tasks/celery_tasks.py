#!/usr/bin/env python3
"""
Celery Tasks for Lockup Backend

This module contains Celery tasks for asynchronous processing in the Lockup application.
Currently focused on hourly rewards processing for lock tasks.

Author: Claude Code
Created: 2024-12-19
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import LockTask, HourlyReward, TaskTimelineEvent
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