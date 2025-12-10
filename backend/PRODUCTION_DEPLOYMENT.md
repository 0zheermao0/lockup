# 生产环境Telegram Bot配置指南

## 问题描述
生产环境出现 "Telegram Bot Token not configured" 错误，说明.env文件配置没有正确加载。

## 解决方案

### 方案1: 检查和修复.env文件（推荐）

1. **运行诊断脚本**
```bash
cd /path/to/your/app
python diagnose_env.py
```

2. **检查.env文件是否存在**
```bash
ls -la .env
cat .env | grep TELEGRAM_BOT_TOKEN
```

3. **如果.env文件不存在，创建它**
```bash
cat > .env << 'EOF'
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=8593610083:AAFPwRTuNZ_9zO8dEKSIKzUfyGF57faeRhY
TELEGRAM_BOT_USERNAME=lock_up_bot
TELEGRAM_WEBHOOK_URL=https://lock-down.zheermao.top/api/telegram/webhook/
TELEGRAM_WEBHOOK_SECRET=123456admin
TELEGRAM_IP_WHITELIST=149.154.160.0,149.154.161.0,149.154.162.0,172.71.182.154,172.71.182.191

# 应用URL配置
BASE_URL=https://lock-up.zheermao.top
FRONTEND_URL=https://lock-up.zheermao.top
EOF
```

4. **确保python-dotenv已安装**
```bash
pip install python-dotenv
```

### 方案2: 使用环境变量（备用方案）

如果.env文件无法工作，直接设置环境变量：

```bash
export TELEGRAM_BOT_TOKEN='8593610083:AAFPwRTuNZ_9zO8dEKSIKzUfyGF57faeRhY'
export TELEGRAM_BOT_USERNAME='lock_up_bot'
export TELEGRAM_WEBHOOK_URL='https://lock-down.zheermao.top/api/telegram/webhook/'
export TELEGRAM_WEBHOOK_SECRET='123456admin'
export TELEGRAM_IP_WHITELIST='149.154.160.0,149.154.161.0,149.154.162.0,172.71.182.154,172.71.182.191'
```

### 方案3: 系统服务配置

对于systemd服务，在服务文件中添加环境变量：

```ini
[Service]
Environment=TELEGRAM_BOT_TOKEN=8593610083:AAFPwRTuNZ_9zO8dEKSIKzUfyGF57faeRhY
Environment=TELEGRAM_BOT_USERNAME=lock_up_bot
Environment=TELEGRAM_WEBHOOK_URL=https://lock-down.zheermao.top/api/telegram/webhook/
```

### 方案4: Docker环境

如果使用Docker，在docker-compose.yml中配置：

```yaml
version: '3'
services:
  app:
    environment:
      - TELEGRAM_BOT_TOKEN=8593610083:AAFPwRTuNZ_9zO8dEKSIKzUfyGF57faeRhY
      - TELEGRAM_BOT_USERNAME=lock_up_bot
      - TELEGRAM_WEBHOOK_URL=https://lock-down.zheermao.top/api/telegram/webhook/
```

## 验证配置

1. **验证Django设置**
```bash
python manage.py shell -c "from django.conf import settings; print('Token:', settings.TELEGRAM_BOT_TOKEN[:30] + '...' if settings.TELEGRAM_BOT_TOKEN else 'NOT_SET')"
```

2. **测试Bot初始化**
```bash
python manage.py shell -c "
from telegram_bot.services import telegram_service
import asyncio

async def test():
    if await telegram_service._ensure_initialized():
        bot_info = await telegram_service.bot.get_me()
        print(f'Bot: @{bot_info.username}')
        return True
    return False

result = asyncio.run(test())
print('Bot initialized:', result)
"
```

3. **检查日志**
```bash
# 检查应用日志中是否还有"Token not configured"错误
tail -f /path/to/your/logs/app.log | grep -i telegram
```

## 重启服务

配置完成后，重启应用服务：

```bash
# 如果使用systemd
sudo systemctl restart your-app-service

# 如果使用gunicorn
pkill -f gunicorn
gunicorn --bind 0.0.0.0:8000 lockup_backend.wsgi:application

# 如果使用Docker
docker-compose restart app
```

## 故障排除

### 常见问题

1. **权限问题**
```bash
chmod 600 .env  # 确保.env文件有正确权限
```

2. **文件路径问题**
```bash
# 确保.env文件在正确位置（与manage.py同级）
ls -la | grep -E "(manage.py|\.env)"
```

3. **依赖问题**
```bash
pip list | grep python-dotenv
```

### 调试命令

```bash
# 检查所有环境变量
env | grep TELEGRAM

# 检查Python路径
python -c "import os; print(os.getcwd())"

# 手动测试dotenv加载
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print(os.getenv('TELEGRAM_BOT_TOKEN', 'NOT_FOUND'))
"
```

## 安全注意事项

1. **保护.env文件**
   - 确保.env文件不被提交到版本控制
   - 设置适当的文件权限 (600)

2. **生产环境建议**
   - 使用环境变量而不是.env文件
   - 定期轮换Bot Token
   - 启用webhook secret验证

## 联系支持

如果问题仍然存在，提供以下信息：
1. 诊断脚本输出
2. 应用日志
3. 服务器环境信息
4. 部署方式（Docker/systemd/其他）