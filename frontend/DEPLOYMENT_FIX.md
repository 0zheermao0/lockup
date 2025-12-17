# 部署问题修复指南

## 问题描述
部署后出现白屏，console报错：
- `Failed to load module script: Expected a JavaScript-or-Wasm module script but the server responded with a MIME type of "text/html"`
- `Refused to apply style from 'xxx.css' because its MIME type ('text/html') is not a supported stylesheet MIME type`

## 问题原因
服务器配置错误，将所有请求（包括静态资源）都重定向到了 `index.html`，导致 CSS 和 JS 文件无法正确加载。

## 解决方案

### 1. 确保文件完整上传
首先确保 `dist` 目录下的所有文件都已上传到服务器：
```
dist/
├── index.html
├── assets/
│   ├── index-Btw_-Z24.css
│   ├── index-DbQ_-cPe.js
│   └── ...
├── logo.jpeg
├── .htaccess (Apache服务器)
└── nginx.conf (Nginx服务器参考)
```

### 2. Apache 服务器配置
如果使用 Apache，确保 `.htaccess` 文件已上传并生效：

```apache
# 启用重写引擎
RewriteEngine On

# 对于真实存在的文件和目录，直接提供服务
RewriteCond %{REQUEST_FILENAME} -f [OR]
RewriteCond %{REQUEST_FILENAME} -d
RewriteRule ^ - [L]

# 对于assets目录下的文件，直接提供服务
RewriteRule ^assets/ - [L]

# 设置正确的MIME类型
<IfModule mod_mime.c>
    AddType text/css .css
    AddType application/javascript .js
</IfModule>

# 其他所有请求重定向到index.html
RewriteRule ^ index.html [L]
```

### 3. Nginx 服务器配置
如果使用 Nginx，添加以下配置到服务器配置文件：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/your/dist;
    index index.html;

    # 正确设置MIME类型
    location ~* \.(css)$ {
        add_header Content-Type text/css;
    }

    location ~* \.(js|mjs)$ {
        add_header Content-Type application/javascript;
    }

    # 静态资源文件
    location /assets/ {
        try_files $uri =404;
    }

    # SPA路由回退
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 4. Cloudflare 配置（如果使用）
如果通过 Cloudflare 部署，检查：
1. **Page Rules**: 确保没有规则将所有请求重定向到首页
2. **Transform Rules**: 检查是否有规则修改了静态资源的响应
3. **缓存设置**: 确保静态资源能够正确缓存

### 5. 验证修复
部署后，在浏览器开发者工具中检查：
1. Network 标签中 CSS/JS 文件的状态码应该是 200
2. Response Headers 中的 Content-Type 应该正确：
   - CSS 文件: `text/css`
   - JS 文件: `application/javascript`

### 6. 测试命令
使用以下命令测试静态资源是否正确提供：
```bash
# 测试CSS文件
curl -I https://your-domain.com/assets/index-Btw_-Z24.css

# 测试JS文件
curl -I https://your-domain.com/assets/index-DbQ_-cPe.js
```

应该返回正确的 Content-Type，而不是 `text/html`。

## 常见部署平台解决方案

### Vercel
在项目根目录创建 `vercel.json`：
```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

### Netlify
在 `dist` 目录创建 `_redirects` 文件：
```
/*    /index.html   200
```

### GitHub Pages
确保仓库设置中的发布源指向正确的分支和目录。