#!/usr/bin/env python3
"""
测试API在认证情况下的工作状态
"""

import os
import sys
import django

# 设置Django环境
sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from tasks.models import LockTask, TaskParticipant
import requests

User = get_user_model()

def get_or_create_test_user():
    """获取或创建测试用户"""
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'is_active': True
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Created test user: {user.username}")

    # 获取或创建token
    token, created = Token.objects.get_or_create(user=user)
    return user, token.key

def test_api_with_auth():
    """测试API在认证情况下的工作状态"""

    # 获取测试用户和token
    user, token = get_or_create_test_user()

    print(f"Testing with user: {user.username}")
    print(f"Token: {token}")

    # 测试API端点
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json'
    }

    test_urls = [
        "http://localhost:8000/api/tasks/",
        "http://localhost:8000/api/tasks/?task_type=lock",
        "http://localhost:8000/api/tasks/?task_type=board",
        "http://localhost:8000/api/tasks/?task_type=lock&can_overtime=true&page=1&page_size=12&sort_by=user_activity&sort_order=desc",
    ]

    for url in test_urls:
        print(f"\nTesting: {url}")
        try:
            response = requests.get(url, headers=headers)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'results' in data:
                    print(f"Success: Got {len(data['results'])} tasks")
                elif isinstance(data, list):
                    print(f"Success: Got {len(data)} tasks")
                else:
                    print(f"Success: {data}")
            else:
                print(f"Error: {response.text}")

        except Exception as e:
            print(f"Request failed: {e}")

    # 测试数据库状态
    print(f"\nDatabase Status:")
    print(f"Total LockTasks: {LockTask.objects.count()}")
    print(f"Lock tasks: {LockTask.objects.filter(task_type='lock').count()}")
    print(f"Board tasks: {LockTask.objects.filter(task_type='board').count()}")
    print(f"TaskParticipants: {TaskParticipant.objects.count()}")

    # 检查多人任务
    multi_tasks = LockTask.objects.filter(max_participants__gt=1)
    print(f"Multi-participant tasks: {multi_tasks.count()}")

    for task in multi_tasks[:3]:  # 显示前3个多人任务
        print(f"  - {task.title}: {task.participants.count()}/{task.max_participants} participants")

if __name__ == "__main__":
    test_api_with_auth()