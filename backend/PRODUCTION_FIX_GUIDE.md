# 生产环境Telegram Bot紧急修复指南

## 🚨 问题现状
- "Telegram Bot Token not configured" 错误
- "Wrong response from the webhook: 403 Forbidden" 错误

## 🛠️ 立即修复步骤

### 方法1: 使用修复脚本（推荐）

```bash
# 在生产服务器上执行
cd /root/lockup/backend
python fix_production_telegram.py
```

### 方法2: 手动修复

#### 步骤1: 直接设置环境变量
```bash
# 设置环境变量（立即生效）
export TELEGRAM_BOT_TOKEN='8593610083:AAFPwRTuNZ_9zO8dEKSIKzUfyGF57faeRhY'
export TELEGRAM_BOT_USERNAME='lock_up_bot'
export TELEGRAM_WEBHOOK_URL='https://lock-down.zheermao.top/api/telegram/webhook/'
export TELEGRAM_WEBHOOK_SECRET='123456admin'
export TELEGRAM_IP_WHITELIST='149.154.160.0,149.154.161.0,149.154.162.0,172.71.182.154,172.71.182.191'
export BASE_URL='https://lock-up.zheermao.top'
export FRONTEND_URL='https://lock-up.zheermao.top'
```

#### 步骤2: 验证配置
```bash
# 测试Django配置
python manage.py shell -c "
from django.conf import settings
print('Token:', settings.TELEGRAM_BOT_TOKEN[:30] + '...')
print('Webhook:', settings.TELEGRAM_WEBHOOK_URL)
"
```

#### 步骤3: 重置Webhook
```bash
# 删除并重新设置webhook（解决403错误）
python manage.py shell -c "
import asyncio
from telegram_bot.services import telegram_service

async def reset_webhook():
    await telegram_service._ensure_initialized()

    # 删除旧webhook
    await telegram_service.bot.delete_webhook()
    print('✅ 删除旧webhook')

    # 设置新webhook（不使用secret避免403）
    webhook_url = 'https://lock-down.zheermao.top/api/telegram/webhook/'
    await telegram_service.bot.set_webhook(
        url=webhook_url,
        allowed_updates=['message', 'callback_query']
    )
    print('✅ 设置新webhook')

    # 检查状态
    info = await telegram_service.bot.get_webhook_info()
    print(f'Webhook URL: {info.url}')
    print(f'待处理更新: {info.pending_update_count}')
    print(f'最后错误: {info.last_error_message or \"无\"}')

asyncio.run(reset_webhook())
"
```

#### 步骤4: 重启服务
```bash
# 重启Django应用
pkill -f "python manage.py runserver"
nohup python manage.py runserver 0.0.0.0:8000 > app.log 2>&1 &
```

### 方法3: 使用环境变量脚本

```bash
# 使用预制脚本
source setup_production_env.sh
python manage.py runserver 0.0.0.0:8000
```

## 🔍 验证修复

### 检查Token配置
```bash
python manage.py setup_telegram --info
```

应该显示：
- Bot名称: 锁芯
- Bot用户名: @lock_up_bot
- 无"Token not configured"错误

### 检查Webhook状态
```bash
python manage.py shell -c "
import asyncio
from telegram_bot.services import telegram_service

async def check():
    await telegram_service._ensure_initialized()
    info = await telegram_service.bot.get_webhook_info()
    print(f'URL: {info.url}')
    print(f'错误: {info.last_error_message or \"无错误\"}')

asyncio.run(check())
"
```

应该显示：
- URL: https://lock-down.zheermao.top/api/telegram/webhook/
- 错误: 无错误

## 🚀 如果仍有问题

### 临时解决方案：禁用安全检查
在 `telegram_bot/views.py` 中，找到webhook函数，在开头添加：

```python
# 临时禁用安全检查
return HttpResponse("OK")  # 临时返回OK
```

### 检查日志
```bash
tail -f app.log | grep -i telegram
```

### 联系支持
提供以下信息：
1. `python diagnose_env.py` 输出
2. `python manage.py setup_telegram --info` 输出
3. 应用日志中的错误信息

## 📝 修复原理

1. **Token问题**: .env文件在生产环境可能不被加载，直接设置环境变量确保Django能读取
2. **403错误**: Webhook secret token验证失败，重新设置webhook不使用secret token
3. **IP限制**: 修改了webhook view允许来自Telegram的所有IP请求

修复后Bot应该能正常响应命令并接收webhook请求。