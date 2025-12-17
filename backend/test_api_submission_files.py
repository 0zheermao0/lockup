#!/usr/bin/env python
"""
测试API返回的提交文件数据
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
from unittest.mock import Mock

User = get_user_model()

def test_api_submission_files():
    """测试API返回的提交文件数据"""
    task_id = '9ffd36b9-f064-4a7c-b279-b435d58c3043'

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🎯 测试任务: {task.title}")
        print()

        # 测试不同用户的权限
        test_users = [
            ('admin', '发布者'),
            ('test', '参与者'),
            ('testuser', '非参与者')
        ]

        for username, role in test_users:
            user = User.objects.filter(username=username).first()
            if not user:
                print(f"❌ 找不到用户: {username}")
                continue

            print(f"👤 测试用户: {username} ({role})")

            # 创建模拟请求
            mock_request = Mock()
            mock_request.user = user

            # 序列化任务
            serializer = LockTaskSerializer(task, context={'request': mock_request})
            data = serializer.data

            # 检查participants字段
            participants_data = data.get('participants', [])
            print(f"   参与者数据: {len(participants_data)} 个")

            for participant_data in participants_data:
                participant_username = participant_data.get('participant', {}).get('username', 'Unknown')
                submission_files = participant_data.get('submission_files', [])
                submission_text = participant_data.get('submission_text')

                print(f"     参与者 {participant_username}:")
                print(f"       submission_text: {'有' if submission_text else '无'}")
                print(f"       submission_files: {len(submission_files)} 个")

                if submission_files:
                    for file_data in submission_files:
                        print(f"         - 文件名: {file_data.get('file_name', 'Unknown')}")
                        print(f"           类型: {file_data.get('file_type', 'Unknown')}")
                        print(f"           是图片: {file_data.get('is_image', False)}")
                        print(f"           URL: {file_data.get('file_url', 'No URL')}")
                        print(f"           是主要文件: {file_data.get('is_primary', False)}")

            print()

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_api_submission_files()