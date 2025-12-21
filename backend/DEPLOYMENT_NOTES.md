# 生产环境部署说明

## 环境变量配置

为了修复Mixed Content错误和确保正确的媒体文件URL生成，请在生产环境中设置以下环境变量：

### 必需的环境变量

```bash
# 明确指定生产环境
ENVIRONMENT=production

# 或者，明确指定媒体文件基础URL
MEDIA_BASE_URL=https://lock-down.zheermao.top

# 确保DEBUG为False
DEBUG=false
```

### 推荐配置

生产环境的`.env`文件应包含：

```env
# 环境标识
ENVIRONMENT=production

# 安全设置
DEBUG=false
SECRET_KEY=your-production-secret-key

# 域名配置
ALLOWED_HOSTS=lock-up.zheermao.top,lock-down.zheermao.top

# 媒体文件URL（可选，如果设置了ENVIRONMENT=production可以不设置）
MEDIA_BASE_URL=https://lock-down.zheermao.top

# 数据库等其他配置...
```

## URL生成逻辑

系统会按以下优先级确定媒体文件URL：

1. **MEDIA_BASE_URL** (最高优先级) - 如果设置，直接使用
2. **ENVIRONMENT** - 如果设置为'production'，使用HTTPS生产域名
3. **DEBUG** - 如果为False，视为生产环境
4. **默认** - DEBUG=True时，使用localhost开发URL

## 修复的问题

- ✅ 解决Mixed Content错误（HTTPS页面请求HTTP资源）
- ✅ 确保生产环境使用HTTPS URL
- ✅ 保持开发环境使用localhost URL
- ✅ 支持自定义域名配置

## 验证方法

部署后可以通过以下方式验证：

1. 检查浏览器控制台是否还有Mixed Content错误
2. 查看图片URL是否使用了正确的HTTPS域名
3. 确认所有媒体文件可以正常加载

## 回滚方案

如果出现问题，可以临时设置：

```env
MEDIA_BASE_URL=https://lock-down.zheermao.top
```

这将强制所有媒体URL使用指定的域名。