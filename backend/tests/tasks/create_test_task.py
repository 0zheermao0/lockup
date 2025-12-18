#!/usr/bin/env python
"""
创建一个测试任务来验证结束逻辑
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskParticipant
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

def create_test_task():
    """创建测试任务"""
    print("🎯 创建测试任务")
    print("=" * 30)

    # 获取发布者
    publisher = User.objects.filter(username='test').first()
    if not publisher:
        print("❌ 找不到test用户")
        return

    # 创建多人任务
    task = LockTask.objects.create(
        user=publisher,
        task_type='board',
        title='测试任务结束逻辑',
        description='用于测试任务结束逻辑和奖励分配',
        status='taken',
        reward=100,
        max_participants=3,
        max_duration=24,
        deadline=timezone.now() + timezone.timedelta(days=1)
    )

    print(f"✅ 创建任务: {task.title}")
    print(f"   ID: {task.id}")
    print(f"   奖励: {task.reward} 积分")
    print(f"   最大参与者: {task.max_participants} 人")
    print()

    # 添加参与者
    participants = ['admin', 'test1', 'test2']

    for i, username in enumerate(participants):
        user = User.objects.filter(username=username).first()
        if user:
            participant = TaskParticipant.objects.create(
                task=task,
                participant=user,
                status='approved' if i < 2 else 'submitted'  # 前两个审核通过，最后一个只提交
            )

            status_text = '审核通过' if i < 2 else '已提交'
            print(f"   + 添加参与者: {username} ({status_text})")

    print()
    print(f"🎯 测试URL: http://localhost:5174/tasks/{task.id}")
    print(f"📋 任务状态: {task.status}")
    print(f"👥 参与情况: {task.participants.count()}/{task.max_participants}")
    print(f"✅ 审核通过: {task.participants.filter(status='approved').count()} 人")
    print(f"📤 已提交: {task.participants.filter(status='submitted').count()} 人")
    print()
    print("现在可以用发布者账号（test）测试结束任务功能")

if __name__ == '__main__':
    create_test_task()