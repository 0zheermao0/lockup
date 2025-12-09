#!/usr/bin/env python3
"""
测试Telegram绑定功能的脚本
用于在本地开发环境中模拟Telegram Bot绑定流程
"""

import os
import sys
import django
import requests

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test.client import Client
from rest_framework.authtoken.models import Token

User = get_user_model()

def test_telegram_binding():
    """测试Telegram绑定功能"""
    print("🔧 开始测试Telegram绑定功能...")

    # 1. 创建测试用户（如果不存在）
    test_username = "testuser"
    test_password = "testpass123"

    try:
        user = User.objects.get(username=test_username)
        print(f"✅ 使用现有测试用户: {test_username}")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username=test_username,
            email="test@example.com",
            password=test_password
        )
        print(f"✅ 创建新测试用户: {test_username}")

    # 2. 获取或创建认证Token
    token, created = Token.objects.get_or_create(user=user)
    print(f"✅ 用户Token: {token.key}")

    # 3. 模拟Telegram用户数据
    telegram_user_id = 123456789
    telegram_username = "test_telegram_user"
    telegram_chat_id = 987654321

    # 4. 测试绑定API
    client = Client()

    bind_data = {
        "telegram_user_id": telegram_user_id,
        "telegram_username": telegram_username,
        "telegram_chat_id": telegram_chat_id
    }

    # 使用Token认证
    response = client.post(
        '/api/telegram/bind/',
        data=bind_data,
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Token {token.key}'
    )

    print(f"📡 绑定API响应状态: {response.status_code}")
    print(f"📡 绑定API响应内容: {response.content.decode()}")

    # 5. 检查绑定状态
    user.refresh_from_db()
    print(f"\n📊 绑定结果:")
    print(f"   - Telegram User ID: {user.telegram_user_id}")
    print(f"   - Telegram Username: {user.telegram_username}")
    print(f"   - Telegram Chat ID: {user.telegram_chat_id}")
    print(f"   - 绑定时间: {user.telegram_bound_at}")
    print(f"   - 是否已绑定: {user.is_telegram_bound()}")

    # 6. 测试状态API
    status_response = client.get(
        '/api/telegram/status/',
        HTTP_AUTHORIZATION=f'Token {token.key}'
    )

    print(f"\n📡 状态API响应: {status_response.status_code}")
    print(f"📡 状态API内容: {status_response.content.decode()}")

    return user, token

def test_telegram_bot_connection():
    """测试Telegram Bot连接"""
    print("\n🤖 测试Telegram Bot连接...")

    from django.conf import settings

    bot_token = settings.TELEGRAM_BOT_TOKEN

    # 测试Bot API连接
    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            print(f"✅ Bot连接成功:")
            print(f"   - Bot名称: {bot_info['result']['first_name']}")
            print(f"   - Bot用户名: @{bot_info['result']['username']}")
            print(f"   - Bot ID: {bot_info['result']['id']}")
        else:
            print(f"❌ Bot连接失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"❌ Bot连接异常: {e}")

def print_local_testing_guide():
    """打印本地测试指南"""
    print("\n" + "="*60)
    print("🔧 本地Telegram Bot测试指南")
    print("="*60)

    print("\n📋 问题诊断:")
    print("   1. ❌ 未设置Webhook - Bot无法接收消息")
    print("   2. ❌ Inline Mode未启用 - 影响某些功能")
    print("   3. ⚠️  本地开发环境限制")

    print("\n🛠️  解决方案:")
    print("\n方案1: 使用ngrok建立本地隧道（推荐）")
    print("   1. 安装ngrok: brew install ngrok")
    print("   2. 启动隧道: ngrok http 8000")
    print("   3. 复制HTTPS URL（如: https://abc123.ngrok.io）")
    print("   4. 设置Webhook:")
    print("      python manage.py setup_telegram --set-webhook https://abc123.ngrok.io/telegram/webhook/")

    print("\n方案2: 手动模拟绑定（测试用）")
    print("   1. 运行此脚本进行API测试")
    print("   2. 在数据库中直接设置绑定数据")
    print("   3. 测试前端显示状态")

    print("\n方案3: 使用生产环境")
    print("   1. 部署到服务器")
    print("   2. 设置正确的Webhook URL")
    print("   3. 启用Bot的Inline Mode")

    print("\n🚀 推荐操作步骤:")
    print("   1. 先运行此脚本测试API")
    print("   2. 安装ngrok并设置隧道")
    print("   3. 配置Webhook")
    print("   4. 测试完整绑定流程")

if __name__ == "__main__":
    print("🔧 Telegram Bot绑定测试工具")
    print("-" * 40)

    # 测试Bot连接
    test_telegram_bot_connection()

    # 测试绑定功能
    user, token = test_telegram_binding()

    # 打印指南
    print_local_testing_guide()

    print(f"\n✅ 测试完成！")
    print(f"   测试用户: {user.username}")
    print(f"   认证Token: {token.key}")
    print(f"   绑定状态: {user.is_telegram_bound()}")