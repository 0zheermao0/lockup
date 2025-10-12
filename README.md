# Lockup - 锁芯社区平台

一个专为特定社群设计的完整社交平台，支持动态分享、任务管理、社交互动和游戏化功能。

## 项目结构

```
lockup/
├── backend/          # Django后端 (已完成)
├── frontend/         # Vue.js前端 (已完成)
├── docs/            # 项目文档
└── README.md        # 项目说明
```

## 技术栈

### 后端
- Django 4.2+
- Django REST Framework
- PostgreSQL/SQLite数据库
- Token认证
- CORS支持
- 文件上传管理

### 前端
- Vue 3 + Composition API
- TypeScript
- Vite构建工具
- Pinia状态管理
- 原生CSS (Neo-Brutalism设计风格)
- 响应式设计
- 无限滚动优化

## 功能特性

### 用户系统
- 四级用户等级制度
- 基于活跃度的升降级机制
- 用户资料管理

### 动态系统
- 图文动态发布
- 地理位置定位
- 打卡任务验证
- 社交互动（点赞、评论）

### 任务系统
- 带锁任务管理
- 复杂的时间设置
- 钥匙-管理者机制
- 投票解锁功能
- 任务榜单与悬赏

### 游戏化功能
- 转盘游戏
- 对抗小游戏
- 探索与物品发现
- 虚拟商店
- 漂流瓶系统

### 社交功能
- 好友系统
- 私聊功能
- 金币奖励机制

## 开发进度

### 已完成功能 ✅

#### 后端 (Django)
- [x] 项目架构设计与环境搭建
- [x] 用户认证系统 (Token认证)
- [x] 用户模型与权限管理
- [x] 动态系统 (发布、点赞、评论)
- [x] 任务管理系统 (带锁任务、任务榜)
- [x] 商店系统 (物品购买、背包管理)
- [x] 游戏系统 (时间转盘、石头剪刀布)
- [x] 探索系统 (宝藏埋藏与发现)
- [x] 文件上传与图片处理
- [x] RESTful API设计
- [x] 数据库模型完整性

#### 前端 (Vue.js)
- [x] Vue 3 + TypeScript 项目架构
- [x] 用户认证与路由守卫
- [x] 社区动态流 (无限滚动优化)
- [x] 任务管理界面 (懒加载优化)
- [x] 商店与背包系统
- [x] 游戏界面 (时间转盘、小游戏)
- [x] 探索系统界面
- [x] 用户个人资料管理
- [x] 响应式设计 (Neo-Brutalism风格)
- [x] 状态管理 (Pinia)
- [x] 性能优化 (无限滚动、懒加载)

#### 系统特性
- [x] 完整的用户认证流程
- [x] 动态发布与社交互动
- [x] 复杂任务管理系统
- [x] 游戏化积分系统
- [x] 物品与背包管理
- [x] 探索与收集机制
- [x] 移动端适配
- [x] 实时数据更新

### 技术亮点 🚀
- **性能优化**: 实现无限滚动和懒加载，减少70-80%网络传输
- **用户体验**: Neo-Brutalism设计风格，响应式布局
- **架构设计**: 模块化组件设计，可复用的composable函数
- **类型安全**: 全面的TypeScript支持
- **状态管理**: 基于Pinia的现代状态管理方案

## 开发环境

### 快速启动
```bash
# 克隆项目
git clone <repository-url>
cd lockup

# 后端设置
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver  # 运行在 http://127.0.0.1:8000

# 前端设置 (新终端)
cd frontend
npm install
npm run dev  # 运行在 http://localhost:5173
```

### 项目特性说明

#### 性能优化
- **无限滚动**: 社区动态和任务列表采用懒加载，显著提升性能
- **状态管理**: 使用Pinia进行高效的客户端状态管理
- **类型安全**: 完整的TypeScript类型定义

#### 设计风格
- **Neo-Brutalism**: 独特的视觉设计语言
- **响应式布局**: 完美适配移动端和桌面端
- **用户体验**: 流畅的交互动画和反馈

#### API特性
- **RESTful设计**: 标准化的API接口
- **分页支持**: 所有列表接口支持分页
- **文件上传**: 支持图片上传和处理
- **权限控制**: 基于用户角色的权限管理

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

MIT License