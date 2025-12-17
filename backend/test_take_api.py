#!/usr/bin/env python
"""
测试take API修复
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskParticipant
from django.contrib.auth import get_user_model

User = get_user_model()

def test_take_api_logic():
    """测试take API逻辑"""
    task_id = 'b4989c58-f7a6-4e09-b998-09fa5ca49f75'

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🎯 测试任务: {task.title}")
        print(f"   状态: {task.status}")
        print(f"   参与: {task.participants.count()}/{task.max_participants}")
        print()

        # 获取测试用户
        test_user = User.objects.filter(username='testuser').first()
        if not test_user:
            print("❌ 找不到testuser用户")
            return

        print(f"👤 测试用户: {test_user.username}")
        print()

        # 模拟take API的检查逻辑
        print("🔍 take API检查逻辑:")

        # 1. 检查是否是任务板
        is_board = task.task_type == 'board'
        print(f"   1. is_board: {is_board}")

        # 2. 检查是否是自己发布的任务
        is_own_task = task.user == test_user
        print(f"   2. is_own_task: {is_own_task}")

        # 3. 检查是否已经参与过
        already_participated = TaskParticipant.objects.filter(task=task, participant=test_user).exists()
        print(f"   3. already_participated: {already_participated}")

        # 4. 判断是单人还是多人任务
        is_multi_person = task.max_participants and task.max_participants > 1
        print(f"   4. is_multi_person: {is_multi_person}")

        if is_multi_person:
            # 5. 检查任务状态（修复后应该包含'taken'）
            status_allowed = task.status in ['open', 'taken', 'submitted']
            print(f"   5. status_allowed: {status_allowed} (status: {task.status})")

            # 6. 检查是否已满员
            current_participants = TaskParticipant.objects.filter(task=task).count()
            not_full = current_participants < task.max_participants
            print(f"   6. not_full: {not_full} ({current_participants}/{task.max_participants})")

            # 最终结果
            can_take = (is_board and
                       not is_own_task and
                       not already_participated and
                       status_allowed and
                       not_full)
        else:
            # 单人任务逻辑
            can_take = (is_board and
                       not is_own_task and
                       not already_participated and
                       task.status == 'open')

        print()
        print(f"✅ 最终结果: can_take = {can_take}")

        if can_take:
            print("🎉 修复成功！用户应该可以接取任务")
        else:
            print("❌ 仍有问题，需要进一步检查")

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_take_api_logic()