# 活跃度衰减系统 - Django 管理命令

本文档介绍了活跃度衰减系统的Django管理命令，这些命令用于管理和监控Celery定期任务。

## 📋 可用命令

### 1. 设置活跃度衰减任务

**命令**: `python manage.py setup_activity_decay_task`

**功能**: 创建或更新活跃度衰减的Celery定期任务到数据库中。

**参数**:
- `--hour` (默认: 4) - 执行时间（小时，0-23）
- `--minute` (默认: 45) - 执行时间（分钟，0-59）
- `--timezone` (默认: Asia/Shanghai) - 时区设置
- `--force` - 强制覆盖已存在的任务
- `--disable` - 创建任务但设为禁用状态

**示例**:
```bash
# 使用默认设置（每日4:45执行）
python manage.py setup_activity_decay_task

# 设置为每日2:30执行
python manage.py setup_activity_decay_task --hour 2 --minute 30

# 强制覆盖现有任务
python manage.py setup_activity_decay_task --force

# 创建禁用的任务
python manage.py setup_activity_decay_task --disable
```

### 2. 手动执行活跃度衰减

**命令**: `python manage.py run_activity_decay`

**功能**: 手动执行活跃度衰减处理，用于测试和紧急处理。

**参数**:
- `--dry-run` - 只显示将要处理的用户，不实际执行
- `--user USER` - 只处理指定用户名的用户
- `--days-threshold N` (默认: 1) - 处理最后活跃时间超过N天的用户
- `--min-activity N` (默认: 1) - 只处理活跃度≥N的用户
- `--verbose` - 显示详细处理信息

**示例**:
```bash
# 模拟执行，查看将要处理的用户
python manage.py run_activity_decay --dry-run --verbose

# 实际执行衰减处理
python manage.py run_activity_decay

# 只处理特定用户
python manage.py run_activity_decay --user testuser

# 处理超过3天未活跃的用户
python manage.py run_activity_decay --days-threshold 3
```

### 3. 检查任务状态

**命令**: `python manage.py check_activity_decay_task`

**功能**: 检查活跃度衰减任务的配置、状态和执行历史。

**参数**:
- `--history N` (默认: 10) - 显示最近N次执行历史
- `--enable` - 启用任务
- `--disable` - 禁用任务

**示例**:
```bash
# 检查任务状态
python manage.py check_activity_decay_task

# 启用任务
python manage.py check_activity_decay_task --enable

# 禁用任务
python manage.py check_activity_decay_task --disable

# 查看更多执行历史
python manage.py check_activity_decay_task --history 20
```

## 🚀 快速开始

### 初次设置

1. **创建定期任务**:
   ```bash
   python manage.py setup_activity_decay_task
   ```

2. **验证任务创建**:
   ```bash
   python manage.py check_activity_decay_task
   ```

3. **测试手动执行**:
   ```bash
   python manage.py run_activity_decay --dry-run --verbose
   ```

### 日常管理

1. **检查任务状态**:
   ```bash
   python manage.py check_activity_decay_task
   ```

2. **紧急手动处理**:
   ```bash
   python manage.py run_activity_decay
   ```

3. **查看特定用户**:
   ```bash
   python manage.py run_activity_decay --user username --dry-run
   ```

## ⚙️ 系统要求

### Celery 服务

确保以下Celery服务正在运行：

1. **Celery Beat调度器**:
   ```bash
   celery -A celery_app beat
   ```

2. **Celery Worker**:
   ```bash
   celery -A celery_app worker
   ```

### 数据库表

系统使用以下数据库表：
- `django_celery_beat_periodictask` - 定期任务配置
- `django_celery_beat_crontabschedule` - Cron调度配置
- `activity_logs` - 活跃度变化日志
- `users_user` - 用户表（包含活跃度字段）

## 📊 监控和日志

### Django Admin界面

访问 `/admin/django_celery_beat/periodictask/` 查看和管理定期任务。

### 活跃度日志

访问 `/admin/users/activitylog/` 查看活跃度变化历史。

### 任务执行日志

如果安装了 `django-celery-results`，可以在Admin中查看任务执行历史。

## 🔧 故障排除

### 常见问题

1. **任务未执行**:
   - 检查Celery Beat是否运行
   - 检查任务是否启用
   - 查看Celery日志

2. **衰减计算错误**:
   - 使用 `--dry-run` 模式测试
   - 检查用户的 `last_active` 时间

3. **权限问题**:
   - 确保数据库连接正常
   - 检查Django设置

### 调试命令

```bash
# 检查Django配置
python manage.py check

# 查看定期任务列表
python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print([t.name for t in PeriodicTask.objects.all()])"

# 手动测试衰减计算
python manage.py shell -c "from users.models import User; u=User.objects.first(); print(f'Decay: {u.calculate_fibonacci_decay()}')"
```

## 📝 注意事项

1. **时区设置**: 确保时区设置正确，默认使用 `Asia/Shanghai`
2. **数据备份**: 建议在首次运行前备份用户数据
3. **性能考虑**: 大量用户时考虑分批处理
4. **监控告警**: 建议设置监控，及时发现任务执行异常

## 🔗 相关文件

- 任务实现: `tasks/celery_tasks.py:process_activity_decay`
- 用户模型: `users/models.py:User.apply_time_decay`
- Celery配置: `celery_app.py`
- 管理命令: `tasks/management/commands/`

---

*最后更新: 2024-12-25*
*作者: Claude Code*