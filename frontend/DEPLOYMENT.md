# 前端部署指南

## 🚀 部署到生产环境

### 1. 环境配置

在部署之前，需要正确配置 API 基础URL：

#### 方法1：修改环境变量文件
复制 `.env.example` 为 `.env.production`：
```bash
cp .env.example .env.production
```

然后编辑 `.env.production` 文件：
```bash
# 生产环境配置
VITE_API_BASE_URL=https://your-domain.com/api
```

#### 方法2：在构建时设置环境变量
```bash
VITE_API_BASE_URL=https://your-domain.com/api npm run build
```

### 2. 构建生产版本

```bash
# 安装依赖
npm install

# 构建生产版本
npm run build
```

构建完成后，会在 `dist/` 目录生成静态文件。

### 3. 部署静态文件

将 `dist/` 目录下的所有文件部署到您的 Web 服务器或 CDN。

#### 使用 Nginx 的示例配置：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/your/dist;
    index index.html;

    # 处理 Vue Router 的 history 模式
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 静态资源缓存
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 使用 Apache 的 .htaccess 配置：

```apache
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteBase /
  RewriteRule ^index\.html$ - [L]
  RewriteCond %{REQUEST_FILENAME} !-f
  RewriteCond %{REQUEST_FILENAME} !-d
  RewriteRule . /index.html [L]
</IfModule>
```

### 4. 常见部署平台

#### Vercel
1. 连接 GitHub 仓库
2. 设置环境变量 `VITE_API_BASE_URL`
3. 自动部署

#### Netlify
1. 拖放 `dist/` 文件夹到 Netlify
2. 或连接 Git 仓库并设置构建命令：
   - Build command: `npm run build`
   - Publish directory: `dist`
   - 环境变量：`VITE_API_BASE_URL=https://your-api-domain.com/api`

#### GitHub Pages
```bash
# 安装 gh-pages
npm install --save-dev gh-pages

# 添加部署脚本到 package.json
"scripts": {
  "deploy": "npm run build && gh-pages -d dist"
}

# 部署
npm run deploy
```

## 🔧 环境变量说明

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `VITE_API_BASE_URL` | API 基础URL | `https://api.example.com/api` |

## 📝 注意事项

1. **CORS 配置**：确保后端 API 允许前端域名的跨域请求
2. **HTTPS**：生产环境建议使用 HTTPS
3. **API 路径**：确保 API 基础URL 正确，包含 `/api` 后缀
4. **环境隔离**：不同环境使用不同的 `.env` 文件

## 🐛 常见问题

### Q: 部署后请求仍然指向 127.0.0.1:8000
A: 检查环境变量是否正确设置，确保构建时使用了正确的 `.env.production` 文件。

### Q: 页面刷新后出现 404 错误
A: 需要配置服务器将所有路由重定向到 `index.html`，支持 Vue Router 的 history 模式。

### Q: 静态资源加载失败
A: 检查服务器配置，确保静态资源路径正确。

## 🔍 验证部署

部署完成后，打开浏览器开发者工具的网络面板，检查：
1. API 请求是否指向正确的域名
2. 所有静态资源是否正常加载
3. 没有 CORS 错误

---

如有问题，请检查浏览器控制台的错误信息。