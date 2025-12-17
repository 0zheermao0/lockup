# 数据库回退指南

## 问题描述
前端代码已回退到 commit `b20c3a0`，但服务器数据库已经执行了0012迁移，包含了多人任务相关的字段：
- `max_participants` 字段
- `TaskParticipant` 模型

## 解决方案

### 方案1: 回退数据库迁移（推荐）

在服务器上执行以下命令：

```bash
# 1. 进入后端目录
cd /path/to/backend

# 2. 激活虚拟环境（如果有）
source venv/bin/activate  # 或者其他虚拟环境激活命令

# 3. 回退到0011迁移
python manage.py migrate tasks 0011

# 4. 删除0012迁移文件（如果存在）
rm -f tasks/migrations/0012_*.py

# 5. 验证迁移状态
python manage.py showmigrations tasks
```

### 方案2: 重新部署后端代码

如果方案1不可行，可以重新部署匹配的后端代码：

```bash
# 1. 在本地拉取最新的后端代码
git checkout b20c3a0

# 2. 将后端代码上传到服务器
# 确保服务器上的后端代码也回退到相同的commit

# 3. 重启后端服务
sudo systemctl restart your-backend-service
```

### 方案3: 创建反向迁移（如果需要保留数据）

如果数据库中已经有了使用新字段的数据，需要创建反向迁移：

```bash
# 1. 创建反向迁移文件
python manage.py makemigrations tasks --empty

# 2. 编辑生成的迁移文件，添加删除字段的操作
# 3. 执行迁移
python manage.py migrate
```

## 验证步骤

### 检查迁移状态
```bash
python manage.py showmigrations tasks
```

应该显示：
```
tasks
 [X] 0001_initial
 [X] 0002_alter_locktask_status
 ...
 [X] 0011_alter_tasktimelineevent_event_type_and_more
 [ ] 0012_locktask_max_participants_taskparticipant_and_more  # 应该不存在或未应用
```

### 检查数据库表结构
```bash
# 进入数据库
python manage.py dbshell

# 查看tasks_locktask表结构
\d tasks_locktask;  # PostgreSQL
# 或
DESCRIBE tasks_locktask;  # MySQL
# 或
.schema tasks_locktask  # SQLite

# 检查是否还有max_participants字段
```

### 检查应用是否正常运行
```bash
# 启动开发服务器测试
python manage.py runserver

# 检查API是否正常响应
curl http://localhost:8000/api/tasks/
```

## 注意事项

1. **备份数据库**: 在执行任何迁移回退之前，请备份数据库
2. **检查依赖**: 确保没有其他应用依赖0012迁移中的字段
3. **数据丢失**: 回退迁移可能会导致相关数据丢失，请确认是否可接受

## 推荐执行顺序

1. 备份数据库
2. 执行方案1（回退迁移）
3. 验证应用正常运行
4. 重新部署前端文件

这样可以确保前后端代码和数据库结构完全一致。