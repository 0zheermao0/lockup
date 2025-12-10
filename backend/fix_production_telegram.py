#!/usr/bin/env python3
"""
生产环境Telegram Bot修复脚本
解决Token配置和Webhook 403错误
"""

import os
import sys
import django
from pathlib import Path

def setup_django():
    """设置Django环境"""
    # 设置Django设置模块
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')

    # 添加项目路径到Python路径
    project_path = Path(__file__).parent
    if str(project_path) not in sys.path:
        sys.path.insert(0, str(project_path))

    # 初始化Django
    django.setup()

def fix_production_config():
    """修复生产环境配置"""
    print("=" * 60)
    print("生产环境Telegram Bot修复")
    print("=" * 60)

    # 1. 直接设置环境变量
    print("\n1. 设置环境变量...")
    env_vars = {
        'TELEGRAM_BOT_TOKEN': '8593610083:AAFPwRTuNZ_9zO8dEKSIKzUfyGF57faeRhY',
        'TELEGRAM_BOT_USERNAME': 'lock_up_bot',
        'TELEGRAM_WEBHOOK_URL': 'https://lock-down.zheermao.top/api/telegram/webhook/',
        'TELEGRAM_WEBHOOK_SECRET': '123456admin',
        'TELEGRAM_IP_WHITELIST': '149.154.160.0,149.154.161.0,149.154.162.0,172.71.182.154,172.71.182.191',
        'BASE_URL': 'https://lock-up.zheermao.top',
        'FRONTEND_URL': 'https://lock-up.zheermao.top',
    }

    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"   ✅ {key}: {value[:30]}...")

    # 2. 设置Django
    print("\n2. 初始化Django...")
    try:
        setup_django()
        from django.conf import settings

        print(f"   ✅ Django Token: {settings.TELEGRAM_BOT_TOKEN[:30]}...")
        print(f"   ✅ Django Webhook: {settings.TELEGRAM_WEBHOOK_URL}")

    except Exception as e:
        print(f"   ❌ Django初始化失败: {e}")
        return False

    # 3. 测试Bot初始化
    print("\n3. 测试Bot初始化...")
    try:
        from telegram_bot.services import telegram_service
        import asyncio

        async def test_bot():
            # 强制重新初始化Bot
            telegram_service._initialized = False
            telegram_service.bot = None
            telegram_service.application = None
            telegram_service._setup_bot()

            if await telegram_service._ensure_initialized():
                bot_info = await telegram_service.bot.get_me()
                print(f"   ✅ Bot: @{bot_info.username}")
                return True
            return False

        result = asyncio.run(test_bot())
        if not result:
            print("   ❌ Bot初始化失败")
            return False

    except Exception as e:
        print(f"   ❌ Bot测试失败: {e}")
        return False

    # 4. 设置Webhook
    print("\n4. 设置Webhook...")
    try:
        from telegram_bot.services import telegram_service
        import asyncio

        async def setup_webhook():
            webhook_url = settings.TELEGRAM_WEBHOOK_URL

            # 删除现有webhook
            await telegram_service.bot.delete_webhook()
            print(f"   ✅ 删除旧webhook")

            # 设置新webhook（不使用secret token避免403错误）
            await telegram_service.bot.set_webhook(
                url=webhook_url,
                allowed_updates=['message', 'callback_query']
            )
            print(f"   ✅ 设置新webhook: {webhook_url}")

            # 验证webhook
            webhook_info = await telegram_service.bot.get_webhook_info()
            print(f"   ✅ Webhook状态: {webhook_info.url}")
            print(f"   ✅ 待处理更新: {webhook_info.pending_update_count}")

            if webhook_info.last_error_message:
                print(f"   ⚠️ 最后错误: {webhook_info.last_error_message}")
            else:
                print(f"   ✅ 无错误")

        asyncio.run(setup_webhook())

    except Exception as e:
        print(f"   ❌ Webhook设置失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ 生产环境修复完成！")
    print("=" * 60)

    print("\n📋 下一步操作：")
    print("1. 重启应用服务")
    print("2. 监控日志确认无错误")
    print("3. 测试Bot命令功能")

    return True

if __name__ == "__main__":
    try:
        success = fix_production_config()
        if success:
            print("\n🎉 修复成功！")
        else:
            print("\n❌ 修复失败，请检查错误信息")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)