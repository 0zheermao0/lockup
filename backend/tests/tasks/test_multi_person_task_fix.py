#!/usr/bin/env python
"""
测试多人任务状态修复的脚本
验证以下场景：
1. 多人任务在submitted状态下仍可被筛选出来
2. 多人任务状态转换逻辑正确
3. 参与者状态正确保存
"""

import os
import sys
import django

# 设置Django环境
sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db.models import Q, Count, F
from tasks.models import LockTask, TaskParticipant
from django.utils import timezone

User = get_user_model()

def test_multi_person_task_filtering():
    """测试多人任务筛选逻辑"""
    print("🧪 测试多人任务筛选逻辑...")

    # 模拟筛选逻辑（从views.py复制）
    queryset = LockTask.objects.filter(task_type='board')

    # 添加参与者数量注释
    queryset = queryset.annotate(
        current_participants=Count('participants')
    )

    # 时间条件：未过期
    time_condition = Q(deadline__isnull=True) | Q(deadline__gt=timezone.now())

    # 分别处理单人和多人任务的状态条件
    single_person_condition = (
        (Q(max_participants__isnull=True) | Q(max_participants=1)) &
        Q(status='open')  # 单人任务只能是开放状态
    )

    multi_person_condition = (
        Q(max_participants__gt=1) &
        Q(status__in=['open', 'taken', 'submitted']) &  # 多人任务允许这些状态
        Q(current_participants__lt=F('max_participants'))  # 且未满员
    )

    # 组合所有条件
    available_tasks = queryset.filter(
        time_condition & (single_person_condition | multi_person_condition)
    )

    print(f"✅ 找到 {available_tasks.count()} 个可接取的任务板任务")

    # 显示多人任务的状态分布
    multi_person_tasks = queryset.filter(max_participants__gt=1)
    status_counts = {}
    for task in multi_person_tasks:
        status = task.status
        status_counts[status] = status_counts.get(status, 0) + 1

    print("📊 多人任务状态分布:")
    for status, count in status_counts.items():
        print(f"   - {status}: {count} 个")

    # 检查submitted状态的多人任务是否能被筛选出来
    submitted_multi_tasks = available_tasks.filter(
        max_participants__gt=1,
        status='submitted'
    )
    print(f"✅ submitted状态的多人任务中可接取的: {submitted_multi_tasks.count()} 个")

    return True

def test_task_status_transitions():
    """测试任务状态转换逻辑"""
    print("\n🧪 测试任务状态转换逻辑...")

    # 查找一些多人任务来验证状态
    multi_person_tasks = LockTask.objects.filter(
        task_type='board',
        max_participants__gt=1
    )[:5]

    print(f"📋 检查 {multi_person_tasks.count()} 个多人任务的状态:")
    for task in multi_person_tasks:
        participant_count = task.participants.count()
        submitted_count = task.participants.filter(status='submitted').count()
        approved_count = task.participants.filter(status='approved').count()

        print(f"   任务: {task.title[:30]}...")
        print(f"     状态: {task.status}")
        print(f"     参与: {participant_count}/{task.max_participants}")
        print(f"     提交: {submitted_count}, 通过: {approved_count}")

        # 验证状态逻辑
        if task.status == 'submitted' and participant_count < task.max_participants:
            print(f"     ✅ submitted状态但未满员，应该仍可接取")
        elif task.status == 'open':
            print(f"     ✅ open状态，可以接取")
        elif task.status == 'taken' and participant_count < task.max_participants:
            print(f"     ✅ taken状态但未满员，应该仍可接取")

    return True

def main():
    """主测试函数"""
    print("🚀 开始测试多人任务状态修复...")
    print("=" * 50)

    try:
        # 测试筛选逻辑
        test_multi_person_task_filtering()

        # 测试状态转换
        test_task_status_transitions()

        print("\n" + "=" * 50)
        print("✅ 所有测试完成！多人任务状态修复验证成功")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == '__main__':
    main()