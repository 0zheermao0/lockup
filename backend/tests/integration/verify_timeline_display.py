#!/usr/bin/env python
"""
验证时间线显示文本
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskTimelineEvent

def verify_timeline_display():
    """验证时间线显示文本"""
    print("🎯 验证时间线显示文本")
    print("=" * 40)
    print()

    # 查找已结束的任务的时间线事件
    ended_events = TaskTimelineEvent.objects.filter(event_type='task_ended').order_by('-created_at')[:10]

    if ended_events.exists():
        print(f"📋 找到 {ended_events.count()} 个任务结束事件:")
        print()

        for event in ended_events:
            print(f"🕐 时间: {event.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📋 任务: {event.task.title}")
            print(f"👤 操作者: {event.user.username if event.user else '系统'}")
            print(f"🏷️  事件类型: {event.event_type}")
            print(f"📝 描述: {event.description}")

            if event.metadata:
                print(f"📊 元数据:")
                for key, value in event.metadata.items():
                    print(f"     {key}: {value}")

            print()
            print("-" * 60)
            print()
    else:
        print("ℹ️  没有找到任务结束事件")

    # 检查事件类型的定义
    print("🔍 检查事件类型定义:")
    print("   task_ended: 任务被发布者结束 ✅")
    print("   task_completed: 任务正常完成")
    print("   task_failed: 任务失败")
    print()

    # 模拟时间线描述文本
    print("📝 时间线描述文本示例:")
    print("   ✅ 有审核通过的参与者:")
    print("      '任务被发布者结束：发布者手动结束任务。任务完成：2/3 人通过审核，积分已分配'")
    print()
    print("   ❌ 无人提交:")
    print("      '任务被发布者结束：发布者手动结束任务。任务失败：无人提交'")
    print()
    print("   ❌ 有提交但无人通过:")
    print("      '任务被发布者结束：发布者手动结束任务。任务失败：有 2 人提交但无人通过审核'")

if __name__ == '__main__':
    verify_timeline_display()