#!/usr/bin/env python3
"""
Django Management Command to Set Up Celery Beat Periodic Tasks

This command sets up the hourly rewards processing task in the django-celery-beat
database scheduler. It creates a periodic task that runs every hour to process
hourly rewards for active lock tasks.

Author: Claude Code
Created: 2024-12-19
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json


class Command(BaseCommand):
    help = 'Set up Celery Beat periodic tasks for hourly rewards processing'

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
        """Create periodic tasks for hourly rewards processing"""
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
            return

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

        # Show final task configuration
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Periodic Task Configuration:'))
        self.stdout.write(f'Name: {periodic_task.name}')
        self.stdout.write(f'Task: {periodic_task.task}')
        self.stdout.write(f'Schedule: {periodic_task.interval}')
        self.stdout.write(f'Enabled: {periodic_task.enabled}')
        self.stdout.write(f'Queue: {getattr(periodic_task, "queue", "default")}')
        self.stdout.write(f'Last Run: {periodic_task.last_run_at or "Never"}')
        # Note: next_run_at is calculated dynamically by the scheduler
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

        task_name = 'process-hourly-rewards'

        if dry_run:
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

        try:
            task = PeriodicTask.objects.get(name=task_name)
            task.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted periodic task: {task_name}')
            )
        except PeriodicTask.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f'Periodic task "{task_name}" does not exist')
            )

        # Optionally clean up unused interval schedules
        unused_schedules = IntervalSchedule.objects.filter(
            periodictask__isnull=True
        )
        if unused_schedules.exists():
            count = unused_schedules.count()
            unused_schedules.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned up {count} unused interval schedules')
            )

        self.stdout.write(
            self.style.SUCCESS('Periodic task deletion completed!')
        )