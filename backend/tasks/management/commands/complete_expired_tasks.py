from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.models import LockTask
from tasks.utils import destroy_task_keys


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
            # 销毁任务相关的所有钥匙道具
            destroy_result = destroy_task_keys(task, reason="auto_completion", user=None, metadata={
                'completion_method': 'automatic',
                'auto_completed_at': now.isoformat()
            })

            task.status = 'completed'
            task.completed_at = now
            task.save()
            completed_count += 1

            keys_info = ""
            if destroy_result['success'] and destroy_result['keys_destroyed'] > 0:
                keys_info = f" (destroyed {destroy_result['keys_destroyed']} keys)"

            self.stdout.write(
                self.style.SUCCESS(
                    f'Auto-completed expired lock task: {task.title} (ID: {task.id}){keys_info}'
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