#!/usr/bin/env python3
"""
紧急生产环境修复脚本
直接修改settings.py强制设置Token
"""

import os
import sys
from pathlib import Path

def emergency_fix():
    """紧急修复生产环境Token配置"""
    print("🚨 执行紧急生产环境修复...")

    # 1. 备份settings.py
    settings_file = Path(__file__).parent / 'lockup_backend' / 'settings.py'
    backup_file = settings_file.with_suffix('.py.backup')

    if settings_file.exists():
        print(f"📁 备份settings.py到 {backup_file}")
        import shutil
        shutil.copy2(settings_file, backup_file)

    # 2. 读取现有settings.py
    with open(settings_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 3. 强制替换Token配置
    old_token_line = "TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8593610083:AAFPwRTuNZ_9zO8dEKSIKzUfyGF57faeRhY')"
    new_token_line = "TELEGRAM_BOT_TOKEN = '8593610083:AAFPwRTuNZ_9zO8dEKSIKzUfyGF57faeRhY'  # 强制设置生产环境Token"

    if old_token_line in content:
        content = content.replace(old_token_line, new_token_line)
        print("✅ 替换了TELEGRAM_BOT_TOKEN配置")
    else:
        # 如果找不到原行，在文件末尾添加
        content += f"\n\n# 紧急生产环境修复 - 强制设置Token\n{new_token_line}\n"
        print("✅ 添加了强制Token配置")

    # 4. 同样处理其他配置
    replacements = {
        "TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME', 'lock_up_bot')":
        "TELEGRAM_BOT_USERNAME = 'lock_up_bot'  # 强制设置",

        "TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', 'https://lock-down.zheermao.top/api/telegram/webhook/')":
        "TELEGRAM_WEBHOOK_URL = 'https://lock-down.zheermao.top/api/telegram/webhook/'  # 强制设置"
    }

    for old, new in replacements.items():
        if old in content:
            content = content.replace(old, new)
            print(f"✅ 替换了配置: {old.split('=')[0].strip()}")

    # 5. 写入修改后的settings.py
    with open(settings_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("🔧 settings.py已更新")

    # 6. 验证修改
    print("\n🧪 验证修改...")
    try:
        # 重新加载Django设置
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')

        # 清除已导入的设置模块
        if 'lockup_backend.settings' in sys.modules:
            del sys.modules['lockup_backend.settings']
        if 'django.conf' in sys.modules:
            del sys.modules['django.conf']

        # 重新导入
        import django
        from django.conf import settings
        django.setup()

        print(f"✅ Token: {settings.TELEGRAM_BOT_TOKEN[:30]}...")
        print(f"✅ Username: {settings.TELEGRAM_BOT_USERNAME}")
        print(f"✅ Webhook: {settings.TELEGRAM_WEBHOOK_URL}")

        return True

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def restore_backup():
    """恢复备份"""
    settings_file = Path(__file__).parent / 'lockup_backend' / 'settings.py'
    backup_file = settings_file.with_suffix('.py.backup')

    if backup_file.exists():
        import shutil
        shutil.copy2(backup_file, settings_file)
        print(f"✅ 已恢复备份: {backup_file} -> {settings_file}")
        return True
    else:
        print("❌ 未找到备份文件")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        restore_backup()
    else:
        print("🚨 紧急生产环境Telegram Bot修复")
        print("=" * 50)

        success = emergency_fix()

        if success:
            print("\n✅ 紧急修复完成！")
            print("📋 下一步:")
            print("1. 重启Django应用")
            print("2. 测试: python manage.py setup_telegram --info")
            print("3. 如需恢复: python emergency_production_fix.py restore")
        else:
            print("\n❌ 修复失败")
            print("📋 建议:")
            print("1. 检查settings.py文件权限")
            print("2. 手动编辑settings.py")
            print("3. 如需恢复: python emergency_production_fix.py restore")