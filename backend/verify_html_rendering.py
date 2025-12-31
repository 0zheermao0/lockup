#!/usr/bin/env python
"""
验证HTML链接渲染效果
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask

def verify_html_rendering():
    """验证HTML链接渲染效果"""

    print("=== 验证HTML链接渲染效果 ===")

    # 获取一个包含HTML链接的任务
    task_with_html_link = LockTask.objects.filter(
        description__contains='<a href='
    ).first()

    if not task_with_html_link:
        print("❌ 没有找到包含HTML链接的任务")
        return

    print(f"\n任务: {task_with_html_link.title}")
    print(f"ID: {task_with_html_link.id}")
    print(f"创建时间: {task_with_html_link.created_at}")

    print(f"\n完整描述:")
    print(f"'{task_with_html_link.description}'")

    # 检查HTML链接的具体格式
    description = task_with_html_link.description

    # 查找HTML链接部分
    import re
    html_link_pattern = r'📌\s*<a href="([^"]+)" target="_blank"[^>]*>查看相关动态</a>'
    matches = re.findall(html_link_pattern, description)

    if matches:
        print(f"\n✅ 找到 {len(matches)} 个HTML格式链接:")
        for i, url in enumerate(matches, 1):
            print(f"  {i}. {url}")

        # 检查链接的具体HTML代码
        html_links = re.findall(r'📌\s*<a href="[^"]+[^>]*>查看相关动态</a>', description)
        print(f"\n📝 完整HTML链接代码:")
        for i, html_link in enumerate(html_links, 1):
            print(f"  {i}. {html_link}")

        # 验证链接属性
        print(f"\n🔍 链接属性验证:")
        for html_link in html_links:
            has_target_blank = 'target="_blank"' in html_link
            has_color_style = 'color: #007bff' in html_link
            has_text_decoration = 'text-decoration: none' in html_link

            print(f"  - target=\"_blank\": {'✅' if has_target_blank else '❌'}")
            print(f"  - 颜色样式: {'✅' if has_color_style else '❌'}")
            print(f"  - 文本装饰: {'✅' if has_text_decoration else '❌'}")

    else:
        print(f"\n❌ 没有找到HTML格式链接")

    # 检查是否有关联的动态
    if task_with_html_link.auto_created_post:
        print(f"\n🔗 关联动态:")
        post = task_with_html_link.auto_created_post
        print(f"  - 动态ID: {post.id}")
        # Post model doesn't have title field
        print(f"  - 动态内容: {post.content[:100]}...")
        print(f"  - 创建时间: {post.created_at}")
    else:
        print(f"\n⚠️  没有关联的动态")

    print(f"\n=== 验证完成 ===")

if __name__ == "__main__":
    verify_html_rendering()