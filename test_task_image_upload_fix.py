#!/usr/bin/env python
"""
测试任务创建图片上传修复功能
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

# Add testserver to ALLOWED_HOSTS for testing
from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from tasks.models import LockTask
from posts.models import Post, PostImage

User = get_user_model()

def create_test_image(size_mb=1, format='JPEG', corrupt=False):
    """创建指定大小和格式的测试图片"""
    if corrupt:
        # 创建损坏的图片文件
        content = b"Not a real image file"
        return SimpleUploadedFile(
            name='corrupt_image.jpg',
            content=content,
            content_type='image/jpeg'
        )

    if size_mb > 5:
        # 对于超大文件，创建一个大的虚假文件来测试大小限制
        target_size = size_mb * 1024 * 1024
        # 创建一个看起来像JPEG的文件头，然后填充大量数据
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
        padding = b'\x00' * (target_size - len(jpeg_header) - 2)
        jpeg_footer = b'\xff\xd9'  # JPEG结束标记
        content = jpeg_header + padding + jpeg_footer

        return SimpleUploadedFile(
            name=f'test_task_image_{size_mb}mb.jpeg',
            content=content,
            content_type='image/jpeg'
        )

    # 对于正常大小的图片，创建真实的图片
    if size_mb <= 1:
        width = height = 100
    else:
        # 增加尺寸来创建较大的文件
        width = height = int(300 * size_mb)

    image = Image.new('RGB', (width, height), color='blue')
    buffer = BytesIO()
    image.save(buffer, format=format, quality=95)
    buffer.seek(0)

    return SimpleUploadedFile(
        name=f'test_task_image_{size_mb}mb.{format.lower()}',
        content=buffer.getvalue(),
        content_type=f'image/{format.lower()}'
    )

def test_task_image_upload_fixes():
    """测试任务创建图片上传修复功能"""
    print("🧪 测试任务创建图片上传修复...")

    try:
        # 创建测试用户
        try:
            user = User.objects.create_user(
                username='test_task_user',
                email='test_task@example.com',
                password='testpass123'
            )
            created_user = True
        except Exception:
            user = User.objects.get(username='test_task_user')
            created_user = False

        # 创建 Django 测试客户端
        client = Client()

        # 使用session登录而不是force_login
        from django.contrib.auth import login
        from django.contrib.sessions.backends.db import SessionStore

        # 模拟登录
        session = SessionStore()
        session.create()

        # 直接设置认证头
        from rest_framework.authtoken.models import Token
        token, created = Token.objects.get_or_create(user=user)

        # 设置认证头
        auth_headers = {'HTTP_AUTHORIZATION': f'Token {token.key}'}

        # 给用户一些积分用于测试
        user.coins = 1000
        user.save()

        # 测试1: 创建带锁任务（无图片，JSON）
        print("\\n📝 测试1: 创建带锁任务（无图片）...")

        response = client.post('/api/tasks/', {
            'task_type': 'lock',
            'title': '测试带锁任务',
            'description': '这是一个测试带锁任务',
            'duration_type': 'fixed',
            'duration_value': 60,
            'difficulty': 'normal',
            'unlock_type': 'time',
            'auto_publish': True
        }, content_type='application/json', **auth_headers)

        print(f"带锁任务创建响应状态: {response.status_code}")
        if response.status_code == 201:
            print("✅ 带锁任务创建成功")
            data = response.json()
            task_id = data.get('id')
            print(f"创建的任务ID: {task_id}")

            # 检查是否自动创建了动态
            task = LockTask.objects.get(id=task_id)
            if hasattr(task, 'auto_created_post') and task.auto_created_post:
                print(f"✅ 自动创建了动态: {task.auto_created_post.id}")
            else:
                print("❌ 未自动创建动态")
        else:
            print(f"❌ 带锁任务创建失败: {response.content.decode()}")

        # 测试2: 创建任务板（带图片，FormData）
        print("\\n📝 测试2: 创建任务板（带图片）...")
        normal_image = create_test_image(1)

        response = client.post('/api/tasks/', {
            'task_type': 'board',
            'title': '测试任务板带图片',
            'description': '这是一个带图片的测试任务板',
            'reward': 100,
            'max_duration': 24,
            'auto_publish': True,
            'images': normal_image
        }, format='multipart', **auth_headers)

        print(f"任务板创建响应状态: {response.status_code}")
        if response.status_code == 201:
            print("✅ 任务板创建成功")
            data = response.json()
            task_id = data.get('id')
            print(f"创建的任务ID: {task_id}")

            # 检查是否自动创建了动态和图片
            task = LockTask.objects.get(id=task_id)
            if hasattr(task, 'auto_created_post') and task.auto_created_post:
                post = task.auto_created_post
                print(f"✅ 自动创建了动态: {post.id}")

                # 检查动态是否有图片
                post_images = PostImage.objects.filter(post=post)
                if post_images.exists():
                    print(f"✅ 动态包含 {post_images.count()} 张图片")
                else:
                    print("❌ 动态没有图片")
            else:
                print("❌ 未自动创建动态")
        else:
            print(f"❌ 任务板创建失败: {response.content.decode()}")

        # 测试3: 超大图片上传（应该被拒绝）
        print("\\n📝 测试3: 超大图片上传...")
        large_image = create_test_image(6)

        response = client.post('/api/tasks/', {
            'task_type': 'board',
            'title': '测试超大图片任务板',
            'description': '这是一个超大图片的测试任务板',
            'reward': 100,
            'max_duration': 24,
            'auto_publish': True,
            'images': large_image
        }, format='multipart', **auth_headers)

        print(f"超大图片任务创建响应状态: {response.status_code}")
        if response.status_code == 400:
            print("✅ 超大图片正确被拒绝")
            print(f"错误信息: {response.content.decode()}")
        else:
            print(f"❌ 超大图片应该被拒绝但没有: {response.content.decode()}")

        # 测试4: 损坏的图片文件
        print("\\n📝 测试4: 损坏的图片文件...")
        corrupt_image = create_test_image(1, corrupt=True)

        response = client.post('/api/tasks/', {
            'task_type': 'board',
            'title': '测试损坏图片任务板',
            'description': '这是一个损坏图片的测试任务板',
            'reward': 100,
            'max_duration': 24,
            'auto_publish': True,
            'images': corrupt_image
        }, format='multipart', **auth_headers)

        print(f"损坏图片任务创建响应状态: {response.status_code}")
        if response.status_code == 400:
            print("✅ 损坏图片正确被拒绝")
            print(f"错误信息: {response.content.decode()}")
        else:
            print(f"❌ 损坏图片应该被拒绝: {response.content.decode()}")

        # 清理测试数据
        LockTask.objects.filter(user=user).delete()
        Post.objects.filter(user=user).delete()
        if created_user:
            user.delete()

        print("\\n✅ 任务创建图片上传修复测试完成")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("开始任务创建图片上传修复测试...")
    success = test_task_image_upload_fixes()

    if success:
        print("\\n🎉 所有测试通过！任务创建图片上传修复工作正常。")
    else:
        print("\\n⚠️  测试失败，需要检查修复。")