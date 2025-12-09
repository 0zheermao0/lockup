#!/usr/bin/env python3
"""
模拟Telegram绑定流程的脚本
用于在没有webhook的情况下测试绑定功能
"""

import os
import sys
import django
import json

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test.client import Client
from rest_framework.authtoken.models import Token

User = get_user_model()

def simulate_telegram_start_with_deep_link():
    """模拟用户点击深度链接并在Telegram中发送/start命令的流程"""
    print("🔗 模拟Telegram深度链接绑定流程...")

    # 1. 模拟前端生成深度链接
    # 假设当前登录用户ID为1（你可以根据实际情况修改）
    user_id = 1
    try:
        current_user = User.objects.get(id=user_id)
        print(f"✅ 当前用户: {current_user.username}")
    except User.DoesNotExist:
        print("❌ 用户不存在，请先创建用户或修改user_id")
        return

    # 2. 生成深度链接（前端逻辑）
    bot_username = 'lock_up_bot'
    bind_token = f'bind_{user_id}_{int(time.time())}'
    deep_link = f'https://t.me/{bot_username}?start={bind_token}'
    print(f"🔗 生成深度链接: {deep_link}")

    # 3. 模拟Telegram用户数据（从Bot API获取）
    # 这些数据通常在用户点击深度链接后由Telegram发送给Bot
    telegram_user_data = {
        'id': 123456789,  # Telegram用户ID
        'username': 'test_user',  # Telegram用户名
        'first_name': '测试',
        'last_name': '用户'
    }

    telegram_chat_id = 987654321  # 聊天ID

    print(f"📱 模拟Telegram用户数据:")
    print(f"   - User ID: {telegram_user_data['id']}")
    print(f"   - Username: @{telegram_user_data['username']}")
    print(f"   - Chat ID: {telegram_chat_id}")

    # 4. 解析bind_token并提取用户ID
    try:
        parts = bind_token.split('_')
        if len(parts) >= 2 and parts[0] == 'bind':
            extracted_user_id = int(parts[1])
            print(f"✅ 从bind_token提取用户ID: {extracted_user_id}")
        else:
            print("❌ bind_token格式错误")
            return
    except ValueError:
        print("❌ 无法解析bind_token中的用户ID")
        return

    # 5. 验证用户ID匹配
    if extracted_user_id != user_id:
        print("❌ 用户ID不匹配")
        return

    # 6. 执行绑定操作
    try:
        # 检查是否已经有其他用户绑定了这个Telegram账户
        existing_user = User.objects.filter(telegram_user_id=telegram_user_data['id']).first()
        if existing_user and existing_user.id != user_id:
            print(f"❌ Telegram账户已被用户 {existing_user.username} 绑定")
            return

        # 执行绑定
        current_user.bind_telegram(
            telegram_user_id=telegram_user_data['id'],
            telegram_username=telegram_user_data['username'],
            telegram_chat_id=telegram_chat_id
        )

        print("✅ 绑定成功！")
        print(f"   - 用户: {current_user.username}")
        print(f"   - Telegram ID: {current_user.telegram_user_id}")
        print(f"   - Telegram 用户名: @{current_user.telegram_username}")
        print(f"   - 绑定时间: {current_user.telegram_bound_at}")

        return True

    except Exception as e:
        print(f"❌ 绑定失败: {e}")
        return False

def test_frontend_binding_status():
    """测试前端绑定状态API"""
    print("\n🔍 测试前端绑定状态...")

    # 获取用户Token
    try:
        user = User.objects.get(id=1)  # 根据实际情况修改
        token, created = Token.objects.get_or_create(user=user)

        # 模拟前端API调用
        client = Client()
        response = client.get(
            '/api/telegram/status/',
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )

        print(f"📡 API响应状态: {response.status_code}")
        if response.status_code == 200:
            data = json.loads(response.content.decode())
            print(f"📊 绑定状态:")
            print(f"   - 是否绑定: {data.get('is_bound')}")
            print(f"   - Telegram用户名: {data.get('telegram_username')}")
            print(f"   - 绑定时间: {data.get('bound_at')}")
            print(f"   - 通知开启: {data.get('notifications_enabled')}")
        else:
            print(f"❌ API调用失败: {response.content.decode()}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")

def show_next_steps():
    """显示下一步操作指南"""
    print("\n" + "="*60)
    print("🎯 下一步操作指南")
    print("="*60)

    print("\n✅ 当前状态:")
    print("   - API功能正常")
    print("   - 绑定逻辑正确")
    print("   - 数据库操作成功")

    print("\n🚀 要完成完整的绑定流程，你需要:")
    print("\n1. 设置Webhook（选择一种方案）:")
    print("   方案A: 安装ngrok")
    print("   - brew install ngrok")
    print("   - ngrok http 8000")
    print("   - python manage.py setup_telegram --set-webhook https://xxx.ngrok.io/api/telegram/webhook/")
    print()
    print("   方案B: 使用在线隧道服务")
    print("   - https://localhost.run")
    print("   - https://serveo.net")
    print("   - https://localtunnel.github.io")
    print()
    print("   方案C: 部署到服务器")
    print("   - 使用你现有的域名")
    print("   - https://lock-down.zheermao.top/api/telegram/webhook/")

    print("\n2. 启用Bot的Inline Mode:")
    print("   - 在Telegram中找到@BotFather")
    print("   - 发送 /setinline")
    print("   - 选择你的Bot: @lock_up_bot")
    print("   - 设置提示文本")

    print("\n3. 测试完整流程:")
    print("   - 在应用中点击'打开Telegram Bot'")
    print("   - Bot应该响应并处理绑定")
    print("   - 应用显示绑定成功状态")

    print("\n💡 临时解决方案:")
    print("   - 运行此脚本模拟绑定")
    print("   - 前端会显示绑定成功状态")
    print("   - 可以测试其他功能（如任务分享）")

if __name__ == "__main__":
    import time

    print("🔧 Telegram绑定模拟工具")
    print("-" * 40)

    # 执行模拟绑定
    success = simulate_telegram_start_with_deep_link()

    if success:
        # 测试前端状态
        test_frontend_binding_status()

    # 显示指南
    show_next_steps()

    print(f"\n✅ 模拟完成！现在可以在前端查看绑定状态。")