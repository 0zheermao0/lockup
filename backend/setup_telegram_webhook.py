#!/usr/bin/env python3
"""
Telegram Bot Webhook 设置脚本
用于设置和管理 Telegram Bot 的 Webhook 配置
"""

import os
import sys
import django
import requests
import json
from urllib.parse import urljoin

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from django.conf import settings


class TelegramWebhookManager:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.webhook_url = settings.TELEGRAM_WEBHOOK_URL
        self.webhook_secret = getattr(settings, 'TELEGRAM_SECURITY', {}).get('WEBHOOK_SECRET_TOKEN')
        self.base_api_url = f"https://api.telegram.org/bot{self.bot_token}"

        if not self.bot_token or self.bot_token == 'YOUR_BOT_TOKEN_HERE':
            raise ValueError("请在设置中配置有效的 TELEGRAM_BOT_TOKEN")

    def get_webhook_info(self):
        """获取当前 Webhook 信息"""
        url = f"{self.base_api_url}/getWebhookInfo"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取 Webhook 信息失败: {e}")
            return None

    def set_webhook(self):
        """设置 Webhook"""
        url = f"{self.base_api_url}/setWebhook"

        payload = {
            'url': self.webhook_url,
            'allowed_updates': settings.TELEGRAM_SECURITY.get('ALLOWED_UPDATES', ['message', 'inline_query', 'callback_query']),
            'max_connections': 100,
            'drop_pending_updates': True
        }

        # 如果配置了 Webhook Secret，添加到请求中
        if self.webhook_secret:
            payload['secret_token'] = self.webhook_secret

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                print("✅ Webhook 设置成功!")
                print(f"📍 Webhook URL: {self.webhook_url}")
                if self.webhook_secret:
                    print("🔐 Secret Token: 已配置")
                print(f"📥 允许的更新类型: {', '.join(payload['allowed_updates'])}")
                return True
            else:
                print(f"❌ Webhook 设置失败: {result.get('description', '未知错误')}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}")
            return False

    def delete_webhook(self):
        """删除 Webhook（切换回长轮询模式）"""
        url = f"{self.base_api_url}/deleteWebhook"

        try:
            response = requests.post(url, json={'drop_pending_updates': True})
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                print("✅ Webhook 已删除，Bot 切换回长轮询模式")
                return True
            else:
                print(f"❌ 删除 Webhook 失败: {result.get('description', '未知错误')}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}")
            return False

    def get_bot_info(self):
        """获取 Bot 基本信息"""
        url = f"{self.base_api_url}/getMe"
        try:
            response = requests.get(url)
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                bot_info = result['result']
                print("🤖 Bot 信息:")
                print(f"   名称: {bot_info.get('first_name', 'N/A')}")
                print(f"   用户名: @{bot_info.get('username', 'N/A')}")
                print(f"   ID: {bot_info.get('id', 'N/A')}")
                print(f"   支持 Inline Mode: {'✅' if bot_info.get('supports_inline_queries') else '❌'}")
                return bot_info
            else:
                print(f"❌ 获取 Bot 信息失败: {result.get('description', '未知错误')}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}")
            return None

    def test_webhook(self):
        """测试 Webhook 连接"""
        print("🔍 测试 Webhook 连接...")

        # 检查 URL 是否可访问
        try:
            response = requests.head(self.webhook_url, timeout=10)
            if response.status_code == 405:  # Method Not Allowed 是正常的，因为我们用的是 HEAD
                print("✅ Webhook URL 可访问")
            elif response.status_code == 200:
                print("✅ Webhook URL 可访问")
            else:
                print(f"⚠️ Webhook URL 返回状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Webhook URL 无法访问: {e}")
            return False

        return True


def main():
    print("🔧 Telegram Bot Webhook 管理工具")
    print("=" * 50)

    try:
        manager = TelegramWebhookManager()
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        sys.exit(1)

    # 显示当前配置
    print(f"🤖 Bot Token: {manager.bot_token[:10]}...")
    print(f"📍 Webhook URL: {manager.webhook_url}")
    print()

    # 获取 Bot 信息
    bot_info = manager.get_bot_info()
    if not bot_info:
        sys.exit(1)
    print()

    # 获取当前 Webhook 状态
    print("📊 当前 Webhook 状态:")
    webhook_info = manager.get_webhook_info()
    if webhook_info and webhook_info.get('ok'):
        info = webhook_info['result']
        if info.get('url'):
            print(f"   URL: {info['url']}")
            print(f"   待处理更新: {info.get('pending_update_count', 0)}")
            if info.get('last_error_date'):
                print(f"   最后错误: {info.get('last_error_message', 'N/A')}")
        else:
            print("   ❌ 未设置 Webhook（使用长轮询模式）")
    print()

    # 交互式菜单
    while True:
        print("请选择操作:")
        print("1. 设置 Webhook")
        print("2. 删除 Webhook")
        print("3. 查看 Webhook 状态")
        print("4. 测试 Webhook 连接")
        print("5. 退出")

        choice = input("\n请输入选项 (1-5): ").strip()

        if choice == '1':
            print("\n🔧 设置 Webhook...")
            manager.set_webhook()
        elif choice == '2':
            print("\n🗑️ 删除 Webhook...")
            manager.delete_webhook()
        elif choice == '3':
            print("\n📊 查看 Webhook 状态...")
            webhook_info = manager.get_webhook_info()
            if webhook_info:
                print(json.dumps(webhook_info, indent=2, ensure_ascii=False))
        elif choice == '4':
            print("\n🔍 测试 Webhook 连接...")
            manager.test_webhook()
        elif choice == '5':
            print("\n👋 再见!")
            break
        else:
            print("❌ 无效选项，请重新选择")

        print("\n" + "=" * 50)


if __name__ == "__main__":
    main()