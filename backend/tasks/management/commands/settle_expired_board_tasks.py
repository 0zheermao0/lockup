"""
Management command to settle expired board tasks
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.models import LockTask
from tasks.celery_tasks import auto_settle_expired_board_task
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Settle expired board tasks that have passed their deadline'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be settled without actually settling',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Find expired board tasks that need settlement
        expired_tasks = LockTask.objects.filter(
            task_type='board',
            deadline__isnull=False,
            deadline__lt=timezone.now(),
            status__in=['open', 'taken', 'submitted']
        ).order_by('deadline')

        if not expired_tasks.exists():
            self.stdout.write(
                self.style.SUCCESS('No expired board tasks found that need settlement.')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'Found {expired_tasks.count()} expired board tasks that need settlement.')
        )

        settled_count = 0
        failed_count = 0

        for task in expired_tasks:
            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Would settle task: {task.title} (ID: {task.id}, deadline: {task.deadline})'
                )
            else:
                try:
                    self.stdout.write(f'Settling task: {task.title} (ID: {task.id})')
                    result = auto_settle_expired_board_task(str(task.id))

                    if result and result.get('status') == 'success':
                        settlement_action = result['settlement_result']['action']
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Settled as: {settlement_action}')
                        )
                        settled_count += 1
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Settlement failed: {result}')
                        )
                        failed_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error settling task {task.id}: {e}')
                    )
                    failed_count += 1
                    logger.error(f'Error settling expired task {task.id}: {e}', exc_info=True)

        if not dry_run:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(f'Settlement complete: {settled_count} succeeded, {failed_count} failed')
            )
        else:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(f'Dry run complete: {expired_tasks.count()} tasks would be processed')
            )