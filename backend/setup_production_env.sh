#!/bin/bash
# 生产环境Telegram Bot环境变量设置脚本
# 直接设置环境变量，避免.env文件加载问题

echo "🔧 设置生产环境Telegram Bot环境变量..."

# 设置Telegram Bot配置
export TELEGRAM_BOT_TOKEN='8593610083:AAFPwRTuNZ_9zO8dEKSIKzUfyGF57faeRhY'
export TELEGRAM_BOT_USERNAME='lock_up_bot'
export TELEGRAM_WEBHOOK_URL='https://lock-down.zheermao.top/api/telegram/webhook/'
export TELEGRAM_WEBHOOK_SECRET='123456admin'
export TELEGRAM_IP_WHITELIST='149.154.160.0,149.154.161.0,149.154.162.0,172.71.182.154,172.71.182.191'

# 设置应用URL
export BASE_URL='https://lock-up.zheermao.top'
export FRONTEND_URL='https://lock-up.zheermao.top'

# 验证设置
echo "✅ 环境变量设置完成"
echo "Token: ${TELEGRAM_BOT_TOKEN:0:30}..."
echo "Webhook URL: $TELEGRAM_WEBHOOK_URL"

# 测试Django设置
echo "🧪 测试Django配置..."
python manage.py shell -c "
from django.conf import settings
print(f'Django Token: {settings.TELEGRAM_BOT_TOKEN[:30]}...')
print(f'Django Webhook: {settings.TELEGRAM_WEBHOOK_URL}')
"

echo "🚀 可以启动服务了："
echo "python manage.py runserver 0.0.0.0:8000"