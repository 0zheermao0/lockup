#!/usr/bin/env python
"""
调试API响应，检查can_take字段是否正确返回
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
from django.test import RequestFactory
import json

User = get_user_model()

def debug_api_response():
    """调试API响应"""
    task_id = 'b4989c58-f7a6-4e09-b998-09fa5ca49f75'

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🔍 调试任务API响应: {task.title}")
        print(f"   ID: {task.id}")
        print()

        # 获取测试用户
        test_user = User.objects.filter(username='testuser').first()
        if not test_user:
            print("❌ 找不到testuser用户")
            return

        print(f"👤 测试用户: {test_user.username}")
        print()

        # 创建模拟请求
        factory = RequestFactory()
        request = factory.get('/')
        request.user = test_user

        # 序列化任务
        serializer = LockTaskSerializer(task, context={'request': request})
        data = serializer.data

        # 检查关键字段
        print("📊 序列化器返回的关键字段:")
        key_fields = [
            'id', 'task_type', 'status', 'max_participants',
            'participant_count', 'can_take'
        ]

        for field in key_fields:
            value = data.get(field, 'MISSING')
            print(f"   {field}: {value}")

        print()
        print("🔍 can_take字段详细分析:")

        # 手动计算can_take
        is_board = task.task_type == 'board'
        is_own_task = task.user == test_user
        is_participant = task.participants.filter(participant=test_user).exists()
        is_multi_person = task.max_participants and task.max_participants > 1
        current_participants = task.participants.count()
        status_allowed = task.status in ['open', 'taken', 'submitted']
        not_full = current_participants < task.max_participants

        print(f"   is_board: {is_board}")
        print(f"   is_own_task: {is_own_task}")
        print(f"   is_participant: {is_participant}")
        print(f"   is_multi_person: {is_multi_person}")
        print(f"   status_allowed: {status_allowed} (status: {task.status})")
        print(f"   not_full: {not_full} ({current_participants}/{task.max_participants})")

        expected_can_take = (
            is_board and
            not is_own_task and
            not is_participant and
            is_multi_person and
            status_allowed and
            not_full
        )

        print(f"   expected_can_take: {expected_can_take}")
        print(f"   actual_can_take: {data.get('can_take')}")

        if expected_can_take != data.get('can_take'):
            print("   ⚠️  计算结果不匹配！")
        else:
            print("   ✅ 计算结果匹配")

        # 检查participants字段
        print()
        print("👥 参与者信息:")
        participants = data.get('participants', [])
        print(f"   participants字段长度: {len(participants)}")
        for p in participants:
            print(f"   - {p.get('participant', {}).get('username', 'Unknown')}: {p.get('status', 'Unknown')}")

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_api_response()