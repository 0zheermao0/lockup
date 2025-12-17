#!/usr/bin/env python
"""
测试前端数据格式是否正确
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask
from tasks.serializers import LockTaskSerializer
from django.contrib.auth import get_user_model
from unittest.mock import Mock
import json

User = get_user_model()

def test_frontend_data():
    """测试前端数据格式"""
    task_id = '9ffd36b9-f064-4a7c-b279-b435d58c3043'

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🎯 测试前端数据格式: {task.title}")
        print()

        # 模拟admin用户请求
        admin = User.objects.get(username='admin')
        mock_request = Mock()
        mock_request.user = admin

        # 序列化任务数据
        serializer = LockTaskSerializer(task, context={'request': mock_request})
        data = serializer.data

        print("📊 序列化数据结构:")
        print(f"   participants: {len(data.get('participants', []))} 个")
        print()

        # 检查每个参与者的数据
        for i, participant_data in enumerate(data.get('participants', [])):
            username = participant_data.get('participant', {}).get('username', 'Unknown')
            submission_files = participant_data.get('submission_files', [])

            print(f"👤 参与者 {i+1}: {username}")
            print(f"   submission_text: {participant_data.get('submission_text') is not None}")
            print(f"   submission_files: {len(submission_files)} 个")

            for j, file_data in enumerate(submission_files):
                print(f"     文件 {j+1}:")
                print(f"       id: {file_data.get('id')}")
                print(f"       file_url: {file_data.get('file_url')}")
                print(f"       file_type: {file_data.get('file_type')}")
                print(f"       is_image: {file_data.get('is_image')}")
                print(f"       is_primary: {file_data.get('is_primary')}")

            print()

        # 生成前端可以使用的JSON数据
        print("📝 生成前端测试数据:")
        frontend_data = {
            'task_id': str(task.id),
            'participants': []
        }

        for participant_data in data.get('participants', []):
            frontend_participant = {
                'username': participant_data.get('participant', {}).get('username'),
                'submission_files': participant_data.get('submission_files', [])
            }
            frontend_data['participants'].append(frontend_participant)

        print(json.dumps(frontend_data, indent=2, ensure_ascii=False))

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_frontend_data()