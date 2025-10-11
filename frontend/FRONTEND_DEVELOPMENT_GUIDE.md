# Vue 3 + TypeScript 前端开发指南

## 项目概述

这是一个社交社区应用的前端项目，使用Vue 3 + TypeScript + Vite技术栈构建。主要功能包括用户认证、社交动态、位置打卡等功能。

## 技术栈

- **框架**: Vue 3 (Composition API)
- **语言**: TypeScript 4.x+
- **构建工具**: Vite 7.x
- **状态管理**: Pinia
- **路由**: Vue Router 4
- **HTTP客户端**: Fetch API (自定义封装)
- **开发服务器**: 前端 http://localhost:5173, 后端 http://127.0.0.1:8000

## 项目结构

```
frontend/
├── src/
│   ├── assets/          # 静态资源
│   │   └── main.css     # 全局样式
│   ├── lib/             # 核心库文件
│   │   └── api.ts       # API请求封装
│   │   └── utils.ts     # 工具函数
│   ├── stores/          # Pinia状态管理
│   │   ├── auth.ts      # 认证状态
│   │   └── posts.ts     # 动态数据
│   ├── types/           # TypeScript类型定义
│   │   └── index.ts     # 全部类型定义
│   ├── views/           # 页面组件
│   │   ├── HomeView.vue     # 主页
│   │   ├── LoginView.vue    # 登录页
│   │   └── RegisterView.vue # 注册页
│   ├── router/          # 路由配置
│   │   └── index.ts     # 路由定义和守卫
│   ├── App.vue          # 根组件
│   └── main.ts          # 应用入口
├── package.json
├── tsconfig.json        # TypeScript配置
├── vite.config.ts       # Vite配置
└── FRONTEND_DEVELOPMENT_GUIDE.md  # 本文档
```

## 关键特性

### 1. 状态管理 (Pinia)

#### 认证状态 (`src/stores/auth.ts`)
```typescript
// 使用示例
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// 登录
await authStore.login({ username, password })

// 检查认证状态
if (authStore.isAuthenticated) {
  // 用户已登录
}

// 登出
authStore.logout()
```

#### 动态数据 (`src/stores/posts.ts`)
```typescript
import { usePostsStore } from '@/stores/posts'

const postsStore = usePostsStore()

// 获取动态
await postsStore.fetchPosts()

// 点赞/取消点赞
await postsStore.likePost(postId)
await postsStore.unlikePost(postId)
```

### 2. 路由守卫 (`src/router/index.ts`)

- **认证保护**: `requiresAuth: true` 的路由需要登录
- **访客页面**: `requiresGuest: true` 的路由已登录用户会重定向到首页
- **自动重定向**: 未认证用户访问保护页面会自动跳转到登录页

### 3. API封装 (`src/lib/api.ts`)

```typescript
// 认证API
authApi.login(credentials)
authApi.register(userData)
authApi.logout()

// 动态API
postsApi.getPosts(params)
postsApi.createPost(postData)
postsApi.likePost(postId)
```

### 4. 类型安全 (`src/types/index.ts`)

所有API响应、组件props、状态数据都有完整的TypeScript类型定义。

## 常见问题及解决方案

### 1. 模块导入错误

**问题**: `Uncaught SyntaxError: The requested module '/src/types/index.ts' does not provide an export named 'LoginRequest'`

**原因**: TypeScript模块导入路径解析问题

**解决方案**:
```typescript
// ❌ 错误写法
import { LoginRequest } from '../types/index'

// ✅ 正确写法
import type { LoginRequest } from '../types/index.js'
```

**最佳实践**:
- 类型导入使用 `import type` 语法
- 模块路径使用 `.js` 扩展名 (即使源文件是.ts)
- 避免循环依赖

### 2. PostCSS/Tailwind配置冲突

**问题**: `Failed to load PostCSS config... Cannot find module '@tailwindcss/postcss'`

**解决方案**:
- 移除 `postcss.config.js`
- 移除 `tailwind.config.js`
- 清理CSS文件中的Tailwind指令
- 使用原生CSS或Vue的scoped样式

### 3. 白屏问题排查

**排查步骤**:
1. 检查浏览器控制台错误
2. 使用curl测试各个模块加载状态:
   ```bash
   curl -s http://localhost:5173/src/main.ts
   curl -s http://localhost:5173/src/App.vue
   curl -s http://localhost:5173/src/lib/api.ts
   ```
