#!/usr/bin/env python
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from posts.models import Comment

def fix_comment_hierarchy_v2():
    """Fix existing comment hierarchy data - version 2"""
    print("开始修复评论层级数据 v2...")

    # 获取所有评论
    all_comments = Comment.objects.all().order_by('created_at')
    print(f"总共有 {all_comments.count()} 个评论需要检查")

    fixed_count = 0

    for comment in all_comments:
        needs_fix = False
        updates = {}

        # 检查是否需要修复
        if comment.parent is None:
            # 第一层评论
            if comment.depth != 0 or comment.root_reply_id is not None:
                needs_fix = True
                updates.update({
                    'depth': 0,
                    'root_reply_id': None,
                    'reply_to_user': None,
                    'path': str(comment.id)
                })
        else:
            # 有parent的评论，应该是第二层
            try:
                parent_comment = Comment.objects.get(id=comment.parent.id)

                if parent_comment.depth == 0:
                    # 回复第一层评论
                    if (comment.depth != 1 or
                        comment.root_reply_id != parent_comment.id or
                        comment.reply_to_user != parent_comment.user):
                        needs_fix = True
                        updates.update({
                            'depth': 1,
                            'root_reply_id': parent_comment.id,
                            'reply_to_user': parent_comment.user,
                            'path': f"{parent_comment.id}.{comment.id}"
                        })
                else:
                    # 回复第二层评论，需要找到根评论并重新设置
                    root_comment = parent_comment
                    while root_comment.parent is not None:
                        try:
                            root_comment = Comment.objects.get(id=root_comment.parent.id)
                        except Comment.DoesNotExist:
                            break

                    if root_comment.depth == 0:  # 确保找到了有效的根评论
                        if (comment.depth != 1 or
                            comment.root_reply_id != root_comment.id or
                            comment.reply_to_user != parent_comment.user or
                            comment.parent.id != root_comment.id):
                            needs_fix = True
                            updates.update({
                                'depth': 1,
                                'root_reply_id': root_comment.id,
                                'reply_to_user': parent_comment.user,
                                'parent': root_comment,
                                'path': f"{root_comment.id}.{comment.id}"
                            })
                    else:
                        # 如果找不到有效的根评论，作为第一层评论处理
                        needs_fix = True
                        updates.update({
                            'depth': 0,
                            'root_reply_id': None,
                            'reply_to_user': None,
                            'parent': None,
                            'path': str(comment.id)
                        })

            except Comment.DoesNotExist:
                # parent不存在，作为第一层评论处理
                needs_fix = True
                updates.update({
                    'depth': 0,
                    'root_reply_id': None,
                    'reply_to_user': None,
                    'parent': None,
                    'path': str(comment.id)
                })

        if needs_fix:
            print(f"修复评论 {comment.id}: {comment.content[:30]}...")
            print(f"  原始数据: depth={comment.depth}, parent={comment.parent_id}, root={comment.root_reply_id}")

            # 使用update避免触发save方法
            Comment.objects.filter(id=comment.id).update(**updates)
            fixed_count += 1

            print(f"  修复后: {updates}")

    print(f"\n修复完成！共修复了 {fixed_count} 个评论")

    # 重新计算回复数
    print("\n重新计算回复数...")
    root_comments = Comment.objects.filter(depth=0)
    for root_comment in root_comments:
        replies_count = Comment.objects.filter(root_reply_id=root_comment.id).count()
        if root_comment.replies_count != replies_count:
            Comment.objects.filter(id=root_comment.id).update(replies_count=replies_count)
            print(f"更新第一层评论 {root_comment.id} 的回复数: {replies_count}")

    print("\n验证修复结果:")
    # 验证修复结果
    all_comments = Comment.objects.all().order_by('created_at')
    for comment in all_comments:
        status = "✓" if (
            (comment.parent is None and comment.depth == 0 and comment.root_reply_id is None) or
            (comment.parent is not None and comment.depth == 1 and comment.root_reply_id is not None)
        ) else "✗"
        print(f"{status} ID: {comment.id}, Content: {comment.content[:30]}, Depth: {comment.depth}, Parent: {comment.parent_id}, Root: {comment.root_reply_id}")

if __name__ == "__main__":
    fix_comment_hierarchy_v2()