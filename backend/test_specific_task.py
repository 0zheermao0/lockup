#!/usr/bin/env python
"""
测试具体任务的操作按钮显示逻辑
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask
from django.contrib.auth import get_user_model

User = get_user_model()

def test_specific_task():
    """测试具体任务的按钮显示逻辑"""
    task_id = 'b4989c58-f7a6-4e09-b998-09fa5ca49f75'

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🎯 测试任务: {task.title}")
        print(f"   URL: http://localhost:5174/tasks/{task.id}")
        print(f"   状态: {task.status}")
        print(f"   类型: {task.task_type}")
        print(f"   发布者: {task.user.username}")
        print(f"   参与: {task.participants.count()}/{task.max_participants}")
        print()

        # 获取测试用户
        test_users = User.objects.exclude(username__in=['admin', task.user.username])[:2]

        for user in test_users:
            print(f"👤 测试用户: {user.username}")

            # 模拟前端 canClaimTask 逻辑
            can_claim = False
            if task.task_type == 'board' and task.user != user:
                # 模拟后端 can_take 逻辑
                is_participant = task.participants.filter(participant=user).exists()
                if not is_participant:
                    is_multi_person = task.max_participants and task.max_participants > 1
                    if is_multi_person:
                        if task.status in ['open', 'taken', 'submitted']:
                            current_participants = task.participants.count()
                            can_claim = current_participants < task.max_participants
                    else:
                        can_claim = task.status == 'open'

            print(f"   can_claim (前端逻辑): {can_claim}")

            # 模拟前端 canSubmitProof 逻辑
            can_submit = False
            if task.task_type == 'board' and task.user != user:
                is_multi_person = task.max_participants and task.max_participants > 1
                if is_multi_person:
                    is_participant_obj = task.participants.filter(participant=user).first()
                    if is_participant_obj and task.status in ['taken', 'submitted']:
                        can_submit = is_participant_obj.status not in ['submitted', 'approved']
                else:
                    can_submit = task.status == 'taken' and hasattr(task, 'taker') and task.taker == user

            print(f"   can_submit (前端逻辑): {can_submit}")
            print()

        # 检查已参与用户的情况
        print("👥 已参与用户:")
        for participant in task.participants.all():
            user = participant.participant
            print(f"   {user.username}:")

            # canClaimTask - 已参与用户不能再接取
            can_claim = False
            print(f"     can_claim: {can_claim} (已参与)")

            # canSubmitProof - 检查是否可以提交
            can_submit = False
            if task.task_type == 'board' and task.user != user:
                is_multi_person = task.max_participants and task.max_participants > 1
                if is_multi_person and task.status in ['taken', 'submitted']:
                    can_submit = participant.status not in ['submitted', 'approved']

            print(f"     can_submit: {can_submit} (参与状态: {participant.status})")
            print()

        print("🔍 前端按钮显示条件总结:")
        print("   揭榜任务按钮显示条件:")
        print("     - 不是自己发布的任务")
        print("     - 未参与过该任务")
        print("     - 多人任务: 状态为 open/taken/submitted 且未满员")
        print("     - 单人任务: 状态为 open")
        print()
        print("   提交证明按钮显示条件:")
        print("     - 不是自己发布的任务")
        print("     - 已参与该任务")
        print("     - 多人任务: 状态为 taken/submitted 且自己未提交")
        print("     - 单人任务: 状态为 taken 且自己是接取者")

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")

if __name__ == '__main__':
    test_specific_task()