#!/usr/bin/env python
"""
测试"我接取的"筛选功能修复
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskParticipant
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

def test_my_taken_filter():
    """测试我接取的筛选功能"""

    # 测试用户
    test_users = ['admin', 'test1', 'test2', 'test3']

    print("🎯 测试'我接取的'筛选功能修复")
    print("=" * 50)
    print()

    for username in test_users:
        user = User.objects.filter(username=username).first()
        if not user:
            print(f"❌ 找不到用户: {username}")
            continue

        print(f"👤 用户: {username}")
        print()

        # 修复前的逻辑（只查taker）
        old_logic_tasks = LockTask.objects.filter(
            task_type='board',
            taker=user
        )

        # 修复后的逻辑（支持多人任务）
        new_logic_tasks = LockTask.objects.filter(
            task_type='board'
        ).filter(
            Q(taker=user) |  # 单人任务：我是taker
            Q(participants__participant=user)  # 多人任务：我是参与者
        ).distinct()

        print(f"   修复前逻辑找到: {old_logic_tasks.count()} 个任务")
        print(f"   修复后逻辑找到: {new_logic_tasks.count()} 个任务")

        if new_logic_tasks.count() > old_logic_tasks.count():
            print(f"   ✅ 修复有效！新增了 {new_logic_tasks.count() - old_logic_tasks.count()} 个多人任务")

            # 显示新增的任务
            new_tasks = new_logic_tasks.exclude(id__in=old_logic_tasks.values('id'))
            for task in new_tasks:
                print(f"     + 多人任务: {task.title} (状态: {task.status})")
                # 检查用户在该任务中的参与状态
                participant = TaskParticipant.objects.filter(task=task, participant=user).first()
                if participant:
                    print(f"       参与状态: {participant.status}")
        else:
            print("   ℹ️  没有新增任务（用户可能没有参与多人任务）")

        print()

    print("🔍 多人任务参与情况总览:")
    multi_person_tasks = LockTask.objects.filter(
        task_type='board',
        max_participants__gt=1
    )

    for task in multi_person_tasks:
        print(f"   任务: {task.title}")
        print(f"     状态: {task.status}")
        print(f"     参与者: {task.participants.count()}/{task.max_participants}")

        participants = task.participants.all()
        for p in participants:
            print(f"       - {p.participant.username}: {p.status}")
        print()

def test_api_counts():
    """测试API计数功能"""
    print("🔢 测试API计数功能")
    print("=" * 30)

    # 模拟不同用户的计数
    test_users = ['admin', 'test1', 'test2', 'test3']

    for username in test_users:
        user = User.objects.filter(username=username).first()
        if not user:
            continue

        board_tasks = LockTask.objects.filter(task_type='board')

        # 修复前的计数
        old_count = board_tasks.filter(taker=user).count()

        # 修复后的计数
        new_count = board_tasks.filter(
            Q(taker=user) |
            Q(participants__participant=user)
        ).distinct().count()

        print(f"👤 {username}:")
        print(f"   修复前 my_taken 计数: {old_count}")
        print(f"   修复后 my_taken 计数: {new_count}")
        print()

if __name__ == '__main__':
    test_my_taken_filter()
    print()
    test_api_counts()