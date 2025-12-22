#!/usr/bin/env python3
"""
Django Management Command to Set Up Celery Beat Periodic Tasks

This command sets up periodic tasks in the django-celery-beat database scheduler:
- Hourly rewards processing task: runs every hour to process hourly rewards for active lock tasks
- Weekly level promotions task: runs every Wednesday at 4:30 AM to check and promote eligible users

Author: Claude Code
Created: 2024-12-19
Updated: 2024-12-22
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Set up Celery Beat periodic tasks for hourly rewards processing and weekly level promotions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete existing periodic tasks instead of creating them',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete_tasks = options['delete']

        if delete_tasks:
            self._delete_periodic_tasks(dry_run)
        else:
            self._create_periodic_tasks(dry_run)

    def _create_periodic_tasks(self, dry_run):
        """Create periodic tasks for hourly rewards processing and weekly level promotions"""
        self.stdout.write(
            self.style.SUCCESS('Setting up Celery Beat periodic tasks...')
        )

        # Create hourly interval schedule
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.HOURS,
        )

        if created and not dry_run:
            self.stdout.write(f'Created hourly interval schedule: {schedule}')
        elif created:
            self.stdout.write(f'[DRY RUN] Would create hourly interval schedule: {schedule}')
        else:
            self.stdout.write(f'Using existing hourly interval schedule: {schedule}')

        # Create periodic task for hourly rewards processing
        task_name = 'process-hourly-rewards'
        task_function = 'tasks.celery_tasks.process_hourly_rewards'

        if dry_run:
            existing_task = PeriodicTask.objects.filter(name=task_name).first()
            if existing_task:
                self.stdout.write(
                    self.style.WARNING(f'[DRY RUN] Task "{task_name}" already exists')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'[DRY RUN] Would create periodic task: {task_name}')
                )
        else:
            periodic_task, created = PeriodicTask.objects.get_or_create(
                name=task_name,
                defaults={
                    'interval': schedule,
                    'task': task_function,
                    'kwargs': json.dumps({}),
                    'enabled': True,
                    'description': 'Process hourly rewards for active lock tasks',
                    'queue': 'rewards',  # Use dedicated rewards queue
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created periodic task: {task_name}')
                )
                self.stdout.write(f'  Task: {task_function}')
                self.stdout.write(f'  Schedule: Every {schedule}')
                self.stdout.write(f'  Queue: rewards')
                self.stdout.write(f'  Enabled: {periodic_task.enabled}')
            else:
                # Update existing task if needed
                updated = False
                if periodic_task.task != task_function:
                    periodic_task.task = task_function
                    updated = True
                if periodic_task.interval != schedule:
                    periodic_task.interval = schedule
                    updated = True
                if not periodic_task.enabled:
                    periodic_task.enabled = True
                    updated = True
                if getattr(periodic_task, 'queue', None) != 'rewards':
                    periodic_task.queue = 'rewards'
                    updated = True

                if updated:
                    periodic_task.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated existing periodic task: {task_name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Periodic task "{task_name}" already exists and is up to date')
                    )

        # ========================================================================
        # Weekly Level Promotions Task Setup
        # ========================================================================

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Setting up weekly level promotions task...'))

        # Create weekly crontab schedule (Wednesday 4:30 AM)
        level_promotion_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=30,
            hour=4,
            day_of_week=3,  # Wednesday (0=Monday)
            day_of_month='*',
            month_of_year='*',
        )

        if created and not dry_run:
            self.stdout.write(f'Created weekly crontab schedule: {level_promotion_schedule}')
        elif created:
            self.stdout.write(f'[DRY RUN] Would create weekly crontab schedule: {level_promotion_schedule}')
        else:
            self.stdout.write(f'Using existing weekly crontab schedule: {level_promotion_schedule}')

        # Create periodic task for level promotions
        level_task_name = 'process-level-promotions'
        level_task_function = 'tasks.celery_tasks.process_level_promotions'

        if dry_run:
            existing_level_task = PeriodicTask.objects.filter(name=level_task_name).first()
            if existing_level_task:
                self.stdout.write(
                    self.style.WARNING(f'[DRY RUN] Task "{level_task_name}" already exists')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'[DRY RUN] Would create periodic task: {level_task_name}')
                )
        else:
            level_periodic_task, created = PeriodicTask.objects.get_or_create(
                name=level_task_name,
                defaults={
                    'crontab': level_promotion_schedule,
                    'task': level_task_function,
                    'kwargs': json.dumps({}),
                    'enabled': True,
                    'description': 'Process weekly user level promotions (Wednesday 4:30 AM)',
                    'queue': 'default',
                    # 'expires': 3600,  # Remove expires field as it expects datetime, not seconds
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created periodic task: {level_task_name}')
                )
                self.stdout.write(f'  Task: {level_task_function}')
                self.stdout.write(f'  Schedule: {level_promotion_schedule}')
                self.stdout.write(f'  Queue: default')
                self.stdout.write(f'  Enabled: {level_periodic_task.enabled}')
                # self.stdout.write(f'  Expires: 1 hour')  # Removed expires field
            else:
                # Update existing task if needed
                updated = False
                if level_periodic_task.task != level_task_function:
                    level_periodic_task.task = level_task_function
                    updated = True
                if level_periodic_task.crontab != level_promotion_schedule:
                    level_periodic_task.crontab = level_promotion_schedule
                    updated = True
                if not level_periodic_task.enabled:
                    level_periodic_task.enabled = True
                    updated = True
                if getattr(level_periodic_task, 'queue', None) != 'default':
                    level_periodic_task.queue = 'default'
                    updated = True
                # Remove expires field check as it's not needed

                if updated:
                    level_periodic_task.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated existing periodic task: {level_task_name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Periodic task "{level_task_name}" already exists and is up to date')
                    )

        # Show final task configurations
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Periodic Tasks Configuration:'))

        if not dry_run:
            self.stdout.write('\n--- Hourly Rewards Task ---')
            self.stdout.write(f'Name: {periodic_task.name}')
            self.stdout.write(f'Task: {periodic_task.task}')
            self.stdout.write(f'Schedule: {periodic_task.interval}')
            self.stdout.write(f'Enabled: {periodic_task.enabled}')
            self.stdout.write(f'Queue: {getattr(periodic_task, "queue", "default")}')
            self.stdout.write(f'Last Run: {periodic_task.last_run_at or "Never"}')

            self.stdout.write('\n--- Weekly Level Promotions Task ---')
            self.stdout.write(f'Name: {level_periodic_task.name}')
            self.stdout.write(f'Task: {level_periodic_task.task}')
            self.stdout.write(f'Schedule: {level_periodic_task.crontab}')
            self.stdout.write(f'Enabled: {level_periodic_task.enabled}')
            self.stdout.write(f'Queue: {getattr(level_periodic_task, "queue", "default")}')
            # self.stdout.write(f'Expires: {getattr(level_periodic_task, "expires", "None")} seconds')  # Removed expires
            self.stdout.write(f'Last Run: {level_periodic_task.last_run_at or "Never"}')
        else:
            self.stdout.write('\n[DRY RUN] Task configuration details not available in dry-run mode')

        self.stdout.write('=' * 60)

        self.stdout.write(
            self.style.SUCCESS('\nCelery Beat setup completed successfully!')
        )
        self.stdout.write(
            'To start the scheduler, run: celery -A lockup_backend beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler'
        )

    def _delete_periodic_tasks(self, dry_run):
        """Delete periodic tasks"""
        self.stdout.write(
            self.style.WARNING('Deleting Celery Beat periodic tasks...')
        )

        task_names = ['process-hourly-rewards', 'process-level-promotions']

        if dry_run:
            for task_name in task_names:
                existing_task = PeriodicTask.objects.filter(name=task_name).first()
                if existing_task:
                    self.stdout.write(
                        self.style.WARNING(f'[DRY RUN] Would delete task: {task_name}')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'[DRY RUN] Task "{task_name}" does not exist')
                    )
            return

        deleted_count = 0
        for task_name in task_names:
            try:
                task = PeriodicTask.objects.get(name=task_name)
                task.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'Deleted periodic task: {task_name}')
                )
                deleted_count += 1
            except PeriodicTask.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Periodic task "{task_name}" does not exist')
                )

        # Clean up unused schedules
        unused_interval_schedules = IntervalSchedule.objects.filter(
            periodictask__isnull=True
        )
        unused_crontab_schedules = CrontabSchedule.objects.filter(
            periodictask__isnull=True
        )

        interval_count = 0
        if unused_interval_schedules.exists():
            interval_count = unused_interval_schedules.count()
            unused_interval_schedules.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned up {interval_count} unused interval schedules')
            )

        crontab_count = 0
        if unused_crontab_schedules.exists():
            crontab_count = unused_crontab_schedules.count()
            unused_crontab_schedules.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned up {crontab_count} unused crontab schedules')
            )

        self.stdout.write(
            self.style.SUCCESS(f'Periodic task deletion completed! Deleted {deleted_count} tasks.')
        )