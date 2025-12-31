from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.models import LockTask, TaskTimelineEvent
import random
import string
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '手动更新所有严格模式任务的验证码'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='只更新指定用户的任务验证码'
        )
        parser.add_argument(
            '--task-id',
            help='只更新指定任务的验证码'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='预览模式，不实际更新'
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        task_id = options.get('task_id')
        dry_run = options.get('dry_run')

        # 构建查询条件
        queryset = LockTask.objects.filter(
            strict_mode=True,
            status='active'
        )

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if task_id:
            queryset = queryset.filter(id=task_id)

        tasks = queryset.select_related('user')

        if not tasks.exists():
            self.stdout.write(
                self.style.WARNING('没有找到符合条件的严格模式任务')
            )
            return

        self.stdout.write(f"找到 {tasks.count()} 个严格模式任务")

        if dry_run:
            self.stdout.write(self.style.WARNING('预览模式，不会实际更新'))
            for task in tasks:
                self.stdout.write(f"  - {task.title} (用户: {task.user.username}, 当前验证码: {task.strict_code})")
            return

        updated_count = 0
        for task in tasks:
            try:
                old_code = task.strict_code
                new_code = self._generate_verification_code()

                # 更新任务
                task.strict_code = new_code
                task.save(update_fields=['strict_code'])

                # 创建时间线事件
                TaskTimelineEvent.objects.create(
                    task=task,
                    user=task.user,
                    event_type='verification_code_updated',
                    description='验证码已更新（管理命令触发）',
                    metadata={
                        'old_verification_code': old_code,
                        'new_verification_code': new_code,
                        'trigger_reason': 'manual_command',
                        'update_time': timezone.now().isoformat()
                    }
                )

                updated_count += 1
                self.stdout.write(f"✓ 更新任务: {task.title} ({old_code} -> {new_code})")

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ 更新任务 {task.title} 失败: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"成功更新了 {updated_count} 个任务的验证码")
        )

    def _generate_verification_code(self):
        """生成4位验证码（格式：字母数字字母数字，如A1B2）"""
        letters = random.choices(string.ascii_uppercase, k=2)
        digits = random.choices(string.digits, k=2)
        return f"{letters[0]}{digits[0]}{letters[1]}{digits[1]}"