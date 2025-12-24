#!/usr/bin/env python3
"""
Django Management Command to Set Up Celery Beat Periodic Tasks

This command sets up ALL periodic tasks in the django-celery-beat database scheduler:
- Hourly rewards processing task: runs every hour to process hourly rewards for active lock tasks
- Auto-freeze strict mode tasks: runs daily at 4:15 AM to freeze tasks without check-ins
- Weekly level promotions task: runs every Wednesday at 4:30 AM to check and promote eligible users
- Activity decay processing: runs daily at 4:45 AM to apply time-based activity decay
- Check-in voting results processing: runs daily at 4:00 AM to process expired voting sessions
- Pinning queue processing: runs every minute to manage user pinning queue
- Pinning system health check: runs every 5 minutes to monitor pinning system

Author: Claude Code
Created: 2024-12-19
Updated: 2024-12-25
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Set up ALL Celery Beat periodic tasks for the complete system (rewards, auto-freeze, promotions, activity decay, voting, pinning)'

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
        # Auto-Freeze Strict Mode Tasks Setup
        # ========================================================================

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Setting up auto-freeze strict mode tasks...'))

        # Create daily crontab schedule (Daily 4:15 AM)
        auto_freeze_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=15,
            hour=4,
            day_of_week='*',  # Daily
            day_of_month='*',
            month_of_year='*',
        )

        if created and not dry_run:
            self.stdout.write(f'Created daily crontab schedule: {auto_freeze_schedule}')
        elif created:
            self.stdout.write(f'[DRY RUN] Would create daily crontab schedule: {auto_freeze_schedule}')
        else:
            self.stdout.write(f'Using existing daily crontab schedule: {auto_freeze_schedule}')

        # Create periodic task for auto-freeze
        auto_freeze_task_name = 'auto-freeze-strict-mode-tasks'
        auto_freeze_task_function = 'tasks.celery_tasks.auto_freeze_strict_mode_tasks'

        if dry_run:
            existing_auto_freeze_task = PeriodicTask.objects.filter(name=auto_freeze_task_name).first()
            if existing_auto_freeze_task:
                self.stdout.write(
                    self.style.WARNING(f'[DRY RUN] Task "{auto_freeze_task_name}" already exists')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'[DRY RUN] Would create periodic task: {auto_freeze_task_name}')
                )
        else:
            auto_freeze_periodic_task, created = PeriodicTask.objects.get_or_create(
                name=auto_freeze_task_name,
                defaults={
                    'crontab': auto_freeze_schedule,
                    'task': auto_freeze_task_function,
                    'kwargs': json.dumps({}),
                    'enabled': True,
                    'description': 'Auto-freeze strict mode tasks without check-in posts (Daily 4:15 AM)',
                    'queue': 'default',
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created periodic task: {auto_freeze_task_name}')
                )
                self.stdout.write(f'  Task: {auto_freeze_task_function}')
                self.stdout.write(f'  Schedule: {auto_freeze_schedule}')
                self.stdout.write(f'  Queue: default')
                self.stdout.write(f'  Enabled: {auto_freeze_periodic_task.enabled}')
            else:
                # Update existing task if needed
                updated = False
                if auto_freeze_periodic_task.task != auto_freeze_task_function:
                    auto_freeze_periodic_task.task = auto_freeze_task_function
                    updated = True
                if auto_freeze_periodic_task.crontab != auto_freeze_schedule:
                    auto_freeze_periodic_task.crontab = auto_freeze_schedule
                    updated = True
                if not auto_freeze_periodic_task.enabled:
                    auto_freeze_periodic_task.enabled = True
                    updated = True
                if getattr(auto_freeze_periodic_task, 'queue', None) != 'default':
                    auto_freeze_periodic_task.queue = 'default'
                    updated = True

                if updated:
                    auto_freeze_periodic_task.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated existing periodic task: {auto_freeze_task_name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Periodic task "{auto_freeze_task_name}" already exists and is up to date')
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

        # ========================================================================
        # Activity Decay Processing Task Setup
        # ========================================================================

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Setting up activity decay processing task...'))

        # Create daily crontab schedule (Daily 4:45 AM Asia/Shanghai)
        activity_decay_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=45,
            hour=4,
            day_of_week='*',  # Daily
            day_of_month='*',
            month_of_year='*',
            timezone='Asia/Shanghai',
        )

        if created and not dry_run:
            self.stdout.write(f'Created activity decay crontab schedule: {activity_decay_schedule}')
        elif created:
            self.stdout.write(f'[DRY RUN] Would create activity decay crontab schedule: {activity_decay_schedule}')
        else:
            self.stdout.write(f'Using existing activity decay crontab schedule: {activity_decay_schedule}')

        # Create periodic task for activity decay
        activity_decay_task_name = 'process-activity-decay'
        activity_decay_task_function = 'tasks.celery_tasks.process_activity_decay'

        if dry_run:
            existing_activity_decay_task = PeriodicTask.objects.filter(name=activity_decay_task_name).first()
            if existing_activity_decay_task:
                self.stdout.write(
                    self.style.WARNING(f'[DRY RUN] Task "{activity_decay_task_name}" already exists')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'[DRY RUN] Would create periodic task: {activity_decay_task_name}')
                )
        else:
            activity_decay_periodic_task, created = PeriodicTask.objects.get_or_create(
                name=activity_decay_task_name,
                defaults={
                    'crontab': activity_decay_schedule,
                    'task': activity_decay_task_function,
                    'kwargs': json.dumps({}),
                    'enabled': True,
                    'description': 'Process user activity decay with Fibonacci time decay (Daily 4:45 AM)',
                    'queue': 'activity',
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created periodic task: {activity_decay_task_name}')
                )
                self.stdout.write(f'  Task: {activity_decay_task_function}')
                self.stdout.write(f'  Schedule: {activity_decay_schedule}')
                self.stdout.write(f'  Queue: activity')
                self.stdout.write(f'  Enabled: {activity_decay_periodic_task.enabled}')
            else:
                # Update existing task if needed
                updated = False
                if activity_decay_periodic_task.task != activity_decay_task_function:
                    activity_decay_periodic_task.task = activity_decay_task_function
                    updated = True
                if activity_decay_periodic_task.crontab != activity_decay_schedule:
                    activity_decay_periodic_task.crontab = activity_decay_schedule
                    updated = True
                if not activity_decay_periodic_task.enabled:
                    activity_decay_periodic_task.enabled = True
                    updated = True
                if getattr(activity_decay_periodic_task, 'queue', None) != 'activity':
                    activity_decay_periodic_task.queue = 'activity'
                    updated = True

                if updated:
                    activity_decay_periodic_task.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated existing periodic task: {activity_decay_task_name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Periodic task "{activity_decay_task_name}" already exists and is up to date')
                    )

        # ========================================================================
        # Check-in Voting Results Processing Task Setup
        # ========================================================================

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Setting up check-in voting results processing task...'))

        # Create daily crontab schedule (Daily 4:00 AM Asia/Shanghai)
        voting_results_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=4,
            day_of_week='*',  # Daily
            day_of_month='*',
            month_of_year='*',
            timezone='Asia/Shanghai',
        )

        if created and not dry_run:
            self.stdout.write(f'Created voting results crontab schedule: {voting_results_schedule}')
        elif created:
            self.stdout.write(f'[DRY RUN] Would create voting results crontab schedule: {voting_results_schedule}')
        else:
            self.stdout.write(f'Using existing voting results crontab schedule: {voting_results_schedule}')

        # Create periodic task for voting results
        voting_results_task_name = 'process-checkin-voting-results'
        voting_results_task_function = 'tasks.celery_tasks.process_checkin_voting_results'

        if dry_run:
            existing_voting_results_task = PeriodicTask.objects.filter(name=voting_results_task_name).first()
            if existing_voting_results_task:
                self.stdout.write(
                    self.style.WARNING(f'[DRY RUN] Task "{voting_results_task_name}" already exists')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'[DRY RUN] Would create periodic task: {voting_results_task_name}')
                )
        else:
            voting_results_periodic_task, created = PeriodicTask.objects.get_or_create(
                name=voting_results_task_name,
                defaults={
                    'crontab': voting_results_schedule,
                    'task': voting_results_task_function,
                    'kwargs': json.dumps({}),
                    'enabled': True,
                    'description': 'Process expired check-in voting sessions and distribute rewards (Daily 4:00 AM)',
                    'queue': 'default',
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created periodic task: {voting_results_task_name}')
                )
                self.stdout.write(f'  Task: {voting_results_task_function}')
                self.stdout.write(f'  Schedule: {voting_results_schedule}')
                self.stdout.write(f'  Queue: default')
                self.stdout.write(f'  Enabled: {voting_results_periodic_task.enabled}')
            else:
                # Update existing task if needed
                updated = False
                if voting_results_periodic_task.task != voting_results_task_function:
                    voting_results_periodic_task.task = voting_results_task_function
                    updated = True
                if voting_results_periodic_task.crontab != voting_results_schedule:
                    voting_results_periodic_task.crontab = voting_results_schedule
                    updated = True
                if not voting_results_periodic_task.enabled:
                    voting_results_periodic_task.enabled = True
                    updated = True
                if getattr(voting_results_periodic_task, 'queue', None) != 'default':
                    voting_results_periodic_task.queue = 'default'
                    updated = True

                if updated:
                    voting_results_periodic_task.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated existing periodic task: {voting_results_task_name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Periodic task "{voting_results_task_name}" already exists and is up to date')
                    )

        # ========================================================================
        # Pinning Queue Processing Task Setup
        # ========================================================================

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Setting up pinning queue processing task...'))

        # Create every-minute interval schedule
        pinning_queue_schedule, created = IntervalSchedule.objects.get_or_create(
            every=60,  # 60 seconds = 1 minute
            period=IntervalSchedule.SECONDS,
        )

        if created and not dry_run:
            self.stdout.write(f'Created pinning queue interval schedule: {pinning_queue_schedule}')
        elif created:
            self.stdout.write(f'[DRY RUN] Would create pinning queue interval schedule: {pinning_queue_schedule}')
        else:
            self.stdout.write(f'Using existing pinning queue interval schedule: {pinning_queue_schedule}')

        # Create periodic task for pinning queue
        pinning_queue_task_name = 'process-pinning-queue'
        pinning_queue_task_function = 'tasks.celery_tasks.process_pinning_queue'

        if dry_run:
            existing_pinning_queue_task = PeriodicTask.objects.filter(name=pinning_queue_task_name).first()
            if existing_pinning_queue_task:
                self.stdout.write(
                    self.style.WARNING(f'[DRY RUN] Task "{pinning_queue_task_name}" already exists')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'[DRY RUN] Would create periodic task: {pinning_queue_task_name}')
                )
        else:
            pinning_queue_periodic_task, created = PeriodicTask.objects.get_or_create(
                name=pinning_queue_task_name,
                defaults={
                    'interval': pinning_queue_schedule,
                    'task': pinning_queue_task_function,
                    'kwargs': json.dumps({}),
                    'enabled': True,
                    'description': 'Process user pinning queue - remove expired, activate waiting users (Every minute)',
                    'queue': 'default',
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created periodic task: {pinning_queue_task_name}')
                )
                self.stdout.write(f'  Task: {pinning_queue_task_function}')
                self.stdout.write(f'  Schedule: {pinning_queue_schedule}')
                self.stdout.write(f'  Queue: default')
                self.stdout.write(f'  Enabled: {pinning_queue_periodic_task.enabled}')
            else:
                # Update existing task if needed
                updated = False
                if pinning_queue_periodic_task.task != pinning_queue_task_function:
                    pinning_queue_periodic_task.task = pinning_queue_task_function
                    updated = True
                if pinning_queue_periodic_task.interval != pinning_queue_schedule:
                    pinning_queue_periodic_task.interval = pinning_queue_schedule
                    updated = True
                if not pinning_queue_periodic_task.enabled:
                    pinning_queue_periodic_task.enabled = True
                    updated = True
                if getattr(pinning_queue_periodic_task, 'queue', None) != 'default':
                    pinning_queue_periodic_task.queue = 'default'
                    updated = True

                if updated:
                    pinning_queue_periodic_task.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated existing periodic task: {pinning_queue_task_name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Periodic task "{pinning_queue_task_name}" already exists and is up to date')
                    )

        # ========================================================================
        # Pinning System Health Check Task Setup
        # ========================================================================

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Setting up pinning system health check task...'))

        # Create every-5-minutes interval schedule
        pinning_health_schedule, created = IntervalSchedule.objects.get_or_create(
            every=300,  # 300 seconds = 5 minutes
            period=IntervalSchedule.SECONDS,
        )

        if created and not dry_run:
            self.stdout.write(f'Created pinning health interval schedule: {pinning_health_schedule}')
        elif created:
            self.stdout.write(f'[DRY RUN] Would create pinning health interval schedule: {pinning_health_schedule}')
        else:
            self.stdout.write(f'Using existing pinning health interval schedule: {pinning_health_schedule}')

        # Create periodic task for pinning health check
        pinning_health_task_name = 'pinning-health-check'
        pinning_health_task_function = 'tasks.celery_tasks.pinning_health_check'

        if dry_run:
            existing_pinning_health_task = PeriodicTask.objects.filter(name=pinning_health_task_name).first()
            if existing_pinning_health_task:
                self.stdout.write(
                    self.style.WARNING(f'[DRY RUN] Task "{pinning_health_task_name}" already exists')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'[DRY RUN] Would create periodic task: {pinning_health_task_name}')
                )
        else:
            pinning_health_periodic_task, created = PeriodicTask.objects.get_or_create(
                name=pinning_health_task_name,
                defaults={
                    'interval': pinning_health_schedule,
                    'task': pinning_health_task_function,
                    'kwargs': json.dumps({}),
                    'enabled': True,
                    'description': 'Monitor pinning system health and detect issues (Every 5 minutes)',
                    'queue': 'default',
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created periodic task: {pinning_health_task_name}')
                )
                self.stdout.write(f'  Task: {pinning_health_task_function}')
                self.stdout.write(f'  Schedule: {pinning_health_schedule}')
                self.stdout.write(f'  Queue: default')
                self.stdout.write(f'  Enabled: {pinning_health_periodic_task.enabled}')
            else:
                # Update existing task if needed
                updated = False
                if pinning_health_periodic_task.task != pinning_health_task_function:
                    pinning_health_periodic_task.task = pinning_health_task_function
                    updated = True
                if pinning_health_periodic_task.interval != pinning_health_schedule:
                    pinning_health_periodic_task.interval = pinning_health_schedule
                    updated = True
                if not pinning_health_periodic_task.enabled:
                    pinning_health_periodic_task.enabled = True
                    updated = True
                if getattr(pinning_health_periodic_task, 'queue', None) != 'default':
                    pinning_health_periodic_task.queue = 'default'
                    updated = True

                if updated:
                    pinning_health_periodic_task.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated existing periodic task: {pinning_health_task_name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Periodic task "{pinning_health_task_name}" already exists and is up to date')
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

            self.stdout.write('\n--- Auto-Freeze Strict Mode Tasks ---')
            self.stdout.write(f'Name: {auto_freeze_periodic_task.name}')
            self.stdout.write(f'Task: {auto_freeze_periodic_task.task}')
            self.stdout.write(f'Schedule: {auto_freeze_periodic_task.crontab}')
            self.stdout.write(f'Enabled: {auto_freeze_periodic_task.enabled}')
            self.stdout.write(f'Queue: {getattr(auto_freeze_periodic_task, "queue", "default")}')
            self.stdout.write(f'Last Run: {auto_freeze_periodic_task.last_run_at or "Never"}')

            self.stdout.write('\n--- Weekly Level Promotions Task ---')
            self.stdout.write(f'Name: {level_periodic_task.name}')
            self.stdout.write(f'Task: {level_periodic_task.task}')
            self.stdout.write(f'Schedule: {level_periodic_task.crontab}')
            self.stdout.write(f'Enabled: {level_periodic_task.enabled}')
            self.stdout.write(f'Queue: {getattr(level_periodic_task, "queue", "default")}')
            self.stdout.write(f'Last Run: {level_periodic_task.last_run_at or "Never"}')

            self.stdout.write('\n--- Activity Decay Processing Task ---')
            self.stdout.write(f'Name: {activity_decay_periodic_task.name}')
            self.stdout.write(f'Task: {activity_decay_periodic_task.task}')
            self.stdout.write(f'Schedule: {activity_decay_periodic_task.crontab}')
            self.stdout.write(f'Enabled: {activity_decay_periodic_task.enabled}')
            self.stdout.write(f'Queue: {getattr(activity_decay_periodic_task, "queue", "default")}')
            self.stdout.write(f'Last Run: {activity_decay_periodic_task.last_run_at or "Never"}')

            self.stdout.write('\n--- Check-in Voting Results Processing Task ---')
            self.stdout.write(f'Name: {voting_results_periodic_task.name}')
            self.stdout.write(f'Task: {voting_results_periodic_task.task}')
            self.stdout.write(f'Schedule: {voting_results_periodic_task.crontab}')
            self.stdout.write(f'Enabled: {voting_results_periodic_task.enabled}')
            self.stdout.write(f'Queue: {getattr(voting_results_periodic_task, "queue", "default")}')
            self.stdout.write(f'Last Run: {voting_results_periodic_task.last_run_at or "Never"}')

            self.stdout.write('\n--- Pinning Queue Processing Task ---')
            self.stdout.write(f'Name: {pinning_queue_periodic_task.name}')
            self.stdout.write(f'Task: {pinning_queue_periodic_task.task}')
            self.stdout.write(f'Schedule: {pinning_queue_periodic_task.interval}')
            self.stdout.write(f'Enabled: {pinning_queue_periodic_task.enabled}')
            self.stdout.write(f'Queue: {getattr(pinning_queue_periodic_task, "queue", "default")}')
            self.stdout.write(f'Last Run: {pinning_queue_periodic_task.last_run_at or "Never"}')

            self.stdout.write('\n--- Pinning System Health Check Task ---')
            self.stdout.write(f'Name: {pinning_health_periodic_task.name}')
            self.stdout.write(f'Task: {pinning_health_periodic_task.task}')
            self.stdout.write(f'Schedule: {pinning_health_periodic_task.interval}')
            self.stdout.write(f'Enabled: {pinning_health_periodic_task.enabled}')
            self.stdout.write(f'Queue: {getattr(pinning_health_periodic_task, "queue", "default")}')
            self.stdout.write(f'Last Run: {pinning_health_periodic_task.last_run_at or "Never"}')
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

        task_names = [
            'process-hourly-rewards',
            'auto-freeze-strict-mode-tasks',
            'process-level-promotions',
            'process-activity-decay',
            'process-checkin-voting-results',
            'process-pinning-queue',
            'pinning-health-check'
        ]

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