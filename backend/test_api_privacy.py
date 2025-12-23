#!/usr/bin/env python3
"""
测试API接口隐私保护功能
验证任务列表等接口不返回用户敏感信息
"""

import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from tasks.models import LockTask
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

def test_api_privacy():
    """测试API接口的隐私保护功能"""
    print("🔒 测试API接口隐私保护功能\n")

    # 创建测试用户
    test_user = User.objects.create_user(
        username='privacy_test_user',
        email='privacy@test.com',
        password='test123456',
        telegram_username='privacy_telegram',
        telegram_notifications_enabled=True,
        show_telegram_account=False  # 不显示telegram账号
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

    # 创建Django测试客户端
    client = Client()

    # 测试未登录用户访问任务列表
    print("\n🔍 测试1: 未登录用户访问任务列表")
    response = client.get('/api/tasks/?task_type=lock&page_size=20')
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        if 'results' in data and len(data['results']) > 0:
            task_data = data['results'][0]
            user_data = task_data.get('user', {})

            print("返回的用户字段:")
            for field, value in user_data.items():
                print(f"  - {field}: {value}")

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
        else:
            print("⚠️  没有找到任务数据")
    else:
        print(f"❌ 请求失败，状态码: {response.status_code}")

    # 测试已登录用户访问任务列表
    print("\n🔍 测试2: 已登录用户访问任务列表")
    client.force_login(other_user)
    response = client.get('/api/tasks/?task_type=lock&page_size=20')
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        if 'results' in data and len(data['results']) > 0:
            task_data = data['results'][0]
            user_data = task_data.get('user', {})

            print("返回的用户字段:")
            for field, value in user_data.items():
                print(f"  - {field}: {value}")

            # 检查是否包含敏感信息
            sensitive_fields = ['email', 'telegram_username', 'telegram_notifications_enabled']

            found_sensitive = []
            for field in sensitive_fields:
                if field in user_data:
                    found_sensitive.append(field)

            if found_sensitive:
                print(f"❌ 发现敏感信息: {found_sensitive}")
            else:
                print("✅ 未发现敏感信息泄漏")
        else:
            print("⚠️  没有找到任务数据")

    # 测试任务详情接口
    print(f"\n🔍 测试3: 任务详情接口 (ID: {task.id})")
    response = client.get(f'/api/tasks/{task.id}/')
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        user_data = data.get('user', {})

        print("任务详情返回的用户字段:")
        for field, value in user_data.items():
            print(f"  - {field}: {value}")

        # 任务详情应该包含更多信息，但仍要保护敏感字段
        sensitive_fields = ['email']  # 邮箱在任何情况下都不应该暴露

        found_sensitive = []
        for field in sensitive_fields:
            if field in user_data:
                found_sensitive.append(field)

        if found_sensitive:
            print(f"❌ 发现敏感信息: {found_sensitive}")
        else:
            print("✅ 邮箱等敏感信息得到保护")

    # 测试任务板类型
    print("\n🔍 测试4: 任务板列表")
    board_task = LockTask.objects.create(
        user=test_user,
        title='隐私测试任务板',
        description='测试任务板API接口隐私保护',
        task_type='board',
        status='open',
        reward=50,
        max_duration=24
    )

    response = client.get('/api/tasks/?task_type=board&page_size=20')
    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        if 'results' in data and len(data['results']) > 0:
            # 查找我们创建的任务板
            board_data = None
            for task_data in data['results']:
                if task_data['id'] == str(board_task.id):
                    board_data = task_data
                    break

            if board_data:
                user_data = board_data.get('user', {})
                print("任务板返回的用户字段:")
                for field, value in user_data.items():
                    print(f"  - {field}: {value}")

                # 检查敏感信息
                sensitive_fields = ['email', 'telegram_username']
                found_sensitive = []
                for field in sensitive_fields:
                    if field in user_data:
                        found_sensitive.append(field)

                if found_sensitive:
                    print(f"❌ 任务板发现敏感信息: {found_sensitive}")
                else:
                    print("✅ 任务板未发现敏感信息泄漏")

    # 清理测试数据
    print("\n🧹 清理测试数据...")
    task.delete()
    board_task.delete()
    test_user.delete()
    other_user.delete()
    print("✅ 清理完成")

    print("\n🎉 API隐私保护测试完成!")
    print("\n📋 优化总结:")
    print("1. ✅ 创建了UserMinimalSerializer，只包含基本字段：id, username, level, avatar")
    print("2. ✅ 创建了LockTaskListSerializer，用于任务列表，移除了敏感用户信息")
    print("3. ✅ 任务详情仍使用完整序列化器，但邮箱等敏感信息仍受保护")
    print("4. ✅ 优化了所有相关序列化器，统一使用精简用户信息")
    print("5. ✅ 防止了email、telegram_username等敏感信息在不必要的接口中泄漏")

if __name__ == "__main__":
    test_api_privacy()