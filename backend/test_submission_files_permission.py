#!/usr/bin/env python
"""
测试提交文件权限修复
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskParticipant
from tasks.serializers import LockTaskSerializer
from django.contrib.auth import get_user_model
from django.test import RequestFactory

User = get_user_model()

def test_submission_files_permission():
    """测试提交文件权限"""
    task_id = 'b4989c58-f7a6-4e09-b998-09fa5ca49f75'

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🎯 测试任务: {task.title}")
        print(f"   发布者: {task.user.username}")
        print(f"   参与者数量: {task.participants.count()}")
        print()

        # 获取参与者
        participants = task.participants.all()
        for p in participants:
            print(f"   参与者: {p.participant.username}, 状态: {p.status}")

        print()

        # 测试不同用户的权限
        test_users = [
            ('admin', '参与者'),
            ('testuser', '非参与者'),
            (task.user.username, '发布者')
        ]

        factory = RequestFactory()

        for username, role in test_users:
            user = User.objects.filter(username=username).first()
            if not user:
                print(f"❌ 找不到用户: {username}")
                continue

            print(f"👤 测试用户: {username} ({role})")

            # 创建模拟请求
            request = factory.get('/')
            request.user = user

            # 序列化任务
            serializer = LockTaskSerializer(task, context={'request': request})
            data = serializer.data

            # 检查participants字段中的submission_files
            participants_data = data.get('participants', [])
            print(f"   参与者数据长度: {len(participants_data)}")

            for i, participant_data in enumerate(participants_data):
                participant_username = participant_data.get('participant', {}).get('username', 'Unknown')
                submission_files = participant_data.get('submission_files', [])
                submission_text = participant_data.get('submission_text')

                print(f"     参与者 {participant_username}:")
                print(f"       submission_text: {'有' if submission_text else '无'}")
                print(f"       submission_files: {len(submission_files)} 个文件")

                if submission_files:
                    for file_data in submission_files:
                        print(f"         - {file_data.get('file_name', 'Unknown')} ({file_data.get('file_type', 'Unknown')})")

            print()

        print("🎯 权限测试总结:")
        print("   发布者应该能看到所有参与者的提交文件")
        print("   参与者应该能看到所有参与者的提交文件")
        print("   非参与者不应该看到提交文件")

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_submission_files_permission()