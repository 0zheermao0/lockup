#!/usr/bin/env python
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from posts.models import Comment

def fix_comment_hierarchy():
    """Fix existing comment hierarchy data"""
    print("开始修复评论层级数据...")

    # 获取所有有parent的评论（回复评论）
    reply_comments = Comment.objects.filter(parent__isnull=False)

    print(f"找到 {reply_comments.count()} 个回复评论需要修复")

    for comment in reply_comments:
        print(f"修复评论 {comment.id}: {comment.content[:30]}...")

        # 找到根评论（第一层评论）
        root_comment = comment.parent
        while root_comment.parent is not None:
            root_comment = root_comment.parent

        # 设置正确的层级信息
        comment.depth = 1
        comment.root_reply_id = root_comment.id
        comment.reply_to_user = comment.parent.user
        comment.path = f"{root_comment.id}.{comment.id}"

        # 如果回复的不是第一层评论，修正parent指向
        if comment.parent.depth != 0:
            comment.parent = root_comment

        # 保存（不触发save方法的逻辑，直接更新数据库）
        Comment.objects.filter(id=comment.id).update(
            depth=comment.depth,
            root_reply_id=comment.root_reply_id,
            reply_to_user=comment.reply_to_user,
            path=comment.path,
            parent=comment.parent
        )

        print(f"  -> depth: {comment.depth}, root_reply_id: {comment.root_reply_id}, path: {comment.path}")

    # 修复第一层评论的path
    root_comments = Comment.objects.filter(parent__isnull=True)
    print(f"\n修复 {root_comments.count()} 个第一层评论的path...")

    for comment in root_comments:
        if comment.path != str(comment.id):
            Comment.objects.filter(id=comment.id).update(path=str(comment.id))
            print(f"修复第一层评论 {comment.id} 的path: {comment.id}")

    # 重新计算回复数
    print("\n重新计算回复数...")
    for root_comment in root_comments:
        replies_count = Comment.objects.filter(root_reply_id=root_comment.id).count()
        Comment.objects.filter(id=root_comment.id).update(replies_count=replies_count)
        if replies_count > 0:
            print(f"第一层评论 {root_comment.id} 有 {replies_count} 个回复")

    print("\n修复完成！")

    # 验证修复结果
    print("\n验证修复结果:")
    all_comments = Comment.objects.all().order_by('created_at')
    for comment in all_comments:
        print(f"ID: {comment.id}, Content: {comment.content[:30]}, Depth: {comment.depth}, Parent: {comment.parent_id}, Root: {comment.root_reply_id}, Path: {comment.path}")

if __name__ == "__main__":
    fix_comment_hierarchy()