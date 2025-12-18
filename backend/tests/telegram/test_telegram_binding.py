#!/usr/bin/env python
"""
测试Telegram绑定流程的脚本
"""

import os
import sys
import django
import json
import requests

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from users.models import User
from django.contrib.auth import get_user_model

User = get_user_model()

def test_telegram_binding():
    """测试完整的Telegram绑定流程"""

    print("=== Telegram绑定流程测试 ===")

    # 1. 创建测试用户
    test_user, created = User.objects.get_or_create(
        username='telegram_test_user',
        defaults={
            'email': 'test@example.com',
            'password': 'test123',
            'level': 1,
            'coins': 100
        }
    )

    print(f"1. 测试用户: {test_user.username} (新建: {created})")

    # 2. 模拟前端启动绑定流程
    test_telegram_user_id = 987654321
    test_user.telegram_user_id = test_telegram_user_id
    test_user.telegram_chat_id = None  # 等待webhook设置
    test_user.save()

    print(f"2. 设置telegram_user_id: {test_user.telegram_user_id}")
    print(f"   telegram_chat_id: {test_user.telegram_chat_id}")
    print(f"   is_telegram_bound: {test_user.is_telegram_bound()}")

    # 3. 模拟用户在Telegram中发送/start命令
    webhook_data = {
        "update_id": 123456,
        "message": {
            "message_id": 1,
            "date": 1733800000,
            "chat": {
                "id": 123456789,
                "type": "private"
            },
            "from": {
                "id": test_telegram_user_id,
                "is_bot": False,
                "first_name": "Test",
                "username": "test_user",
                "language_code": "zh"
            },
            "text": "/start"
        }
    }

    print("\n3. 模拟webhook接收/start命令...")

    # 发送webhook请求到本地服务器
    try:
        response = requests.post(
            'http://127.0.0.1:8000/api/telegram/webhook/',
            json=webhook_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        print(f"   Webhook响应状态: {response.status_code}")
        print(f"   Webhook响应内容: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"   Webhook请求失败: {e}")

    # 4. 检查绑定结果
    test_user.refresh_from_db()
    print(f"\n4. 绑定结果:")
    print(f"   telegram_user_id: {test_user.telegram_user_id}")
    print(f"   telegram_username: {test_user.telegram_username}")
    print(f"   telegram_chat_id: {test_user.telegram_chat_id}")
    print(f"   telegram_bound_at: {test_user.telegram_bound_at}")
    print(f"   is_telegram_bound: {test_user.is_telegram_bound()}")

    # 5. 测试/status命令
    status_webhook_data = {
        "update_id": 123457,
        "message": {
            "message_id": 2,
            "date": 1733800010,
            "chat": {
                "id": 123456789,
                "type": "private"
            },
            "from": {
                "id": test_telegram_user_id,
                "is_bot": False,
                "first_name": "Test",
                "username": "test_user",
                "language_code": "zh"
            },
            "text": "/status"
        }
    }

    print("\n5. 测试/status命令...")

    try:
        response = requests.post(
            'http://127.0.0.1:8000/api/telegram/webhook/',
            json=status_webhook_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        print(f"   /status响应状态: {response.status_code}")
        print(f"   /status响应内容: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"   /status请求失败: {e}")

    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_telegram_binding()