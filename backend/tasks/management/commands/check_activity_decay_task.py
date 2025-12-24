#!/usr/bin/env python3
"""
Django Management Command: Check Activity Decay Task Status

This command checks the status of the activity decay periodic task and provides
information about its configuration and execution history.

Usage:
    python manage.py check_activity_decay_task

Author: Claude Code
Created: 2024-12-25
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from datetime import datetime, timedelta
import pytz


class Command(BaseCommand):
    help = '检查活跃度衰减定期任务的状态和执行历史'

    def add_arguments(self, parser):
        parser.add_argument(
            '--history',
            type=int,
            default=10,
            help='显示最近N次执行历史（默认10次）'
        )
        parser.add_argument(
            '--enable',
            action='store_true',
            help='启用任务'
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='禁用任务'
        )

    def handle(self, *args, **options):
        history_count = options['history']
        enable_task = options['enable']
        disable_task = options['disable']

        if enable_task and disable_task:
            raise CommandError('不能同时启用和禁用任务')

        self.stdout.write(
            self.style.SUCCESS('检查活跃度衰减任务状态...')
        )

        try:
            # 查找任务
            task_name = 'process-activity-decay'
            task = PeriodicTask.objects.filter(name=task_name).first()

            if not task:
                self.stdout.write(
                    self.style.ERROR(
                        f'未找到任务 "{task_name}"。请先运行 setup_activity_decay_task 命令创建任务。'
                    )
                )
                return

            # 处理启用/禁用请求
            if enable_task:
                if task.enabled:
                    self.stdout.write(
                        self.style.WARNING('任务已经是启用状态')
                    )
                else:
                    task.enabled = True
                    task.save()
                    self.stdout.write(
                        self.style.SUCCESS('✅ 任务已启用')
                    )

            if disable_task:
                if not task.enabled:
                    self.stdout.write(
                        self.style.WARNING('任务已经是禁用状态')
                    )
                else:
                    task.enabled = False
                    task.save()
                    self.stdout.write(
                        self.style.SUCCESS('✅ 任务已禁用')
                    )

            # 显示任务基本信息
            self.stdout.write('\n' + '='*60)
            self.stdout.write('任务基本信息:')
            self.stdout.write('='*60)
            self.stdout.write(f'  名称: {task.name}')
            self.stdout.write(f'  描述: {task.description}')
            self.stdout.write(f'  任务函数: {task.task}')
            self.stdout.write(f'  状态: {"🟢 启用" if task.enabled else "🔴 禁用"}')
            self.stdout.write(f'  创建时间: {task.date_changed}')
            self.stdout.write(f'  最后修改: {task.date_changed}')

            # 显示调度信息
            if task.crontab:
                crontab = task.crontab
                self.stdout.write(f'\n调度信息:')
                self.stdout.write(f'  时区: {crontab.timezone}')
                self.stdout.write(f'  时间: 每日 {int(crontab.hour):02d}:{int(crontab.minute):02d}')
                self.stdout.write(f'  Cron表达式: {crontab.minute} {crontab.hour} {crontab.day_of_month} {crontab.month_of_year} {crontab.day_of_week}')

                # 计算下次运行时间
                if task.enabled:
                    try:
                        tz = pytz.timezone(crontab.timezone)
                        now = timezone.now().astimezone(tz)
                        today = now.date()

                        # 计算今天的执行时间
                        from datetime import time
                        today_run = tz.localize(datetime.combine(today, time(int(crontab.hour), int(crontab.minute))))

                        if now < today_run:
                            next_run = today_run
                        else:
                            # 如果今天的时间已过，计算明天的执行时间
                            tomorrow = today + timedelta(days=1)
                            next_run = tz.localize(datetime.combine(tomorrow, time(int(crontab.hour), int(crontab.minute))))

                        self.stdout.write(f'  下次运行: {next_run.strftime("%Y-%m-%d %H:%M:%S %Z")}')

                        # 计算距离下次运行的时间
                        time_until = next_run - now
                        hours, remainder = divmod(time_until.total_seconds(), 3600)
                        minutes, _ = divmod(remainder, 60)
                        self.stdout.write(f'  距离下次运行: {int(hours)}小时{int(minutes)}分钟')

                    except Exception as e:
                        self.stdout.write(f'  下次运行时间计算错误: {str(e)}')

            # 显示执行历史
            self.stdout.write(f'\n最近 {history_count} 次执行历史:')
            self.stdout.write('-'*60)

            # 尝试查询执行结果
            try:
                from django_celery_results.models import TaskResult
                task_results = TaskResult.objects.filter(
                    task_name='tasks.celery_tasks.process_activity_decay'
                ).order_by('-date_done')[:history_count]

                if not task_results:
                    self.stdout.write('  暂无执行历史')
                else:
                    for i, result in enumerate(task_results, 1):
                        status_icon = {
                            'SUCCESS': '✅',
                            'FAILURE': '❌',
                            'PENDING': '⏳',
                            'RETRY': '🔄',
                            'REVOKED': '🚫'
                        }.get(result.status, '❓')

                        self.stdout.write(
                            f'  {i:2d}. {status_icon} {result.date_done.strftime("%Y-%m-%d %H:%M:%S")} '
                            f'({result.status})'
                        )

                        if result.status == 'SUCCESS' and result.result:
                            try:
                                import json
                                result_data = json.loads(result.result) if isinstance(result.result, str) else result.result
                                if isinstance(result_data, dict):
                                    processed = result_data.get('processed_users', 0)
                                    decay = result_data.get('total_decay_applied', 0)
                                    self.stdout.write(f'      处理用户: {processed}, 总衰减: {decay}')
                            except:
                                pass

                        elif result.status == 'FAILURE' and result.traceback:
                            # 显示错误信息的前100个字符
                            error = result.traceback[:100] + '...' if len(result.traceback) > 100 else result.traceback
                            self.stdout.write(f'      错误: {error}')

            except ImportError:
                self.stdout.write('  ❓ 无法查询执行历史 (django-celery-results 未安装)')

            # 显示系统状态检查
            self.stdout.write(f'\n系统状态检查:')
            self.stdout.write('-'*60)

            # 检查是否有Celery Worker在运行
            from celery import current_app
            try:
                inspect = current_app.control.inspect()
                active_workers = inspect.active()
                if active_workers:
                    self.stdout.write(f'  ✅ Celery Worker: {len(active_workers)} 个活跃')
                    for worker_name in active_workers.keys():
                        self.stdout.write(f'     - {worker_name}')
                else:
                    self.stdout.write('  ❌ Celery Worker: 无活跃Worker')
            except Exception as e:
                self.stdout.write(f'  ❓ Celery Worker: 无法检查状态 ({str(e)})')

            # 检查任务队列
            try:
                from django_celery_beat.models import CrontabSchedule
                total_tasks = PeriodicTask.objects.filter(enabled=True).count()
                self.stdout.write(f'  📋 定期任务: {total_tasks} 个启用')
            except Exception as e:
                self.stdout.write(f'  ❓ 定期任务: 无法检查 ({str(e)})')

            self.stdout.write('\n' + '='*60)

            # 提供有用的提示
            self.stdout.write('\n' + self.style.WARNING('管理提示:'))
            if not task.enabled:
                self.stdout.write('• 任务已禁用，使用 --enable 参数启用任务')
            self.stdout.write('• 查看Django Admin: /admin/django_celery_beat/periodictask/')
            self.stdout.write('• 手动执行: python manage.py run_activity_decay')
            self.stdout.write('• 启动Celery Beat: celery -A celery_app beat')
            self.stdout.write('• 启动Celery Worker: celery -A celery_app worker')

            self.stdout.write(
                self.style.SUCCESS('\n✅ 状态检查完成!')
            )

        except Exception as e:
            raise CommandError(f'检查任务状态时发生错误: {str(e)}')