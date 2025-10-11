# Lockup - 贞操锁社群App

一个专为贞操锁爱好者设计的社群应用，支持动态分享、任务管理、社交互动和游戏化功能。

## 项目结构

```
lockup/
├── backend/          # Django后端
├── frontend/         # React前端
├── docs/            # 项目文档
└── README.md        # 项目说明
```

## 技术栈

### 后端
- Django 4.2+
- Django REST Framework
- SQLite数据库
- Pydantic数据验证
- JWT认证

### 前端
- React 18+
- TypeScript
- Vite构建工具
- Shad CN UI组件库
- Tailwind CSS
- PWA支持

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

- [x] 项目规划与架构设计
- [ ] 基础环境搭建
- [ ] 用户认证系统
- [ ] 核心功能开发
- [ ] 游戏化功能
- [ ] UI/UX优化
- [ ] 测试与部署

## 开发环境

### 后端设置
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 前端设置
```bash
cd frontend
npm install
npm run dev
```

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

MIT License