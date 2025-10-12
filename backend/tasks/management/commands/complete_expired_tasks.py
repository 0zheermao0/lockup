from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.models import LockTask


class Command(BaseCommand):
    help = 'Complete lock tasks that have reached their end time'

    def handle(self, *args, **options):
        # Find active lock tasks that have expired
        now = timezone.now()
        expired_tasks = LockTask.objects.filter(
            task_type='lock',
            status='active',
            end_time__lte=now
        )

        completed_count = 0
        for task in expired_tasks:
            task.status = 'completed'
            task.completed_at = now
            task.save()
            completed_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Auto-completed expired lock task: {task.title} (ID: {task.id})'
                )
            )

        if completed_count == 0:
            self.stdout.write(
                self.style.WARNING('No expired lock tasks found to complete.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully auto-completed {completed_count} expired lock task(s).'
                )
            )