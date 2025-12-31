#!/usr/bin/env python
"""
验证HTML链接修复效果
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask

def check_recent_tasks():
    """检查最近创建的任务中的HTML链接"""

    # 获取最近创建的有自动动态的任务
    recent_tasks = LockTask.objects.filter(
        auto_created_post__isnull=False
    ).order_by('-created_at')[:3]

    print("=== 检查最近任务的HTML链接格式 ===")

    for i, task in enumerate(recent_tasks, 1):
        print(f"\n{i}. 任务: {task.title}")
        print(f"   ID: {task.id}")
        print(f"   动态ID: {task.auto_created_post.id}")
        print(f"   描述长度: {len(task.description)}")

        # 检查HTML格式
        has_html_link = '<a href=' in task.description
        has_target_blank = 'target="_blank"' in task.description
        has_br_tags = '<br>' in task.description

        print(f"   ✓ HTML链接: {has_html_link}")
        print(f"   ✓ 新窗口打开: {has_target_blank}")
        print(f"   ✓ 换行标签: {has_br_tags}")

        # 显示链接部分
        if '📌' in task.description:
            link_part = task.description.split('📌')[1].strip()
            print(f"   链接部分: 📌{link_part[:100]}...")

        print(f"   状态: {'✅ 格式正确' if has_html_link and has_target_blank else '❌ 需要修复'}")

if __name__ == "__main__":
    check_recent_tasks()