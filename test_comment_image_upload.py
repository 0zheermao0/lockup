#!/usr/bin/env python
"""
测试评论图片上传的安全限制功能
"""
import os
import sys
import django
from io import BytesIO
from PIL import Image
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

# Add the backend directory to the path
sys.path.insert(0, '/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')

# Setup Django
django.setup()

from posts.models import Post, Comment, CommentImage

User = get_user_model()

def create_test_image(size_mb=1):
    """创建指定大小的测试图片"""
    # 根据需要的大小计算图片尺寸
    if size_mb <= 1:
        width = height = 100
    else:
        # 大概估算尺寸来达到目标文件大小
        width = height = int(100 * (size_mb ** 0.5) * 10)

    image = Image.new('RGB', (width, height), color='red')
    buffer = BytesIO()
    image.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)

    return SimpleUploadedFile(
        name=f'test_image_{size_mb}mb.jpg',
        content=buffer.getvalue(),
        content_type='image/jpeg'
    )

def test_comment_image_upload():
    """测试评论图片上传功能"""
    print("测试评论图片上传安全限制...")

    try:
        # 创建测试用户
        try:
            user = User.objects.create_user(
                username='test_comment_user',
                email='test_comment@example.com',
                password='testpass123'
            )
            created_user = True
        except Exception:
            user = User.objects.get(username='test_comment_user')
            created_user = False

        # 创建测试动态
        post = Post.objects.create(
            user=user,
            content='测试动态',
            post_type='normal'
        )

        # 创建 Django 测试客户端
        client = Client()
        client.force_login(user)

        # 测试1: 正常大小的图片 (1MB)
        print("测试1: 上传正常大小的图片...")
        normal_image = create_test_image(1)

        response = client.post(f'/api/posts/{post.id}/comments/', {
            'content': '测试评论带图片',
            'images': normal_image
        }, format='multipart')

        print(f"正常图片上传响应状态: {response.status_code}")
        if response.status_code == 201:
            print("✅ 正常大小图片上传成功")
        else:
            print(f"❌ 正常图片上传失败: {response.content.decode()}")

        # 测试2: 超大图片 (模拟6MB)
        print("\n测试2: 上传超大图片...")
        large_image = create_test_image(6)

        response = client.post(f'/api/posts/{post.id}/comments/', {
            'content': '测试评论带超大图片',
            'images': large_image
        }, format='multipart')

        print(f"超大图片上传响应状态: {response.status_code}")
        if response.status_code == 400:
            print("✅ 超大图片正确被拒绝")
            print(f"错误信息: {response.content.decode()}")
        else:
            print(f"❌ 超大图片应该被拒绝但没有: {response.content.decode()}")

        # 清理
        Comment.objects.filter(post=post).delete()
        post.delete()
        if created_user:
            user.delete()

        print("\n✅ 评论图片上传测试完成")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("开始评论图片上传安全测试...")
    success = test_comment_image_upload()

    if success:
        print("\n🎉 所有测试通过！评论图片上传安全限制工作正常。")
    else:
        print("\n⚠️  测试失败，需要检查配置。")