3. 检查Vite开发服务器日志
4. 验证TypeScript编译无错误

### 4. 跨框架污染问题

**问题**: 在Vue项目中错误引用React类型

**解决方案**:
```typescript
// ❌ 错误 - 在Vue项目中引用React类型
icon: React.ComponentType<{ className?: string }>

// ✅ 正确 - 使用通用类型
icon: any // 或定义Vue特定的组件类型
```

## 开发最佳实践

### 1. 代码组织

- **单一职责**: 每个文件专注单一功能
- **类型先行**: 优先定义TypeScript类型
- **组合式API**: 使用Vue 3 Composition API
- **状态集中**: 复杂状态使用Pinia管理

### 2. 错误处理

```typescript
// API调用错误处理
try {
  const response = await authApi.login(credentials)
  // 成功处理
} catch (error) {
  console.error('Login failed:', error)
  // 错误提示给用户
}
```

### 3. 类型安全

```typescript
// 定义明确的接口
interface LoginRequest {
  username: string
  password: string
}

// 使用泛型
const response = await apiRequest<AuthResponse>('/auth/login/', options)
```

### 4. 组件设计

```vue
<script setup lang="ts">
// 明确的props类型
interface Props {
  title: string
  count?: number
}

// 使用组合式API
const props = defineProps<Props>()
const emit = defineEmits<{
  click: [id: string]
}>()
</script>
```

## 调试技巧

### 1. Vue DevTools
- 安装Vue DevTools浏览器扩展
- 查看组件状态和Pinia store

### 2. 网络调试
```typescript
// API请求添加日志
console.log('API Request:', endpoint, options)
console.log('API Response:', response)
```

### 3. Vite调试
- 检查 `http://localhost:5173/__devtools__/`
- 查看HMR更新日志

## 部署注意事项

### 1. 环境变量
```typescript
// 使用Vite环境变量
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'
```

### 2. 构建优化
```bash
# 生产构建
npm run build

# 预览构建结果
npm run preview
```

### 3. 类型检查
```bash
# TypeScript类型检查
npx tsc --noEmit
```

## 常用命令

```bash
# 开发服务器
npm run dev

# 类型检查
npm run type-check

# 代码构建
npm run build

# 依赖管理
npm install
npm install <package-name>
npm uninstall <package-name>

# 清理缓存
rm -rf node_modules/.vite
npm run dev
```

## 故障排除清单

当遇到问题时，按以下顺序检查:

1. **检查控制台错误** - 浏览器开发者工具
2. **验证服务器状态** - 前端和后端服务都在运行
3. **检查模块导入** - 确保导入路径正确
4. **清理缓存** - 删除 `node_modules/.vite`
5. **重启服务** - 重新启动开发服务器
6. **类型检查** - 运行 `npx tsc --noEmit`
7. **依赖检查** - 确保所有必要的包已安装

## 性能优化建议

### 1. 代码分割
```typescript
// 路由懒加载
const AboutView = () => import('../views/AboutView.vue')
```

### 2. API优化
```typescript
// 请求去重和缓存
const cache = new Map()
const apiRequest = async (url: string) => {
  if (cache.has(url)) return cache.get(url)
  const response = await fetch(url)
  cache.set(url, response)
  return response
}
```

### 3. 状态优化
```typescript
// 避免不必要的响应式
import { markRaw } from 'vue'
const staticData = markRaw(largeObject)
```

## 扩展功能建议

1. **UI组件库集成** - 如 Element Plus、Ant Design Vue
2. **国际化支持** - Vue I18n
3. **主题系统** - CSS变量 + 动态切换
4. **离线支持** - Service Worker + PWA
5. **测试框架** - Vitest + Vue Test Utils
6. **代码质量** - ESLint + Prettier

## 联系与支持

- 项目文档: 本文件
- API文档: 后端提供的API接口文档
- 技术栈官方文档:
  - [Vue 3](https://vuejs.org/)
  - [TypeScript](https://www.typescriptlang.org/)
  - [Vite](https://vitejs.dev/)
  - [Pinia](https://pinia.vuejs.org/)

---

**最后更新**: 2025-10-11
**维护者**: Claude Code Assistant
**版本**: 1.0.0