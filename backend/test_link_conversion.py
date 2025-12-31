#!/usr/bin/env python
"""
测试链接转换结果
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask

def test_link_conversion():
    """测试链接转换结果"""

    print("=== 检查所有包含动态链接的任务 ===")

    # 查找所有包含链接的任务
    tasks_with_links = LockTask.objects.filter(
        description__contains='📌'
    ).order_by('-created_at')

    print(f"\n找到 {tasks_with_links.count()} 个包含链接的任务:")

    markdown_count = 0
    html_count = 0

    for i, task in enumerate(tasks_with_links, 1):
        print(f"\n{i}. 任务: {task.title}")
        print(f"   ID: {task.id}")
        print(f"   创建时间: {task.created_at}")

        # 检查链接格式
        has_markdown_link = '[查看相关动态]' in task.description
        has_html_link = '<a href=' in task.description and '查看相关动态</a>' in task.description

        if has_markdown_link:
            print(f"   ❌ 链接格式: Markdown (需要转换)")
            markdown_count += 1
            # 显示Markdown链接部分
            if '📌' in task.description:
                link_part = task.description.split('📌')[1].strip()
                print(f"   链接内容: 📌{link_part[:100]}...")
        elif has_html_link:
            print(f"   ✅ 链接格式: HTML (已转换)")
            html_count += 1
            # 显示HTML链接部分
            if '📌' in task.description:
                link_part = task.description.split('📌')[1].strip()
                print(f"   链接内容: 📌{link_part[:100]}...")
        else:
            print(f"   ⚠️  链接格式: 未识别")
            # 显示完整链接部分
            if '📌' in task.description:
                link_part = task.description.split('📌')[1].strip()
                print(f"   链接内容: 📌{link_part}")

    print(f"\n=== 统计结果 ===")
    print(f"Markdown格式链接: {markdown_count} 个")
    print(f"HTML格式链接: {html_count} 个")
    print(f"总计: {markdown_count + html_count} 个")

    if markdown_count == 0:
        print("✅ 所有链接都已成功转换为HTML格式！")
    else:
        print(f"❌ 还有 {markdown_count} 个链接需要转换")

if __name__ == "__main__":
    test_link_conversion()