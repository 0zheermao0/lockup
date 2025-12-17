#!/usr/bin/env python
"""
为测试任务添加提交文件
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskSubmissionFile, TaskParticipant
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils import timezone

User = get_user_model()

def create_test_submission():
    """为测试任务添加提交文件"""
    task_id = 'd7942bf9-b0ad-41ec-877c-bba1355913f8'  # 之前创建的测试任务

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🎯 为测试任务添加提交文件: {task.title}")
        print()

        # 获取一个参与者
        participant = task.participants.filter(status='approved').first()
        if not participant:
            print("❌ 没有找到合适的参与者")
            return

        print(f"👤 参与者: {participant.participant.username}")

        # 检查是否已有提交文件
        existing_files = TaskSubmissionFile.objects.filter(participant=participant)
        if existing_files.exists():
            print(f"✅ 已有 {existing_files.count()} 个提交文件:")
            for file in existing_files:
                print(f"   - {file.file_name}")
            print()
            print(f"🎯 测试URL: http://localhost:5174/tasks/{task.id}")
            return

        # 创建一个测试图片文件
        test_content = b"Test image content"
        test_file = ContentFile(test_content, name="test_image.jpg")

        submission_file = TaskSubmissionFile.objects.create(
            task=task,
            participant=participant,
            uploader=participant.participant,
            file=test_file,
            file_type='image',
            file_name='test_image.jpg',
            file_size=len(test_content),
            is_primary=True,
            description='测试提交图片'
        )

        print(f"✅ 创建提交文件: {submission_file.file_name}")
        print(f"   URL: {submission_file.file_url}")
        print(f"   是图片: {submission_file.is_image}")
        print()
        print(f"🎯 测试URL: http://localhost:5174/tasks/{task.id}")

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    create_test_submission()