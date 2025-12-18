#!/usr/bin/env python
"""
测试多人任务的接取和提交操作逻辑
"""

import os
import sys
import django

# 设置Django环境
sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from tasks.models import LockTask, TaskParticipant
from tasks.serializers import LockTaskSerializer
from django.test import RequestFactory
from unittest.mock import Mock

User = get_user_model()

def test_multi_task_operations():
    """测试多人任务操作逻辑"""
    print("🧪 测试多人任务接取和提交操作逻辑...")
    print("=" * 60)

    # 获取一些用户
    users = list(User.objects.all()[:3])
    if len(users) < 3:
        print("❌ 需要至少3个用户来测试")
        return

    publisher, user1, user2 = users[:3]

    # 找一个多人任务
    multi_task = LockTask.objects.filter(
        task_type='board',
        max_participants__gt=1
    ).first()

    if not multi_task:
        print("❌ 没有找到多人任务")
        return

    print(f"📋 测试任务: {multi_task.title}")
    print(f"   发布者: {multi_task.user.username}")
    print(f"   最大参与者: {multi_task.max_participants}")
    print(f"   当前状态: {multi_task.status}")
    print()

    # 模拟不同用户的请求上下文
    factory = RequestFactory()

    def test_user_permissions(user, task):
        """测试特定用户的权限"""
        print(f"👤 用户 {user.username}:")

        # 检查是否已参与
        is_participant = task.participants.filter(participant=user).exists()
        print(f"   已参与: {is_participant}")

        if is_participant:
            participant = task.participants.filter(participant=user).first()
            print(f"   参与状态: {participant.status}")

        # 检查前端逻辑（模拟）
        is_publisher = task.user.id == user.id
        is_multi_person = task.max_participants and task.max_participants > 1

        # 模拟后端 can_take 逻辑
        can_take = False
        if not is_publisher and not is_participant:
            if is_multi_person:
                if task.status in ['open', 'submitted']:
                    current_participants = task.participants.count()
                    can_take = current_participants < task.max_participants
            else:
                can_take = task.status == 'open'

        print(f"   can_take (后端逻辑): {can_take}")

        # 模拟修复后的 canSubmitProof 逻辑
        can_submit = False
        if task.task_type == 'board' and not is_publisher and is_multi_person:
            is_participant_obj = task.participants.filter(participant=user).first()
            if is_participant_obj and task.status in ['taken', 'submitted']:
                can_submit = is_participant_obj.status not in ['submitted', 'approved']

        print(f"   can_submit (修复后前端逻辑): {can_submit}")
        print()

    # 测试发布者
    print("🔍 测试各用户权限:")
    test_user_permissions(multi_task.user, multi_task)

    # 测试其他用户
    for user in [user1, user2]:
        if user.id != multi_task.user.id:
            test_user_permissions(user, multi_task)

    # 显示任务当前参与情况
    print("📊 当前参与情况:")
    participants = multi_task.participants.all()
    if participants:
        for p in participants:
            print(f"   - {p.participant.username}: {p.status}")
    else:
        print("   无参与者")

    print(f"\n✅ 测试完成")
    print(f"📈 关键发现:")
    print(f"   - 任务状态: {multi_task.status}")
    print(f"   - 参与人数: {multi_task.participants.count()}/{multi_task.max_participants}")
    print(f"   - 已提交人数: {multi_task.participants.filter(status='submitted').count()}")

if __name__ == '__main__':
    test_multi_task_operations()