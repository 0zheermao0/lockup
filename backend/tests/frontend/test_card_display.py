#!/usr/bin/env python
"""
测试简化后的卡片显示数据
"""

import os
import sys
import django

# 设置Django环境
sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask

def test_card_display_data():
    """测试卡片显示数据"""
    print("🔍 检查多人任务卡片显示数据...")
    print("=" * 50)

    # 找到多人任务板任务
    multi_tasks = LockTask.objects.filter(
        task_type='board',
        max_participants__gt=1
    )[:5]

    if not multi_tasks.exists():
        print("❌ 没有找到多人任务")
        return

    for task in multi_tasks:
        participant_count = task.participants.count()
        submitted_count = task.participants.filter(status='submitted').count()
        approved_count = task.participants.filter(status='approved').count()

        print(f"📋 任务: {task.title[:30]}...")
        print(f"   状态: {task.status}")
        print(f"   参与者: {participant_count}/{task.max_participants}")
        print(f"   已提交: {submitted_count}")
        print(f"   已通过: {approved_count}")
        print(f"   奖励: {task.reward}")

        if task.reward and task.max_participants > 1:
            reward_per_person = task.reward // task.max_participants
            print(f"   每人奖励: {reward_per_person}")

        # 检查简化显示逻辑
        print(f"   简化显示:")
        print(f"     👥 {participant_count}/{task.max_participants}")
        if submitted_count > 0:
            print(f"     📤 {submitted_count}")
        if approved_count > 0:
            print(f"     ✅ {approved_count}")
        if task.reward and task.max_participants > 1:
            per_person = task.reward // task.max_participants
            print(f"     💰 {per_person}/人")
        print()

if __name__ == '__main__':
    test_card_display_data()