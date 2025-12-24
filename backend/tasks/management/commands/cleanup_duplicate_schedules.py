#!/usr/bin/env python3
"""
Django Management Command: Clean Up Duplicate CrontabSchedule Records

This command identifies and removes duplicate CrontabSchedule records that are
causing the MultipleObjectsReturned error in setup_celery_beat.

Author: Claude Code
Created: 2024-12-25
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from django.db import transaction


class Command(BaseCommand):
    help = 'Clean up duplicate CrontabSchedule records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup without confirmation',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(
            self.style.SUCCESS('检查CrontabSchedule重复记录...')
        )

        # 查找所有重复的调度记录
        duplicates_info = self._find_duplicates()

        if not duplicates_info:
            self.stdout.write(
                self.style.SUCCESS('✅ 没有发现重复的CrontabSchedule记录')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'发现 {len(duplicates_info)} 组重复记录:')
        )

        for i, (criteria, schedules) in enumerate(duplicates_info, 1):
            self.stdout.write(f'\n--- 重复组 {i} ---')
            self.stdout.write(f'条件: {criteria}')
            self.stdout.write(f'重复数量: {len(schedules)}')

            for schedule in schedules:
                tasks = PeriodicTask.objects.filter(crontab=schedule)
                task_names = [task.name for task in tasks]
                self.stdout.write(
                    f'  ID:{schedule.id} 时区:{schedule.timezone} '
                    f'使用者:{task_names if task_names else "无"}'
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n[DRY RUN] 预览清理操作:')
            )
            self._preview_cleanup(duplicates_info)
            return

        if not force:
            confirm = input('\n是否继续清理重复记录? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write('操作已取消')
                return

        # 执行清理
        self._cleanup_duplicates(duplicates_info)

    def _find_duplicates(self):
        """查找重复的CrontabSchedule记录"""
        duplicates = []

        # 获取所有CrontabSchedule记录
        all_schedules = CrontabSchedule.objects.all()

        self.stdout.write(f'总共找到 {all_schedules.count()} 个CrontabSchedule记录')

        # 按照关键字段分组
        groups = {}
        for schedule in all_schedules:
            # 处理时区字段
            timezone_str = None
            if schedule.timezone:
                if hasattr(schedule.timezone, 'zone'):
                    timezone_str = schedule.timezone.zone
                else:
                    timezone_str = str(schedule.timezone)

            key = (
                schedule.minute,
                schedule.hour,
                schedule.day_of_week,
                schedule.day_of_month,
                schedule.month_of_year,
                timezone_str
            )
            if key not in groups:
                groups[key] = []
            groups[key].append(schedule)

            # 调试输出：显示每个记录的详细信息
            self.stdout.write(
                f'记录 ID:{schedule.id} - {schedule.minute} {schedule.hour} {schedule.day_of_week} {schedule.day_of_month} {schedule.month_of_year} (时区: {timezone_str})'
            )

        # 找出有重复的组
        for key, schedules in groups.items():
            if len(schedules) > 1:
                criteria = f"minute={key[0]} hour={key[1]} day_of_week={key[2]} day_of_month={key[3]} month_of_year={key[4]} timezone={key[5]}"
                duplicates.append((criteria, schedules))

        return duplicates

    def _preview_cleanup(self, duplicates_info):
        """预览清理操作"""
        for criteria, schedules in duplicates_info:
            self.stdout.write(f'\n清理组: {criteria}')

            # 确定要保留的记录（优先保留有任务使用的）
            schedules_with_tasks = []
            schedules_without_tasks = []

            for schedule in schedules:
                tasks = PeriodicTask.objects.filter(crontab=schedule)
                if tasks.exists():
                    schedules_with_tasks.append((schedule, list(tasks)))
                else:
                    schedules_without_tasks.append(schedule)

            if schedules_with_tasks:
                # 保留第一个有任务的记录
                keep_schedule, keep_tasks = schedules_with_tasks[0]
                self.stdout.write(f'  ✅ 保留: ID:{keep_schedule.id} (被任务使用: {[t.name for t in keep_tasks]})')

                # 其他有任务的记录需要迁移任务
                for schedule, tasks in schedules_with_tasks[1:]:
                    self.stdout.write(f'  🔄 迁移: ID:{schedule.id} -> ID:{keep_schedule.id} (任务: {[t.name for t in tasks]})')
                    self.stdout.write(f'  ❌ 删除: ID:{schedule.id}')
            else:
                # 没有任务使用，保留第一个
                keep_schedule = schedules[0]
                self.stdout.write(f'  ✅ 保留: ID:{keep_schedule.id} (无任务使用)')

            # 删除其余记录
            for schedule in schedules_without_tasks:
                if schedule.id != keep_schedule.id:
                    self.stdout.write(f'  ❌ 删除: ID:{schedule.id} (无任务使用)')

    def _cleanup_duplicates(self, duplicates_info):
        """执行清理重复记录"""
        total_deleted = 0
        total_migrated = 0

        for criteria, schedules in duplicates_info:
            self.stdout.write(f'\n处理组: {criteria}')

            # 确定要保留的记录
            schedules_with_tasks = []
            schedules_without_tasks = []

            for schedule in schedules:
                tasks = PeriodicTask.objects.filter(crontab=schedule)
                if tasks.exists():
                    schedules_with_tasks.append((schedule, list(tasks)))
                else:
                    schedules_without_tasks.append(schedule)

            if schedules_with_tasks:
                # 保留第一个有任务的记录
                keep_schedule, keep_tasks = schedules_with_tasks[0]
                self.stdout.write(f'  ✅ 保留: ID:{keep_schedule.id}')

                # 迁移其他记录的任务到保留的记录
                with transaction.atomic():
                    for schedule, tasks in schedules_with_tasks[1:]:
                        for task in tasks:
                            task.crontab = keep_schedule
                            task.save()
                            total_migrated += 1
                            self.stdout.write(f'    🔄 迁移任务: {task.name}')

                        schedule.delete()
                        total_deleted += 1
                        self.stdout.write(f'    ❌ 删除: ID:{schedule.id}')
            else:
                # 保留第一个记录
                keep_schedule = schedules[0]
                self.stdout.write(f'  ✅ 保留: ID:{keep_schedule.id}')

            # 删除其余无任务的记录
            for schedule in schedules_without_tasks:
                if schedule.id != keep_schedule.id:
                    schedule.delete()
                    total_deleted += 1
                    self.stdout.write(f'    ❌ 删除: ID:{schedule.id}')

        self.stdout.write(f'\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ 清理完成! 删除了 {total_deleted} 个重复记录，迁移了 {total_migrated} 个任务'
            )
        )

        # 验证结果
        remaining_duplicates = self._find_duplicates()
        if remaining_duplicates:
            self.stdout.write(
                self.style.WARNING(f'⚠️  仍有 {len(remaining_duplicates)} 组重复记录')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ 所有重复记录已清理完成')
            )