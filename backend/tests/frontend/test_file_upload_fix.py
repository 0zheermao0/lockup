#!/usr/bin/env python
"""
测试文件上传修复
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskSubmissionFile, TaskParticipant
from tasks.serializers import LockTaskSerializer
from django.contrib.auth import get_user_model
from unittest.mock import Mock

User = get_user_model()

def test_file_upload_fix():
    """测试文件上传修复"""
    print("🔍 测试文件上传修复")
    print("=" * 60)

    # 查找一个多人任务用于测试
    multi_person_tasks = LockTask.objects.filter(
        task_type='board',
        max_participants__gt=1,
        status__in=['open', 'taken', 'submitted']
    ).order_by('-created_at')

    if not multi_person_tasks.exists():
        print("❌ 没有找到可用的多人任务")
        return

    task = multi_person_tasks.first()
    print(f"📋 测试任务: {task.title} (ID: {task.id})")
    print(f"   状态: {task.status}")
    print(f"   最大参与者: {task.max_participants}")
    print()

    # 检查参与者
    participants = task.participants.all()
    print(f"👥 参与者数量: {participants.count()}")
    for p in participants:
        print(f"   {p.participant.username}: 状态={p.status}")
    print()

    # 检查现有文件
    existing_files = TaskSubmissionFile.objects.filter(task=task)
    print(f"📁 现有文件数量: {existing_files.count()}")
    for file in existing_files:
        print(f"   文件: {file.file_name}")
        print(f"     上传者: {file.uploader.username}")
        print(f"     关联参与者: {file.participant.participant.username if file.participant else '无'}")
        print(f"     是图片: {file.is_image}")
    print()

    # 测试API序列化
    print("🔧 测试API序列化:")
    test_users = ['admin', 'test', 'test1']

    for username in test_users:
        try:
            user = User.objects.get(username=username)
            mock_request = Mock()
            mock_request.user = user

            serializer = LockTaskSerializer(task, context={'request': mock_request})
            data = serializer.data

            total_files = sum(
                len(p.get('submission_files', []))
                for p in data.get('participants', [])
            )

            role = '发布者' if user == task.user else (
                '参与者' if task.participants.filter(participant=user).exists() else '非参与者'
            )
            print(f"   {username} ({role}): 可见 {total_files} 个文件")

        except User.DoesNotExist:
            print(f"   {username}: 用户不存在")

    print()
    print("✅ 测试完成")
    print()
    print("📝 说明:")
    print("   - 如果现有文件的'关联参与者'显示'无'，说明这些是旧文件")
    print("   - 新上传的文件应该自动关联到正确的参与者")
    print("   - 可以通过前端上传新文件来验证修复效果")

if __name__ == '__main__':
    test_file_upload_fix()