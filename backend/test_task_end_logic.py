#!/usr/bin/env python
"""
测试任务结束逻辑修复
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskParticipant
from django.contrib.auth import get_user_model
import math

User = get_user_model()

def test_task_end_logic():
    """测试任务结束逻辑"""
    print("🎯 测试任务结束逻辑修复")
    print("=" * 50)
    print()

    # 查找多人任务进行测试
    multi_person_tasks = LockTask.objects.filter(
        task_type='board',
        max_participants__gt=1
    ).exclude(status__in=['completed', 'failed'])

    print(f"🔍 找到 {multi_person_tasks.count()} 个可测试的多人任务")
    print()

    for task in multi_person_tasks[:3]:  # 只测试前3个
        print(f"📋 任务: {task.title}")
        print(f"   状态: {task.status}")
        print(f"   奖励: {task.reward} 积分")
        print(f"   参与: {task.participants.count()}/{task.max_participants}")

        participants = task.participants.all()
        submitted_participants = participants.filter(status='submitted')
        approved_participants = participants.filter(status='approved')

        print(f"   已提交: {submitted_participants.count()} 人")
        print(f"   已审核通过: {approved_participants.count()} 人")

        # 显示参与者状态
        for p in participants:
            print(f"     - {p.participant.username}: {p.status}")

        print()

        # 模拟结束逻辑判断
        print("🔍 模拟结束逻辑判断:")

        if approved_participants.count() == 0:
            if submitted_participants.count() == 0:
                print("   ❌ 结果: 任务失败（无人提交）")
                print("   💰 奖励: 返还给发布者")
            else:
                print("   ❌ 结果: 任务失败（有人提交但无人通过审核）")
                print("   💰 奖励: 返还给发布者")
        else:
            print("   ✅ 结果: 任务完成")
            if task.reward:
                reward_per_person = math.ceil(task.reward / approved_participants.count())
                total_distributed = reward_per_person * approved_participants.count()
                print(f"   💰 奖励分配: 每人 {reward_per_person} 积分（向上取整）")
                print(f"   📊 总分配: {total_distributed} 积分（原奖励: {task.reward}）")
                if total_distributed > task.reward:
                    print(f"   ⚠️  超出原奖励: +{total_distributed - task.reward} 积分")

        print()
        print("-" * 40)
        print()

def test_reward_calculation():
    """测试奖励计算逻辑"""
    print("🧮 测试奖励计算逻辑（向上取整）")
    print("=" * 40)
    print()

    test_cases = [
        (100, 3),  # 100积分分给3人
        (50, 3),   # 50积分分给3人
        (10, 3),   # 10积分分给3人
        (7, 4),    # 7积分分给4人
        (1, 3),    # 1积分分给3人
    ]

    for reward, participants in test_cases:
        reward_per_person = math.ceil(reward / participants)
        total_distributed = reward_per_person * participants

        print(f"📊 原奖励: {reward} 积分，参与者: {participants} 人")
        print(f"   每人获得: {reward_per_person} 积分")
        print(f"   总分配: {total_distributed} 积分")
        if total_distributed > reward:
            print(f"   超出原奖励: +{total_distributed - reward} 积分")
        print()

if __name__ == '__main__':
    test_task_end_logic()
    print()
    test_reward_calculation()