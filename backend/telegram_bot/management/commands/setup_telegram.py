from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import json


class Command(BaseCommand):
    help = 'Setup Telegram Bot webhook and configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--set-webhook',
            action='store_true',
            help='Set webhook URL for the bot',
        )
        parser.add_argument(
            '--delete-webhook',
            action='store_true',
            help='Delete webhook (switch to polling)',
        )
        parser.add_argument(
            '--info',
            action='store_true',
            help='Show bot and webhook information',
        )

    def handle(self, *args, **options):
        bot_token = settings.TELEGRAM_BOT_TOKEN

        if not bot_token or bot_token == 'YOUR_BOT_TOKEN_HERE':
            self.stdout.write(
                self.style.ERROR('请在设置中配置有效的 TELEGRAM_BOT_TOKEN')
            )
            return

        base_url = f"https://api.telegram.org/bot{bot_token}"

        if options['info']:
            self.show_info(base_url)
        elif options['set_webhook']:
            self.set_webhook(base_url)
        elif options['delete_webhook']:
            self.delete_webhook(base_url)
        else:
            self.stdout.write(
                self.style.WARNING('请指定操作: --info, --set-webhook, 或 --delete-webhook')
            )

    def show_info(self, base_url):
        """显示Bot和Webhook信息"""
        self.stdout.write("🤖 获取Bot信息...")

        # 获取Bot信息
        try:
            response = requests.get(f"{base_url}/getMe")
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                bot_info = result['result']
                self.stdout.write(
                    self.style.SUCCESS(f"Bot名称: {bot_info.get('first_name', 'N/A')}")
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Bot用户名: @{bot_info.get('username', 'N/A')}")
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Bot ID: {bot_info.get('id', 'N/A')}")
                )
                self.stdout.write(
                    self.style.SUCCESS(f"支持Inline Mode: {'是' if bot_info.get('supports_inline_queries') else '否'}")
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"获取Bot信息失败: {e}")
            )
            return

        # 获取Webhook信息
        self.stdout.write("\n📍 获取Webhook信息...")
        try:
            response = requests.get(f"{base_url}/getWebhookInfo")
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                webhook_info = result['result']
                if webhook_info.get('url'):
                    self.stdout.write(
                        self.style.SUCCESS(f"Webhook URL: {webhook_info['url']}")
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"待处理更新: {webhook_info.get('pending_update_count', 0)}")
                    )
                    if webhook_info.get('last_error_date'):
                        self.stdout.write(
                            self.style.WARNING(f"最后错误: {webhook_info.get('last_error_message', 'N/A')}")
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING("未设置Webhook（使用长轮询模式）")
                    )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"获取Webhook信息失败: {e}")
            )

    def set_webhook(self, base_url):
        """设置Webhook"""
        webhook_url = settings.TELEGRAM_WEBHOOK_URL

        self.stdout.write(f"🔧 设置Webhook: {webhook_url}")

        payload = {
            'url': webhook_url,
            'allowed_updates': getattr(settings, 'TELEGRAM_SECURITY', {}).get(
                'ALLOWED_UPDATES', ['message', 'inline_query', 'callback_query']
            ),
            'max_connections': 100,
            'drop_pending_updates': True
        }

        # 如果配置了Secret Token
        webhook_secret = getattr(settings, 'TELEGRAM_SECURITY', {}).get('WEBHOOK_SECRET_TOKEN')
        if webhook_secret:
            payload['secret_token'] = webhook_secret
            self.stdout.write("🔐 使用Secret Token")

        try:
            response = requests.post(f"{base_url}/setWebhook", json=payload)
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                self.stdout.write(
                    self.style.SUCCESS("✅ Webhook设置成功!")
                )
                self.stdout.write(
                    self.style.SUCCESS(f"📍 URL: {webhook_url}")
                )
                self.stdout.write(
                    self.style.SUCCESS(f"📥 允许的更新类型: {', '.join(payload['allowed_updates'])}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Webhook设置失败: {result.get('description', '未知错误')}")
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ 请求失败: {e}")
            )

    def delete_webhook(self, base_url):
        """删除Webhook"""
        self.stdout.write("🗑️ 删除Webhook...")

        try:
            response = requests.post(f"{base_url}/deleteWebhook", json={'drop_pending_updates': True})
            response.raise_for_status()
            result = response.json()

            if result.get('ok'):
                self.stdout.write(
                    self.style.SUCCESS("✅ Webhook已删除，Bot切换回长轮询模式")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ 删除Webhook失败: {result.get('description', '未知错误')}")
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ 请求失败: {e}")
            )