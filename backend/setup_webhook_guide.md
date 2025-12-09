# Telegram Bot Webhook 设置指南

## 🚀 方案1: 使用ngrok（本地开发）

### 步骤1: 启动ngrok隧道
```bash
# 在新终端窗口中运行
ngrok http 8000
```

### 步骤2: 复制HTTPS URL
ngrok会显示类似这样的信息：
```
Session Status                online
Account                       your-account
Version                       3.x.x
Region                        United States (us)
Forwarding                    https://abc123.ngrok.io -> http://localhost:8000
```

复制 `https://abc123.ngrok.io` 这个URL

### 步骤3: 设置Webhook
```bash
# 在backend目录下运行
source venv/bin/activate
python manage.py setup_telegram --set-webhook https://abc123.ngrok.io/api/telegram/webhook/
```

### 步骤4: 验证设置
```bash
python manage.py setup_telegram --info
```

---

## 🌐 方案2: 使用其他隧道工具

### 选项A: 使用Cloudflare Tunnel
```bash
# 安装cloudflared
brew install cloudflared

# 启动隧道
cloudflared tunnel --url http://localhost:8000
```

### 选项B: 使用localtunnel
```bash
# 安装localtunnel
npm install -g localtunnel

# 启动隧道
lt --port 8000
```

---

## 🏭 方案3: 生产环境部署

如果你有服务器，可以直接设置生产环境的webhook：
```bash
python manage.py setup_telegram --set-webhook https://your-domain.com/api/telegram/webhook/
```

---

## 🔧 手动设置Webhook（备用方案）

如果管理命令有问题，可以手动设置：

```bash
# 使用curl直接调用Telegram API
curl -X POST "https://api.telegram.org/bot8593610083:AAEHkca4MOhtkaDJRQnQtzYQVDloWLIiJsE/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-ngrok-url.ngrok.io/api/telegram/webhook/",
    "allowed_updates": ["message", "callback_query"]
  }'
```

---

## ✅ 测试绑定流程

设置好webhook后：

1. **在Telegram中找到你的Bot**: @lock_up_bot
2. **发送 /start 命令**
3. **Bot应该会回复欢迎消息**
4. **在应用中点击"打开Telegram Bot"按钮**
5. **应该会跳转到Bot并自动发送带参数的/start**
6. **Bot处理绑定逻辑并更新数据库**
7. **应用中显示绑定成功**

---

## 🐛 故障排除

### 问题1: ngrok连接失败
- 检查网络连接
- 尝试不同的region: `ngrok http 8000 --region=ap`

### 问题2: Webhook设置失败
- 确保URL是HTTPS
- 检查Bot Token是否正确
- 确认端口8000可访问

### 问题3: Bot不响应
- 检查Django服务器是否运行在8000端口
- 查看Django日志是否收到webhook请求
- 验证webhook URL路径正确

### 问题4: 绑定不成功
- 检查数据库连接
- 查看Django日志中的错误信息
- 确认用户已登录应用

---

## 📝 注意事项

1. **安全性**: 生产环境应该设置webhook secret token
2. **稳定性**: ngrok免费版有连接限制，长期使用建议升级
3. **调试**: 可以在Django settings中启用详细日志查看webhook请求