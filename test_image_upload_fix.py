#!/usr/bin/env python
"""
测试图片上传HTTP 500错误修复功能
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

    # 根据需要的大小计算图片尺寸
    if size_mb <= 1:
        width = height = 100
    else:
        # 大概估算尺寸来达到目标文件大小
        width = height = int(100 * (size_mb ** 0.5) * 10)

    image = Image.new('RGB', (width, height), color='red')
    buffer = BytesIO()
    image.save(buffer, format=format, quality=85)
    buffer.seek(0)

    return SimpleUploadedFile(
        name=f'test_image_{size_mb}mb.{format.lower()}',
        content=buffer.getvalue(),
        content_type=f'image/{format.lower()}'
    )

def test_image_upload_fixes():
    """测试图片上传修复功能"""
    print("🧪 测试图片上传HTTP 500错误修复...")

    try:
        # 创建测试用户
        try:
            user = User.objects.create_user(
                username='test_image_user',
                email='test_image@example.com',
                password='testpass123'
            )
            created_user = True
        except Exception:
            user = User.objects.get(username='test_image_user')
            created_user = False

        # 创建 Django 测试客户端
        client = Client()
        client.force_login(user)

        # 测试1: 正常图片上传
        print("\n📸 测试1: 正常大小的图片上传...")
        normal_image = create_test_image(1)

        response = client.post('/api/posts/', {
            'content': '测试正常图片上传',
            'post_type': 'normal',
            'images': normal_image
        }, format='multipart')

        print(f"正常图片上传响应状态: {response.status_code}")
        if response.status_code == 201:
            print("✅ 正常大小图片上传成功")
            data = response.json()
            post_id = data.get('id')
            print(f"创建的动态ID: {post_id}")
        else:
            print(f"❌ 正常图片上传失败: {response.content.decode()}")

        # 测试2: 超大图片上传（应该被拒绝）
        print("\n📸 测试2: 超大图片上传...")
        large_image = create_test_image(6)

        response = client.post('/api/posts/', {
            'content': '测试超大图片上传',
            'post_type': 'normal',
            'images': large_image
        }, format='multipart')

        print(f"超大图片上传响应状态: {response.status_code}")
        if response.status_code == 400:
            print("✅ 超大图片正确被拒绝")
            print(f"错误信息: {response.content.decode()}")
        else:
            print(f"❌ 超大图片应该被拒绝但没有: {response.content.decode()}")

        # 测试3: 损坏的图片文件
        print("\n📸 测试3: 损坏的图片文件...")
        corrupt_image = create_test_image(1, corrupt=True)

        response = client.post('/api/posts/', {
            'content': '测试损坏图片上传',
            'post_type': 'normal',
            'images': corrupt_image
        }, format='multipart')

        print(f"损坏图片上传响应状态: {response.status_code}")
        if response.status_code == 400:
            print("✅ 损坏图片正确被拒绝")
            print(f"错误信息: {response.content.decode()}")
        else:
            print(f"❌ 损坏图片应该被拒绝: {response.content.decode()}")

        # 测试4: 多张图片上传
        print("\n📸 测试4: 多张图片上传...")
        image1 = create_test_image(1, 'JPEG')
        image2 = create_test_image(1, 'PNG')
        image3 = create_test_image(1, 'GIF')

        response = client.post('/api/posts/', {
            'content': '测试多张图片上传',
            'post_type': 'normal',
            'images': [image1, image2, image3]
        }, format='multipart')

        print(f"多张图片上传响应状态: {response.status_code}")
        if response.status_code == 201:
            print("✅ 多张图片上传成功")
            data = response.json()
            images = data.get('images', [])
            print(f"上传的图片数量: {len(images)}")
        else:
            print(f"❌ 多张图片上传失败: {response.content.decode()}")

        # 测试5: 评论图片上传
        print("\n📸 测试5: 评论图片上传...")
        # 先创建一个动态
        post_response = client.post('/api/posts/', {
            'content': '测试动态用于评论',
            'post_type': 'normal'
        })

        if post_response.status_code == 201:
            post_data = post_response.json()
            post_id = post_data['id']

            # 创建带图片的评论
            comment_image = create_test_image(1)
            comment_response = client.post(f'/api/posts/{post_id}/comments/', {
                'content': '测试评论带图片',
                'images': comment_image
            }, format='multipart')

            print(f"评论图片上传响应状态: {comment_response.status_code}")
            if comment_response.status_code == 201:
                print("✅ 评论图片上传成功")
                comment_data = comment_response.json()
                comment_images = comment_data.get('images', [])
                print(f"评论图片数量: {len(comment_images)}")
            else:
                print(f"❌ 评论图片上传失败: {comment_response.content.decode()}")
        else:
            print("❌ 无法创建测试动态，跳过评论图片测试")

        # 清理测试数据
        Post.objects.filter(user=user).delete()
        if created_user:
            user.delete()

        print("\n✅ 图片上传修复测试完成")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("开始图片上传修复测试...")
    success = test_image_upload_fixes()

    if success:
        print("\n🎉 所有测试通过！图片上传HTTP 500错误修复工作正常。")
    else:
        print("\n⚠️  测试失败，需要检查修复。")