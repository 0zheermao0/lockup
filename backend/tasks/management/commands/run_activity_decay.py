#!/usr/bin/env python3
"""
Django Management Command: Manual Activity Decay Processing

This command manually executes the activity decay processing task for testing
and administrative purposes.

Usage:
    python manage.py run_activity_decay

Author: Claude Code
Created: 2024-12-25
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from users.models import User, ActivityLog
from datetime import timedelta
import logging


class Command(BaseCommand):
    help = '手动执行用户活跃度时间衰减处理'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示将要处理的用户，不实际执行衰减'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='只处理指定用户名的用户'
        )
        parser.add_argument(
            '--days-threshold',
            type=int,
            default=1,
            help='处理最后活跃时间超过指定天数的用户（默认1天）'
        )
        parser.add_argument(
            '--min-activity',
            type=int,
            default=1,
            help='只处理活跃度大于等于指定值的用户（默认1）'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细处理信息'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_user = options['user']
        days_threshold = options['days_threshold']
        min_activity = options['min_activity']
        verbose = options['verbose']

        self.stdout.write(
            self.style.SUCCESS(
                f'开始{"模拟" if dry_run else "执行"}活跃度衰减处理...'
            )
        )

        try:
            # 获取需要处理衰减的用户
            threshold_time = timezone.now() - timedelta(days=days_threshold)

            queryset = User.objects.filter(
                last_active__lt=threshold_time,
                activity_score__gte=min_activity
            )

            # 排除今天已处理过的用户（除非是dry-run）
            if not dry_run:
                queryset = queryset.exclude(
                    last_decay_processed__date=timezone.now().date()
                )

            # 如果指定了特定用户
            if target_user:
                queryset = queryset.filter(username=target_user)
                if not queryset.exists():
                    raise CommandError(f'用户 "{target_user}" 不存在或不满足处理条件')

            users_to_process = queryset.select_related().order_by('-activity_score')

            if not users_to_process:
                self.stdout.write(
                    self.style.WARNING('没有找到需要处理的用户')
                )
                return

            self.stdout.write(
                f'找到 {users_to_process.count()} 个用户需要处理'
            )

            if dry_run:
                self.stdout.write(
                    self.style.WARNING('\n=== 模拟模式 - 不会实际修改数据 ===')
                )

            processed_count = 0
            total_decay = 0
            notifications_sent = 0

            for user in users_to_process:
                try:
                    # 计算衰减
                    old_score = user.activity_score
                    decay_amount = user.calculate_fibonacci_decay()

                    if decay_amount <= 0:
                        if verbose:
                            self.stdout.write(
                                f'  跳过 {user.username}: 无需衰减'
                            )
                        continue

                    new_score = max(0, old_score - decay_amount)
                    actual_decay = old_score - new_score
                    days_inactive = (timezone.now().date() - user.last_active.date()).days

                    if verbose or dry_run:
                        self.stdout.write(
                            f'  {user.username}: '
                            f'{old_score} → {new_score} '
                            f'(衰减 {actual_decay}, 已{days_inactive}天未活跃)'
                        )

                    if not dry_run:
                        # 实际应用衰减
                        with transaction.atomic():
                            user.activity_score = new_score
                            user.last_decay_processed = timezone.now()
                            user.save(update_fields=['activity_score', 'last_decay_processed'])

                            # 记录衰减日志
                            if actual_decay > 0:
                                ActivityLog.objects.create(
                                    user=user,
                                    action_type='time_decay',
                                    points_change=-actual_decay,
                                    new_total=new_score,
                                    metadata={
                                        'days_inactive': days_inactive,
                                        'decay_amount': decay_amount,
                                        'manual_execution': True
                                    }
                                )

                            # 发送通知（仅当衰减较大时）
                            if actual_decay >= 5:
                                from users.models import Notification
                                try:
                                    Notification.create_notification(
                                        recipient=user,
                                        notification_type='activity_decay_warning',
                                        title='活跃度衰减提醒',
                                        message=f'由于{days_inactive}天未活跃，您的活跃度减少了{actual_decay}分',
                                        priority='low'
                                    )
                                    notifications_sent += 1
                                except Exception as e:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f'    发送通知失败: {str(e)}'
                                        )
                                    )

                    processed_count += 1
                    total_decay += actual_decay

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  处理用户 {user.username} 时发生错误: {str(e)}'
                        )
                    )
                    continue

            # 显示处理结果
            self.stdout.write('\n' + '='*50)
            self.stdout.write('处理结果:')
            self.stdout.write(f'  处理用户数: {processed_count}')
            self.stdout.write(f'  总衰减积分: {total_decay}')

            if not dry_run:
                self.stdout.write(f'  发送通知数: {notifications_sent}')
                self.stdout.write(f'  执行时间: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')

            self.stdout.write('='*50)

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS('\n✅ 模拟执行完成! 使用不带 --dry-run 参数来实际执行')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('\n✅ 活跃度衰减处理完成!')
                )

        except Exception as e:
            raise CommandError(f'执行活跃度衰减时发生错误: {str(e)}')