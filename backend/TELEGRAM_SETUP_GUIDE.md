# Telegram Bot 设置指南

## 🚨 重要发现
当前Bot配置状态：
- ✅ Bot Token 有效
- ✅ Bot名称：锁芯
- ✅ Bot用户名：@lock_up_bot
- ❌ **Inline Mode 未启用**（这是核心功能，必须启用）

## 📋 必需的配置步骤

### 1. 启用 Inline Mode
**这是最重要的步骤！** 我们的加时功能依赖于 Inline Mode。

1. 在 Telegram 中找到 @BotFather
2. 发送 `/setinline`
3. 选择你的 Bot：@lock_up_bot
4. 设置 Inline 提示文本，例如：`输入朋友的用户名来给他们的任务加时`
5. 完成后，Bot 就支持 Inline Mode 了

### 2. 设置 Webhook（生产环境）

#### 方法一：使用 Django 管理命令（推荐）
```bash
# 激活虚拟环境
source venv/bin/activate

# 查看当前状态
python manage.py setup_telegram --info

# 设置 Webhook
python manage.py setup_telegram --set-webhook

# 删除 Webhook（如果需要）
python manage.py setup_telegram --delete-webhook
```

#### 方法二：使用交互式脚本
```bash
source venv/bin/activate
python setup_telegram_webhook.py
```

### 3. 配置环境变量

创建 `.env` 文件（基于 `.env.example`）：
```bash
cp .env.example .env
```

编辑 `.env` 文件，确保以下配置正确：
```env
# 已配置的值
TELEGRAM_BOT_TOKEN=8593610083:AAEHkca4MOhtkaDJRQnQtzYQVDloWLIiJsE
TELEGRAM_BOT_USERNAME=lock_up_bot
TELEGRAM_WEBHOOK_URL=https://lock-down.zheermao.top/telegram/webhook/

# 生产环境强烈推荐设置
TELEGRAM_WEBHOOK_SECRET=your-secret-token-here

# 其他配置
BASE_URL=https://lock-up.zheermao.top
FRONTEND_URL=https://lock-up.zheermao.top
```

### 4. 测试 Webhook 连接

在设置 Webhook 之前，确保你的服务器：
1. ✅ 已部署到 `https://lock-down.zheermao.top`
2. ✅ `/telegram/webhook/` 端点可访问
3. ✅ 使用 HTTPS（Telegram 要求）

### 5. 验证配置

设置完成后，运行以下命令验证：
```bash
python manage.py setup_telegram --info
```

应该看到：
- ✅ Bot信息正常
- ✅ 支持Inline Mode: 是
- ✅ Webhook URL 已设置

## 🎮 功能测试

### Inline Mode 测试
1. 在任何 Telegram 聊天中输入：`@lock_up_bot joey`
2. 应该显示用户 joey 的活跃任务列表
3. 点击任务可以给该任务加时

### Webhook 测试
1. 向 Bot 发送 `/start` 命令
2. 检查服务器日志是否收到 webhook 请求

### 绑定测试
1. 在应用中访问用户资料页
2. 点击"打开 Telegram Bot"按钮
3. 应该跳转到 `https://t.me/lock_up_bot?start=bind_...`

## 🔧 故障排除

### Webhook 设置失败
- 检查 URL 是否可访问
- 确保使用 HTTPS
- 验证 Django 服务器是否运行
- 检查防火墙设置

### Inline Mode 不工作
- 确保在 @BotFather 中启用了 Inline Mode
- 检查用户是否已绑定账户
- 验证数据库中是否有活跃任务

### Bot 不响应
- 检查 Token 是否正确
- 验证 Webhook URL 是否正确
- 查看服务器错误日志

## 📚 相关文件

- `backend/lockup_backend/settings.py` - Django 配置
- `backend/telegram_bot/services.py` - Bot 核心服务
- `backend/telegram_bot/views.py` - API 端点和 Webhook 处理
- `frontend/src/lib/api-telegram.ts` - 前端 API 客户端
- `frontend/src/views/ProfileView.vue` - 用户资料页（绑定界面）

## 🚀 下一步

1. **立即执行**：启用 Bot 的 Inline Mode
2. **部署后**：设置 Webhook
3. **测试**：验证所有功能正常工作

完成这些步骤后，你的 Telegram Bot 就可以完全正常工作了！