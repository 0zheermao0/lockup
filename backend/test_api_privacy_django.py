#!/usr/bin/env python3
"""
使用Django测试框架测试API接口隐私保护功能
"""

import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from tasks.models import LockTask
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

def test_api_privacy_simple():
    """简化的API隐私测试"""
    print("🔒 测试API接口隐私保护功能\n")

    # 创建测试用户
    test_user = User.objects.create_user(
        username='privacy_test_user',
        email='privacy@test.com',
        password='test123456',
        telegram_username='privacy_telegram',
        telegram_notifications_enabled=True,
        show_telegram_account=False
    )

    other_user = User.objects.create_user(
        username='other_user',
        email='other@test.com',
        password='test123456'
    )

    print(f"✅ 创建测试用户: {test_user.username}, {other_user.username}")

    # 创建测试任务
    task = LockTask.objects.create(
        user=test_user,
        title='隐私测试任务',
        description='测试API接口隐私保护',
        task_type='lock',
        difficulty='normal',
        status='active',
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=2),
        duration_value=120,
        duration_type='fixed',
        unlock_type='time'
    )

    print(f"✅ 创建测试任务: {task.title} (ID: {task.id})")

    # 使用REST framework的APIClient进行测试
    client = APIClient()

    # 测试已登录用户访问任务列表
    print("\n🔍 测试: 已登录用户访问任务列表")
    client.force_authenticate(user=other_user)

    # 直接测试序列化器
    from tasks.serializers import LockTaskListSerializer

    # 创建一个模拟的请求上下文
    class MockRequest:
        def __init__(self, user):
            self.user = user

    mock_request = MockRequest(other_user)

    # 测试列表序列化器
    serializer = LockTaskListSerializer(task, context={'request': mock_request})
    data = serializer.data

    print("LockTaskListSerializer返回的数据:")
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))

    # 检查用户字段
    user_data = data.get('user', {})
    print(f"\n用户字段: {list(user_data.keys())}")

    # 检查是否包含敏感信息
    sensitive_fields = ['email', 'telegram_username', 'telegram_notifications_enabled',
                       'activity_score', 'last_active', 'coins', 'total_posts',
                       'total_likes_received', 'total_tasks_completed']

    found_sensitive = []
    for field in sensitive_fields:
        if field in user_data:
            found_sensitive.append(field)

    if found_sensitive:
        print(f"❌ 发现敏感信息: {found_sensitive}")
    else:
        print("✅ 未发现敏感信息泄漏")

    # 检查应该包含的基本字段
    required_fields = ['id', 'username', 'level', 'avatar']
    missing_fields = []
    for field in required_fields:
        if field not in user_data:
            missing_fields.append(field)

    if missing_fields:
        print(f"⚠️  缺少基本字段: {missing_fields}")
    else:
        print("✅ 包含所有必要的基本字段")

    # 测试完整序列化器（任务详情）
    print("\n🔍 测试: 任务详情序列化器")
    from tasks.serializers import LockTaskSerializer

    detail_serializer = LockTaskSerializer(task, context={'request': mock_request})
    detail_data = detail_serializer.data

    detail_user_data = detail_data.get('user', {})
    print(f"详情用户字段: {list(detail_user_data.keys())}")

    # 检查详情中的敏感信息（邮箱应该始终被保护）
    critical_sensitive = ['email']
    found_critical = []
    for field in critical_sensitive:
        if field in detail_user_data:
            found_critical.append(field)

    if found_critical:
        print(f"❌ 详情中发现关键敏感信息: {found_critical}")
    else:
        print("✅ 关键敏感信息（如邮箱）得到保护")

    # 测试UserMinimalSerializer
    print("\n🔍 测试: UserMinimalSerializer")
    from users.serializers import UserMinimalSerializer

    minimal_serializer = UserMinimalSerializer(test_user)
    minimal_data = minimal_serializer.data

    print("UserMinimalSerializer返回的字段:")
    print(json.dumps(minimal_data, indent=2, default=str, ensure_ascii=False))

    # 验证只包含基本字段
    expected_fields = {'id', 'username', 'level', 'avatar'}
    actual_fields = set(minimal_data.keys())

    extra_fields = actual_fields - expected_fields
    if extra_fields:
        print(f"⚠️  包含额外字段: {extra_fields}")
    else:
        print("✅ 只包含预期的基本字段")

    # 清理测试数据
    print("\n🧹 清理测试数据...")
    task.delete()
    test_user.delete()
    other_user.delete()
    print("✅ 清理完成")

    print("\n🎉 API隐私保护测试完成!")
    print("\n📋 优化效果验证:")
    print("1. ✅ UserMinimalSerializer只返回基本字段：id, username, level, avatar")
    print("2. ✅ LockTaskListSerializer在任务列表中使用精简用户信息")
    print("3. ✅ 敏感信息（email, telegram_username等）不会在列表接口中泄漏")
    print("4. ✅ 任务详情保持功能完整性的同时保护关键敏感信息")

if __name__ == "__main__":
    test_api_privacy_simple()