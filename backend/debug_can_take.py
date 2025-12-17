#!/usr/bin/env python
"""
直接测试can_take逻辑
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

User = get_user_model()

def debug_can_take():
    """直接测试can_take逻辑"""
    task_id = 'b4989c58-f7a6-4e09-b998-09fa5ca49f75'

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🔍 调试can_take逻辑: {task.title}")
        print()

        # 获取测试用户
        test_user = User.objects.filter(username='testuser').first()
        if not test_user:
            print("❌ 找不到testuser用户")
            return

        print(f"👤 测试用户: {test_user.username}")
        print()

        # 创建模拟请求上下文
        mock_request = Mock()
        mock_request.user = test_user

        # 创建序列化器实例
        serializer = LockTaskSerializer()
        serializer.context = {'request': mock_request}

        # 直接调用get_can_take方法
        can_take_result = serializer.get_can_take(task)

        print("🔍 get_can_take方法调试:")
        print(f"   返回值: {can_take_result}")
        print()

        # 手动验证逻辑
        print("📋 手动验证条件:")
        print(f"   request.user存在: {mock_request.user is not None}")
        print(f"   request.user已认证: {True}")  # 模拟已认证
        print(f"   task.user != user: {task.user != test_user}")
        print(f"   已参与: {task.participants.filter(participant=test_user).exists()}")

        is_multi_person = task.max_participants and task.max_participants > 1
        print(f"   is_multi_person: {is_multi_person}")

        if is_multi_person:
            status_ok = task.status in ['open', 'submitted']  # 注意：这里应该包含'taken'
            current_participants = task.participants.count()
            not_full = current_participants < task.max_participants

            print(f"   status in ['open', 'submitted']: {status_ok}")
            print(f"   实际status: {task.status}")
            print(f"   current_participants < max_participants: {not_full} ({current_participants}/{task.max_participants})")

        print()
        print("❗ 发现问题:")
        print("   后端serializers.py中的get_can_take方法第164行:")
        print("   if obj.status not in ['open', 'submitted']:")
        print("   这里缺少了'taken'状态！")
        print()
        print("   当前任务状态是'taken'，但逻辑中只允许'open'和'submitted'")
        print("   这就是为什么can_take返回False的原因")

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_can_take()