#!/usr/bin/env python3
"""
Gmail SMTP 配置测试脚本
用于测试Gmail SMTP邮件发送功能
"""

import os
import sys
import django
from django.core.mail import send_mail
from django.conf import settings

# 添加项目路径
sys.path.append('/Users/joey/code/lockup/backend')

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

def test_gmail_smtp():
    """测试Gmail SMTP邮件发送"""
    print("🔧 Gmail SMTP 配置测试")
    print("=" * 50)

    # 显示当前邮件配置
    print(f"📧 邮件后端: {settings.EMAIL_BACKEND}")
    print(f"📡 SMTP主机: {settings.EMAIL_HOST}")
    print(f"🔌 SMTP端口: {settings.EMAIL_PORT}")
    print(f"🔐 使用TLS: {settings.EMAIL_USE_TLS}")
    print(f"👤 发送邮箱: {settings.EMAIL_HOST_USER}")
    print(f"🔑 密码长度: {len(settings.EMAIL_HOST_PASSWORD)} 字符")
    print(f"📨 默认发件人: {settings.DEFAULT_FROM_EMAIL}")
    print()

    # 获取测试邮箱
    test_email = input("🎯 请输入测试接收邮箱地址: ").strip()
    if not test_email:
        print("❌ 未提供测试邮箱地址")
        return False

    print(f"📤 准备发送测试邮件到: {test_email}")
    print("⏳ 发送中...")

    try:
        # 发送测试邮件
        send_mail(
            subject='🔥 锁芯社区 - Gmail SMTP 测试邮件',
            message='''
亲爱的用户，

这是一封来自锁芯社区的Gmail SMTP配置测试邮件。

如果您收到这封邮件，说明Gmail SMTP配置成功！

测试信息：
- 发送时间: 刚刚
- 邮件服务: Gmail SMTP
- 配置状态: ✅ 正常工作

感谢您的测试！

---
锁芯社区团队
https://lock-down.zheermao.top
            ''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )

        print("✅ 测试邮件发送成功！")
        print(f"📬 请检查 {test_email} 的收件箱（包括垃圾邮件文件夹）")
        print()
        print("🎉 Gmail SMTP 配置验证通过！")
        return True

    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        print()
        print("🔍 可能的问题：")
        print("1. Gmail邮箱地址不正确")
        print("2. App Password不正确或已过期")
        print("3. Gmail账户未启用两步验证")
        print("4. 网络连接问题")
        print("5. Gmail SMTP服务暂时不可用")
        return False

def show_configuration_guide():
    """显示配置指南"""
    print("\n📋 Gmail SMTP 配置指南")
    print("=" * 50)
    print("请在 .env 文件中添加以下配置：")
    print()
    print("# Gmail SMTP 配置")
    print("EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend")
    print("EMAIL_HOST=smtp.gmail.com")
    print("EMAIL_PORT=587")
    print("EMAIL_USE_TLS=true")
    print("EMAIL_HOST_USER=您的Gmail邮箱@gmail.com")
    print("EMAIL_HOST_PASSWORD=您的16位App密码")
    print("DEFAULT_FROM_EMAIL=您的Gmail邮箱@gmail.com")
    print("SERVER_EMAIL=您的Gmail邮箱@gmail.com")
    print()
    print("📝 获取App Password的步骤：")
    print("1. 登录Gmail账户")
    print("2. 前往 Google账户设置")
    print("3. 选择 '安全性'")
    print("4. 启用 '两步验证'（如果未启用）")
    print("5. 在 '两步验证' 下找到 '应用专用密码'")
    print("6. 生成新的应用专用密码")
    print("7. 复制16位密码到配置文件")

if __name__ == "__main__":
    # 检查当前配置
    if not hasattr(settings, 'EMAIL_HOST_USER') or not settings.EMAIL_HOST_USER:
        print("⚠️  未检测到Gmail SMTP配置")
        show_configuration_guide()
        sys.exit(1)

    # 运行测试
    success = test_gmail_smtp()

    if not success:
        print("\n🔧 配置帮助")
        show_configuration_guide()
        sys.exit(1)
    else:
        print("\n🚀 Gmail SMTP 配置完成，可以开始使用邮箱验证功能！")