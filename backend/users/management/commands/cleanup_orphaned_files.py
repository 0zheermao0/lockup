"""
Django管理命令：清理孤立的文件记录
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import User
from posts.models import PostImage, CommentImage
from tasks.models import TaskSubmissionFile


class Command(BaseCommand):
    help = '清理指向不存在文件的数据库记录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示要删除的记录，不实际删除',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN模式 - 只显示要删除的记录，不实际删除')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('🧹 开始清理孤立文件记录...')
            )

        media_root = settings.MEDIA_ROOT
        total_cleaned = 0

        # 清理动态图片
        self.stdout.write('\n📸 检查动态图片...')
        post_images = PostImage.objects.all()
        post_cleaned = 0

        for img in post_images:
            if img.image:
                full_path = os.path.join(media_root, img.image.name)
                if not os.path.exists(full_path):
                    if dry_run:
                        self.stdout.write(f'  [DRY RUN] 将删除 PostImage {img.id}: {img.image.name}')
                    else:
                        self.stdout.write(f'  🗑️ 删除 PostImage {img.id}: {img.image.name}')
                        img.delete()
                    post_cleaned += 1

        # 清理评论图片
        self.stdout.write('\n💬 检查评论图片...')
        comment_images = CommentImage.objects.all()
        comment_cleaned = 0

        for img in comment_images:
            if img.image:
                full_path = os.path.join(media_root, img.image.name)
                if not os.path.exists(full_path):
                    if dry_run:
                        self.stdout.write(f'  [DRY RUN] 将删除 CommentImage {img.id}: {img.image.name}')
                    else:
                        self.stdout.write(f'  🗑️ 删除 CommentImage {img.id}: {img.image.name}')
                        img.delete()
                    comment_cleaned += 1

        # 清理任务文件
        self.stdout.write('\n📄 检查任务文件...')
        task_files = TaskSubmissionFile.objects.all()
        task_cleaned = 0

        for file in task_files:
            if file.file:
                full_path = os.path.join(media_root, file.file.name)
                if not os.path.exists(full_path):
                    if dry_run:
                        self.stdout.write(f'  [DRY RUN] 将删除 TaskFile {str(file.id)[:8]}: {file.file.name}')
                    else:
                        self.stdout.write(f'  🗑️ 删除 TaskFile {str(file.id)[:8]}: {file.file.name}')
                        file.delete()
                    task_cleaned += 1

        # 清理用户头像
        self.stdout.write('\n🖼️ 检查用户头像...')
        users = User.objects.filter(avatar__isnull=False).exclude(avatar='')
        avatar_cleaned = 0

        for user in users:
            if user.avatar:
                full_path = os.path.join(media_root, user.avatar.name)
                if not os.path.exists(full_path):
                    if dry_run:
                        self.stdout.write(f'  [DRY RUN] 将清空 User {user.username} 的头像: {user.avatar.name}')
                    else:
                        self.stdout.write(f'  🗑️ 清空 User {user.username} 的头像: {user.avatar.name}')
                        user.avatar = None
                        user.save(skip_file_validation=True)
                    avatar_cleaned += 1

        total_cleaned = post_cleaned + comment_cleaned + task_cleaned + avatar_cleaned

        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'📊 统计结果:')
        self.stdout.write(f'  动态图片: {post_cleaned}')
        self.stdout.write(f'  评论图片: {comment_cleaned}')
        self.stdout.write(f'  任务文件: {task_cleaned}')
        self.stdout.write(f'  用户头像: {avatar_cleaned}')
        self.stdout.write(f'  总计: {total_cleaned}')

        if dry_run:
            if total_cleaned > 0:
                self.stdout.write(
                    self.style.WARNING(f'🔍 发现 {total_cleaned} 个孤立记录，运行不带 --dry-run 参数来清理')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ 没有发现孤立记录')
                )
        else:
            if total_cleaned > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ 清理完成，共处理 {total_cleaned} 个孤立记录')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ 没有发现孤立记录，数据库状态良好')
                )