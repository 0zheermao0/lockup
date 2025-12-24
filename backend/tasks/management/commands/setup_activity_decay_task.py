#!/usr/bin/env python3
"""
Django Management Command: Setup Activity Decay Periodic Task

This command creates or updates the periodic task for processing user activity decay
using django-celery-beat's PeriodicTask model.

Usage:
    python manage.py setup_activity_decay_task

Author: Claude Code
Created: 2024-12-25
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


class Command(BaseCommand):
    help = '设置用户活跃度时间衰减的定期任务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hour',
            type=int,
            default=4,
            help='执行时间（小时，0-23），默认为4点'
        )
        parser.add_argument(
            '--minute',
            type=int,
            default=45,
            help='执行时间（分钟，0-59），默认为45分'
        )
        parser.add_argument(
            '--timezone',
            type=str,
            default='Asia/Shanghai',
            help='时区，默认为Asia/Shanghai'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制覆盖已存在的任务'
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='禁用任务而不是启用'
        )

    def handle(self, *args, **options):
        hour = options['hour']
        minute = options['minute']
        timezone_name = options['timezone']
        force = options['force']
        disable = options['disable']

        # 验证时间参数
        if not (0 <= hour <= 23):
            raise CommandError('小时必须在0-23之间')
        if not (0 <= minute <= 59):
            raise CommandError('分钟必须在0-59之间')

        self.stdout.write(
            self.style.SUCCESS(f'开始设置活跃度衰减任务...')
        )

        try:
            # 创建或获取crontab调度
            schedule, created = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_week='*',
                day_of_month='*',
                month_of_year='*',
                timezone=timezone_name,
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'创建新的crontab调度: 每日 {hour:02d}:{minute:02d} ({timezone_name})'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'使用现有crontab调度: 每日 {hour:02d}:{minute:02d} ({timezone_name})'
                    )
                )

            # 定义任务参数
            task_name = 'process-activity-decay'
            task_description = '用户活跃度时间衰减处理'
            task_function = 'tasks.celery_tasks.process_activity_decay'

            # 检查是否已存在任务
            existing_task = PeriodicTask.objects.filter(name=task_name).first()

            if existing_task:
                if not force:
                    self.stdout.write(
                        self.style.WARNING(
                            f'任务 "{task_name}" 已存在。使用 --force 参数来覆盖现有任务。'
                        )
                    )
                    self.stdout.write(
                        f'当前任务状态: {"启用" if existing_task.enabled else "禁用"}'
                    )
                    self.stdout.write(
                        f'当前调度: {existing_task.crontab}'
                    )
                    return

                # 更新现有任务
                existing_task.crontab = schedule
                existing_task.task = task_function
                existing_task.enabled = not disable
                existing_task.description = task_description
                existing_task.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'更新现有任务 "{task_name}": {"启用" if not disable else "禁用"}'
                    )
                )
            else:
                # 创建新任务
                task = PeriodicTask.objects.create(
                    name=task_name,
                    task=task_function,
                    crontab=schedule,
                    enabled=not disable,
                    description=task_description,
                    kwargs=json.dumps({}),  # 空参数
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'创建新任务 "{task_name}": {"启用" if not disable else "禁用"}'
                    )
                )

            # 显示任务详细信息
            final_task = PeriodicTask.objects.get(name=task_name)
            self.stdout.write('\n' + '='*50)
            self.stdout.write('任务详细信息:')
            self.stdout.write(f'  名称: {final_task.name}')
            self.stdout.write(f'  描述: {final_task.description}')
            self.stdout.write(f'  任务函数: {final_task.task}')
            self.stdout.write(f'  调度: 每日 {hour:02d}:{minute:02d} ({timezone_name})')
            self.stdout.write(f'  状态: {"启用" if final_task.enabled else "禁用"}')
            self.stdout.write(f'  创建时间: {final_task.date_changed}')

            # 提供下次运行时间预估
            if final_task.enabled:
                from django_celery_beat.utils import is_aware
                from datetime import datetime, time
                import pytz

                tz = pytz.timezone(timezone_name)
                now = timezone.now().astimezone(tz)
                today = now.date()

                # 计算今天的执行时间
                today_run = tz.localize(datetime.combine(today, time(hour, minute)))

                if now < today_run:
                    next_run = today_run
                else:
                    # 如果今天的时间已过，计算明天的执行时间
                    from datetime import timedelta
                    tomorrow = today + timedelta(days=1)
                    next_run = tz.localize(datetime.combine(tomorrow, time(hour, minute)))

                self.stdout.write(f'  下次运行: {next_run.strftime("%Y-%m-%d %H:%M:%S %Z")}')

            self.stdout.write('='*50)

            # 提供有用的提示
            self.stdout.write('\n' + self.style.WARNING('提示:'))
            self.stdout.write('• 确保Celery Beat调度器正在运行: celery -A celery_app beat')
            self.stdout.write('• 确保Celery Worker正在运行: celery -A celery_app worker')
            self.stdout.write('• 可以在Django Admin中查看和管理定期任务: /admin/django_celery_beat/periodictask/')

            if not disable:
                self.stdout.write('• 任务将在指定时间自动执行用户活跃度衰减处理')
            else:
                self.stdout.write('• 任务已禁用，不会自动执行。可以在Admin中启用或使用 --force 参数重新启用')

        except Exception as e:
            raise CommandError(f'设置任务时发生错误: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS('\n✅ 活跃度衰减任务设置完成!')
        )