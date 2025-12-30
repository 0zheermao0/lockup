#!/usr/bin/env python3
"""
Event System Celery Tasks

This module contains Celery tasks for the Event System:
- Event scheduling and execution
- Expired effects processing
- Event system health checks

Author: Claude Code
Created: 2024-12-30
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from .models import EventDefinition, EventOccurrence, EventEffect, EventEffectExecution
from .effects import get_effect_executor
from users.models import Notification

logger = logging.getLogger('events.celery_tasks')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def schedule_pending_events(self):
    """调度待执行的事件 - 每分钟运行"""
    try:
        logger.info("Starting event scheduling...")

        with transaction.atomic():
            now = timezone.now()

            # 查找需要调度的事件定义
            active_events = EventDefinition.objects.filter(
                is_active=True,
                schedule_type__in=['interval_hours', 'interval_days']
            )

            scheduled_count = 0

            for event_def in active_events:
                # 检查是否需要创建新的事件发生
                last_occurrence = EventOccurrence.objects.filter(
                    event_definition=event_def
                ).order_by('-scheduled_at').first()

                should_schedule = False
                next_time = now

                if event_def.schedule_type == 'interval_hours':
                    interval = timedelta(hours=event_def.interval_value or 1)
                elif event_def.schedule_type == 'interval_days':
                    interval = timedelta(days=event_def.interval_value or 1)
                else:
                    continue

                if not last_occurrence:
                    should_schedule = True
                else:
                    next_time = last_occurrence.scheduled_at + interval
                    should_schedule = now >= next_time

                if should_schedule:
                    occurrence = EventOccurrence.objects.create(
                        event_definition=event_def,
                        scheduled_at=next_time,
                        trigger_type='scheduled'
                    )
                    scheduled_count += 1
                    logger.info(f"Scheduled event {event_def.name} for {next_time}")

            logger.info(f"Event scheduling completed: {scheduled_count} events scheduled")

            return {
                'status': 'success',
                'scheduled_count': scheduled_count,
                'timestamp': now.isoformat()
            }

    except Exception as exc:
        logger.error(f"Event scheduling failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=min(60 * (2 ** self.request.retries), 300))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_pending_events(self):
    """执行待处理的事件 - 每分钟运行"""
    try:
        logger.info("Starting event execution...")

        with transaction.atomic():
            now = timezone.now()

            # 查找需要执行的事件
            pending_occurrences = EventOccurrence.objects.filter(
                status='pending',
                scheduled_at__lte=now
            ).select_related('event_definition').prefetch_related('event_definition__effects')

            if not pending_occurrences.exists():
                logger.info("No pending events to execute")
                return {
                    'status': 'success',
                    'executed_count': 0,
                    'message': 'No pending events',
                    'timestamp': now.isoformat()
                }

            executed_count = 0

            for occurrence in pending_occurrences:
                try:
                    logger.info(f"Executing event: {occurrence.event_definition.name}")

                    occurrence.status = 'executing'
                    occurrence.started_at = now
                    occurrence.save()

                    # 执行所有效果
                    total_affected = 0
                    execution_log = []

                    effects = occurrence.event_definition.effects.filter(is_active=True).order_by('priority')

                    for effect in effects:
                        effect_result = _execute_single_effect(occurrence, effect)
                        total_affected += effect_result['affected_count']
                        execution_log.append(effect_result)

                    # 更新执行结果
                    occurrence.status = 'completed'
                    occurrence.completed_at = now
                    occurrence.affected_users_count = total_affected
                    occurrence.execution_log = execution_log
                    occurrence.save()

                    # 发送系统通知
                    _send_event_notifications(occurrence)

                    executed_count += 1
                    logger.info(f"Executed event {occurrence.event_definition.name}, affected {total_affected} users")

                except Exception as e:
                    occurrence.status = 'failed'
                    occurrence.error_message = str(e)
                    occurrence.completed_at = now
                    occurrence.save()
                    logger.error(f"Failed to execute event {occurrence.id}: {e}")

            logger.info(f"Event execution completed: {executed_count} events executed")

            return {
                'status': 'success',
                'executed_count': executed_count,
                'timestamp': now.isoformat()
            }

    except Exception as exc:
        logger.error(f"Event execution failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=min(60 * (2 ** self.request.retries), 300))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def trigger_manual_event(self, event_definition_id: str, triggered_by_user_id: int = None):
    """手动触发事件执行"""
    try:
        logger.info(f"Manually triggering event {event_definition_id}")

        with transaction.atomic():
            # 获取事件定义
            try:
                event_def = EventDefinition.objects.get(id=event_definition_id)
            except EventDefinition.DoesNotExist:
                logger.error(f"Event definition {event_definition_id} not found")
                return {
                    'status': 'error',
                    'message': 'Event definition not found'
                }

            # 获取触发用户
            triggered_by = None
            if triggered_by_user_id:
                try:
                    from users.models import User
                    triggered_by = User.objects.get(id=triggered_by_user_id)
                except User.DoesNotExist:
                    pass

            # 创建事件发生记录
            now = timezone.now()
            occurrence = EventOccurrence.objects.create(
                event_definition=event_def,
                scheduled_at=now,
                trigger_type='manual',
                triggered_by=triggered_by
            )

            # 立即执行
            occurrence.status = 'executing'
            occurrence.started_at = now
            occurrence.save()

            total_affected = 0
            execution_log = []

            effects = event_def.effects.filter(is_active=True).order_by('priority')

            for effect in effects:
                effect_result = _execute_single_effect(occurrence, effect)
                total_affected += effect_result['affected_count']
                execution_log.append(effect_result)

            # 更新执行结果
            occurrence.status = 'completed'
            occurrence.completed_at = timezone.now()
            occurrence.affected_users_count = total_affected
            occurrence.execution_log = execution_log
            occurrence.save()

            # 发送系统通知
            _send_event_notifications(occurrence)

            logger.info(f"Manually executed event {event_def.name}, affected {total_affected} users")

            return {
                'status': 'success',
                'event_name': event_def.name,
                'affected_users': total_affected,
                'execution_log': execution_log,
                'timestamp': now.isoformat()
            }

    except Exception as exc:
        logger.error(f"Manual event execution failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=min(60 * (2 ** self.request.retries), 300))


def _execute_single_effect(occurrence, effect):
    """执行单个事件效果"""
    try:
        logger.info(f"Executing effect: {effect.effect_type} for event {occurrence.event_definition.name}")

        executor = get_effect_executor(effect)
        target_users = executor.get_target_users()

        affected_count = 0
        user_results = []

        for user in target_users:
            try:
                execution_data = executor.execute_for_user(user)

                # 记录执行结果
                execution_record = EventEffectExecution.objects.create(
                    occurrence=occurrence,
                    effect=effect,
                    target_user=user,
                    effect_data=execution_data,
                    rollback_data=execution_data if executor.can_rollback() else {}
                )

                # 设置过期时间
                if effect.duration_minutes:
                    execution_record.expires_at = timezone.now() + timedelta(minutes=effect.duration_minutes)
                    execution_record.save()

                affected_count += 1
                user_results.append({
                    'user_id': user.id,
                    'username': user.username,
                    'result': execution_data
                })

            except Exception as e:
                logger.error(f"Failed to execute effect for user {user.id}: {e}")
                user_results.append({
                    'user_id': user.id,
                    'username': user.username,
                    'error': str(e)
                })

        logger.info(f"Effect execution completed: {affected_count}/{len(target_users)} users affected")

        return {
            'effect_type': effect.effect_type,
            'target_type': effect.target_type,
            'affected_count': affected_count,
            'total_targets': len(target_users),
            'user_results': user_results[:10]  # 限制日志大小，只保存前10个结果
        }

    except Exception as e:
        logger.error(f"Effect execution failed: {e}")
        return {
            'effect_type': effect.effect_type,
            'target_type': effect.target_type,
            'error': str(e),
            'affected_count': 0,
            'total_targets': 0
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_expired_effects(self):
    """处理过期的持续效果 - 每小时运行"""
    try:
        logger.info("Starting expired effects processing...")

        with transaction.atomic():
            now = timezone.now()

            # 查找过期的效果执行记录
            expired_executions = EventEffectExecution.objects.filter(
                expires_at__lte=now,
                is_expired=False,
                is_rolled_back=False
            ).select_related('effect', 'target_user')

            if not expired_executions.exists():
                logger.info("No expired effects to process")
                return {
                    'status': 'success',
                    'processed_count': 0,
                    'message': 'No expired effects',
                    'timestamp': now.isoformat()
                }

            processed_count = 0

            for execution in expired_executions:
                try:
                    effect = execution.effect
                    executor = get_effect_executor(effect)

                    if executor.can_rollback():
                        success = executor.rollback_for_user(
                            execution.target_user,
                            execution.rollback_data
                        )

                        if success:
                            execution.is_rolled_back = True
                            execution.rolled_back_at = now

                    execution.is_expired = True
                    execution.save()
                    processed_count += 1

                    logger.debug(f"Processed expired effect for {execution.target_user.username}")

                except Exception as e:
                    logger.error(f"Failed to process expired effect {execution.id}: {e}")

            # 清理过期的持续效果模型
            _cleanup_expired_persistent_effects(now)

            logger.info(f"Expired effects processing completed: {processed_count} effects processed")

            return {
                'status': 'success',
                'processed_count': processed_count,
                'timestamp': now.isoformat()
            }

    except Exception as exc:
        logger.error(f"Expired effects processing failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=min(60 * (2 ** self.request.retries), 300))


def _cleanup_expired_persistent_effects(now):
    """清理过期的持续效果模型"""
    from .models import UserGameEffect, UserCoinsMultiplier

    # 清理过期的游戏效果
    expired_game_effects = UserGameEffect.objects.filter(
        expires_at__lte=now,
        is_active=True
    )
    game_count = expired_game_effects.count()
    expired_game_effects.update(is_active=False)

    # 清理过期的积分倍数
    expired_coins_multipliers = UserCoinsMultiplier.objects.filter(
        expires_at__lte=now,
        is_active=True
    )
    coins_count = expired_coins_multipliers.count()
    expired_coins_multipliers.update(is_active=False)

    if game_count > 0 or coins_count > 0:
        logger.info(f"Cleaned up {game_count} game effects and {coins_count} coins multipliers")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def event_system_health_check(self):
    """事件系统健康检查 - 每5分钟运行"""
    try:
        logger.info("Starting event system health check...")

        now = timezone.now()

        # 统计活跃事件定义数量
        active_events_count = EventDefinition.objects.filter(is_active=True).count()

        # 统计今天的事件执行数量
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_executions = EventOccurrence.objects.filter(
            completed_at__gte=today_start,
            status='completed'
        ).count()

        # 检查是否有长时间未处理的待执行事件
        one_hour_ago = now - timedelta(hours=1)
        stale_events = EventOccurrence.objects.filter(
            status='pending',
            scheduled_at__lt=one_hour_ago
        )

        stale_events_count = stale_events.count()

        # 检查失败的事件
        failed_events_today = EventOccurrence.objects.filter(
            status='failed',
            created_at__gte=today_start
        ).count()

        # 检查过期但未处理的持续效果
        overdue_effects = EventEffectExecution.objects.filter(
            expires_at__lt=now - timedelta(minutes=5),
            is_expired=False
        ).count()

        health_status = 'healthy'
        issues = []

        if stale_events_count > 0:
            health_status = 'warning'
            issues.append(f'{stale_events_count} stale pending events')

        if failed_events_today > 5:  # 允许少量失败
            health_status = 'warning'
            issues.append(f'{failed_events_today} failed events today')

        if overdue_effects > 10:  # 允许少量过期未处理
            health_status = 'warning'
            issues.append(f'{overdue_effects} overdue effects')

        health_report = {
            'status': health_status,
            'timestamp': now.isoformat(),
            'active_events_count': active_events_count,
            'today_executions_count': today_executions,
            'stale_events_count': stale_events_count,
            'failed_events_today': failed_events_today,
            'overdue_effects_count': overdue_effects,
            'issues': issues,
            'stale_events': [
                {
                    'id': str(event.id),
                    'name': event.event_definition.name,
                    'scheduled_at': event.scheduled_at.isoformat()
                }
                for event in stale_events[:5]  # 只返回前5个
            ]
        }

        if health_status == 'warning':
            logger.warning(f"Event system health issues detected: {issues}")
        else:
            logger.info("Event system is healthy")

        return health_report

    except Exception as exc:
        logger.error(f"Event system health check failed: {exc}", exc_info=True)
        return {
            'status': 'error',
            'timestamp': timezone.now().isoformat(),
            'error': str(exc)
        }


def _send_event_notifications(occurrence):
    """发送事件通知"""
    try:
        # 获取受影响的用户（限制数量避免过多通知）
        affected_users = EventEffectExecution.objects.filter(
            occurrence=occurrence
        ).values_list('target_user', flat=True).distinct()[:100]  # 最多100个用户

        notification_count = 0

        for user_id in affected_users:
            try:
                from users.models import User
                user = User.objects.get(id=user_id)

                # 获取该用户受到的具体影响
                user_effects = EventEffectExecution.objects.filter(
                    occurrence=occurrence,
                    target_user=user
                ).select_related('effect')

                # 构建影响描述
                effect_descriptions = []
                for execution in user_effects:
                    effect_data = execution.effect_data
                    effect_type = execution.effect.effect_type

                    if effect_type == 'coins_add':
                        amount = effect_data.get('amount_changed', 0)
                        if amount > 0:
                            effect_descriptions.append(f"获得了 {amount} 积分")
                    elif effect_type == 'coins_subtract':
                        amount = abs(effect_data.get('amount_changed', 0))
                        if amount > 0:
                            effect_descriptions.append(f"失去了 {amount} 积分")
                    elif effect_type == 'item_distribute':
                        item_type = effect_data.get('item_type', '道具')
                        quantity = effect_data.get('quantity', 1)
                        effect_descriptions.append(f"获得了 {quantity} 个 {item_type}")
                    elif effect_type == 'task_freeze_all':
                        frozen_count = effect_data.get('frozen_task_count', 0)
                        if frozen_count > 0:
                            effect_descriptions.append(f"有 {frozen_count} 个任务被冻结")
                    elif effect_type == 'task_unfreeze_all':
                        unfrozen_count = effect_data.get('unfrozen_task_count', 0)
                        if unfrozen_count > 0:
                            effect_descriptions.append(f"有 {unfrozen_count} 个任务被解冻")
                    elif effect_type in ['temporary_coins_multiplier', 'temporary_game_enhancement']:
                        multiplier = effect_data.get('multiplier', 1.0)
                        duration = effect_data.get('duration_minutes', 60)
                        if effect_type == 'temporary_coins_multiplier':
                            effect_descriptions.append(f"获得了 {duration} 分钟的 {multiplier}x 积分倍数")
                        else:
                            effect_descriptions.append(f"获得了 {duration} 分钟的 {multiplier}x 游戏增强")

                # 如果没有具体描述，使用默认描述
                if not effect_descriptions:
                    effect_descriptions.append("受到了系统事件的影响")

                effects_text = "、".join(effect_descriptions)

                # 自定义通知标题和消息
                custom_title = f"系统事件：{occurrence.event_definition.title}"
                custom_message = f"{occurrence.event_definition.description}\n\n你受到的影响：{effects_text}"

                Notification.create_notification(
                    recipient=user,
                    notification_type='system_event_occurred',  # 使用专用的系统事件类型
                    title=custom_title,  # 自定义标题
                    message=custom_message,  # 自定义消息内容
                    actor=None,
                    related_object_type='event_occurrence',
                    related_object_id=occurrence.id,
                    extra_data={
                        'event_title': occurrence.event_definition.title,
                        'event_description': occurrence.event_definition.description,
                        'event_category': occurrence.event_definition.category,
                        'effects_count': occurrence.event_definition.effects.count(),
                        'user_effects': effects_text,  # 添加用户具体影响描述
                        'effects_detail': [exec.effect_data for exec in user_effects]  # 详细效果数据
                    },
                    priority='urgent'  # 事件通知使用紧急优先级
                )

                notification_count += 1

            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")

        logger.info(f"Sent {notification_count} event notifications for {occurrence.event_definition.name}")

    except Exception as e:
        logger.error(f"Failed to send event notifications: {e}")


# 健康检查辅助函数
@shared_task(bind=True)
def debug_event_system(self):
    """调试事件系统状态"""
    try:
        now = timezone.now()

        debug_info = {
            'timestamp': now.isoformat(),
            'active_definitions': EventDefinition.objects.filter(is_active=True).count(),
            'pending_occurrences': EventOccurrence.objects.filter(status='pending').count(),
            'executing_occurrences': EventOccurrence.objects.filter(status='executing').count(),
            'recent_completed': EventOccurrence.objects.filter(
                status='completed',
                completed_at__gte=now - timedelta(hours=24)
            ).count(),
            'recent_failed': EventOccurrence.objects.filter(
                status='failed',
                completed_at__gte=now - timedelta(hours=24)
            ).count(),
            'active_effects': EventEffectExecution.objects.filter(
                expires_at__gt=now,
                is_expired=False,
                is_rolled_back=False
            ).count()
        }

        logger.info(f"Event system debug info: {debug_info}")
        return debug_info

    except Exception as exc:
        logger.error(f"Debug event system failed: {exc}", exc_info=True)
        return {
            'status': 'error',
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }