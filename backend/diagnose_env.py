#!/usr/bin/env python3
"""
生产环境Telegram Bot Token配置诊断脚本
用于诊断生产环境中.env文件不生效的问题
"""

import os
import sys
from pathlib import Path

def diagnose_env_config():
    """诊断环境配置问题"""
    print("=" * 60)
    print("生产环境Telegram Bot配置诊断")
    print("=" * 60)

    # 1. 基本环境信息
    print("\n1. 基本环境信息:")
    print(f"   Python版本: {sys.version}")
    print(f"   当前工作目录: {Path.cwd()}")
    print(f"   脚本执行路径: {Path(__file__).parent}")

    # 2. .env文件检查
    print("\n2. .env文件检查:")
    env_files = [
        Path.cwd() / '.env',
        Path(__file__).parent / '.env',
        Path('/app/.env'),  # Docker容器中的常见路径
        Path('/opt/app/.env'),  # 另一个常见路径
    ]

    env_file_found = None
    for env_file in env_files:
        if env_file.exists():
            print(f"   ✅ 找到.env文件: {env_file}")
            print(f"   文件大小: {env_file.stat().st_size} bytes")
            env_file_found = env_file

            # 检查文件内容
            try:
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                    telegram_token_lines = []
                    for i, line in enumerate(lines, 1):
                        if 'TELEGRAM_BOT_TOKEN' in line:
                            telegram_token_lines.append((i, line.strip()))

                    if telegram_token_lines:
                        print(f"   找到TELEGRAM_BOT_TOKEN配置:")
                        for line_num, line_content in telegram_token_lines:
                            if line_content.startswith('#'):
                                print(f"     第{line_num}行 (注释): {line_content}")
                            else:
                                print(f"     第{line_num}行 (有效): {line_content[:50]}...")
                    else:
                        print("   ❌ .env文件中没有找到TELEGRAM_BOT_TOKEN")
            except Exception as e:
                print(f"   ❌ 读取.env文件失败: {e}")
            break
        else:
            print(f"   ❌ .env文件不存在: {env_file}")

    if not env_file_found:
        print("   ❌ 没有找到任何.env文件!")

    # 3. 环境变量检查
    print("\n3. 环境变量检查:")
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if token:
        print(f"   ✅ TELEGRAM_BOT_TOKEN: {token[:30]}... (长度: {len(token)})")
    else:
        print("   ❌ TELEGRAM_BOT_TOKEN环境变量未设置")

    # 4. python-dotenv检查
    print("\n4. python-dotenv检查:")
    try:
        import dotenv
        print(f"   ✅ python-dotenv已安装")

        # 手动加载.env文件
        if env_file_found:
            print(f"   尝试手动加载: {env_file_found}")
            dotenv.load_dotenv(env_file_found, override=True)
            token_after_load = os.getenv('TELEGRAM_BOT_TOKEN')
            if token_after_load:
                print(f"   ✅ 手动加载后TELEGRAM_BOT_TOKEN: {token_after_load[:30]}...")
            else:
                print("   ❌ 手动加载后仍然没有TELEGRAM_BOT_TOKEN")
    except ImportError:
        print("   ❌ python-dotenv未安装")

    # 5. Django设置检查
    print("\n5. Django设置检查:")
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
        import django
        django.setup()

        from django.conf import settings
        django_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', 'NOT_SET')
        if django_token and django_token != 'YOUR_BOT_TOKEN_HERE':
            print(f"   ✅ Django TELEGRAM_BOT_TOKEN: {django_token[:30]}...")
        else:
            print(f"   ❌ Django TELEGRAM_BOT_TOKEN: {django_token}")

    except Exception as e:
        print(f"   ❌ Django设置检查失败: {e}")

    # 6. 解决方案建议
    print("\n6. 解决方案建议:")
    if not env_file_found:
        print("   📝 创建.env文件:")
        print("   echo 'TELEGRAM_BOT_TOKEN=8593610083:AAFPwRTuNZ_9zO8dEKSIKzUfyGF57faeRhY' > .env")

    if not token:
        print("   📝 直接设置环境变量:")
        print("   export TELEGRAM_BOT_TOKEN='8593610083:AAFPwRTuNZ_9zO8dEKSIKzUfyGF57faeRhY'")

    print("   📝 检查生产环境python-dotenv:")
    print("   pip install python-dotenv")

    print("   📝 验证Django设置:")
    print("   python manage.py shell -c \"from django.conf import settings; print(settings.TELEGRAM_BOT_TOKEN)\"")

if __name__ == "__main__":
    diagnose_env_config()