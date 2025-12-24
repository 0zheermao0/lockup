# Celery Beat 统一设置指南

本文档介绍如何使用统一的 `setup_celery_beat` 命令来初始化和管理所有系统定时任务。

## 📋 概述

`setup_celery_beat` 命令现在可以一次性设置所有系统需要的定时任务，包括：

### 🕐 定时任务清单

| 任务名称 | 执行频率 | 队列 | 功能描述 |
|---------|---------|------|----------|
| **process-hourly-rewards** | 每小时 | rewards | 处理活跃带锁任务的小时奖励 |
| **auto-freeze-strict-mode-tasks** | 每日 4:15 AM (UTC) | default | 自动冻结24小时内无打卡的严格模式任务 |
| **process-level-promotions** | 每周三 4:30 AM (UTC) | default | 批量处理用户等级晋升 |
| **process-activity-decay** | 每日 4:45 AM (Asia/Shanghai) | activity | 基于斐波那契数列的活跃度衰减处理 |
| **process-checkin-voting-results** | 每日 4:00 AM (Asia/Shanghai) | default | 处理过期的打卡投票会话并分发奖励 |
| **process-pinning-queue** | 每分钟 | default | 处理用户置顶队列，移除过期用户，激活等待用户 |
| **pinning-health-check** | 每5分钟 | default | 监控置顶系统健康状态并检测问题 |

## 🚀 使用方法

### 基本命令

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置所有定时任务
python manage.py setup_celery_beat

# 查看将要执行的操作（不实际修改数据）
python manage.py setup_celery_beat --dry-run

# 删除所有定时任务
python manage.py setup_celery_beat --delete

# 删除前预览（不实际删除）
python manage.py setup_celery_beat --delete --dry-run
```

### 命令参数

| 参数 | 描述 |
|------|------|
| `--dry-run` | 只显示将要执行的操作，不实际修改数据库 |
| `--delete` | 删除现有的定时任务而不是创建它们 |

## 📊 系统架构

### 队列分配策略

```
rewards 队列:
├── process-hourly-rewards (高频率，专门处理奖励)

activity 队列:
├── process-activity-decay (用户数据处理，独立队列)

default 队列:
├── auto-freeze-strict-mode-tasks
├── process-level-promotions
├── process-checkin-voting-results
├── process-pinning-queue
└── pinning-health-check
```

### 时间安排设计

```
每日时间线 (Asia/Shanghai):
04:00 - 打卡投票结果处理
04:15 - 自动冻结严格模式任务 (UTC)
04:30 - 用户等级晋升 (UTC, 仅周三)
04:45 - 活跃度衰减处理

高频任务:
每分钟 - 置顶队列处理
每5分钟 - 置顶系统健康检查
每小时 - 小时奖励处理
```

## 🔧 开发者使用指南

### 新项目部署

```bash
# 1. 初始化数据库迁移
python manage.py migrate

# 2. 设置所有定时任务
python manage.py setup_celery_beat

# 3. 启动 Celery Beat 调度器
celery -A celery_app beat -l info

# 4. 启动 Celery Worker
celery -A celery_app worker -l info

# 5. 或者按队列启动多个 Worker
celery -A celery_app worker -Q rewards -l info &
celery -A celery_app worker -Q activity -l info &
celery -A celery_app worker -Q default -l info &
```

### 更新现有部署

```bash
# 1. 更新定时任务配置
python manage.py setup_celery_beat

# 2. 重启 Celery 服务
# (Celery Beat 会自动检测数据库中的任务变化)
```

### 添加新的定时任务

当需要添加新的定时任务时，请按以下步骤操作：

1. **在 `tasks/celery_tasks.py` 中实现任务函数**
2. **修改 `setup_celery_beat.py` 命令**:
   - 在 `_create_periodic_tasks` 方法中添加新任务的设置逻辑
   - 在 `task_names` 列表中添加任务名称
   - 在显示配置的部分添加新任务的信息显示
3. **运行命令更新任务**:
   ```bash
   python manage.py setup_celery_beat
   ```

### 示例：添加新任务

```python
# 在 setup_celery_beat.py 中添加
# ========================================================================
# 新任务设置
# ========================================================================

self.stdout.write('\n' + '=' * 60)
self.stdout.write(self.style.SUCCESS('Setting up new task...'))

# 创建调度
new_schedule, created = CrontabSchedule.objects.get_or_create(
    minute=0,
    hour=6,
    day_of_week='*',
    day_of_month='*',
    month_of_year='*',
    timezone='Asia/Shanghai',
)

# 创建任务
new_task_name = 'new-task-name'
new_task_function = 'tasks.celery_tasks.new_task_function'

new_periodic_task, created = PeriodicTask.objects.get_or_create(
    name=new_task_name,
    defaults={
        'crontab': new_schedule,
        'task': new_task_function,
        'kwargs': json.dumps({}),
        'enabled': True,
        'description': '新任务的描述',
        'queue': 'default',
    }
)
```

## 🔍 监控和管理

### Django Admin 界面

访问以下URL查看和管理定时任务：

- **定时任务管理**: `/admin/django_celery_beat/periodictask/`
- **Cron调度管理**: `/admin/django_celery_beat/crontabschedule/`
- **间隔调度管理**: `/admin/django_celery_beat/intervalschedule/`

### 命令行检查

```bash
# 检查活跃度衰减任务状态
python manage.py check_activity_decay_task

# 手动执行活跃度衰减（测试）
python manage.py run_activity_decay --dry-run

# 手动处理等级晋升
python manage.py process_level_promotions --dry-run
```

### 日志监控

```bash
# 查看 Celery Beat 日志
celery -A celery_app beat -l info

# 查看 Worker 日志
celery -A celery_app worker -l info

# 查看特定队列的 Worker 日志
celery -A celery_app worker -Q rewards -l info
```

## 🛠️ 故障排除

### 常见问题

1. **任务不执行**
   ```bash
   # 检查 Celery Beat 是否运行
   ps aux | grep "celery.*beat"

   # 检查任务是否启用
   python manage.py setup_celery_beat --dry-run
   ```

2. **队列阻塞**
   ```bash
   # 检查 Worker 状态
   celery -A celery_app inspect active

   # 重启特定队列的 Worker
   celery -A celery_app worker -Q rewards --purge
   ```

3. **时区问题**
   ```bash
   # 检查系统时区设置
   python manage.py shell -c "from django.utils import timezone; print(timezone.now())"
   ```

### 重置所有任务

```bash
# 删除所有任务
python manage.py setup_celery_beat --delete

# 重新创建所有任务
python manage.py setup_celery_beat

# 验证设置
python manage.py setup_celery_beat --dry-run
```

## 📈 性能优化建议

### Worker 配置

```bash
# 针对不同队列优化并发数
celery -A celery_app worker -Q rewards -c 2 -l info    # 奖励队列：低并发
celery -A celery_app worker -Q activity -c 1 -l info   # 活跃度队列：单线程
celery -A celery_app worker -Q default -c 4 -l info    # 默认队列：高并发
```

### 监控指标

- **任务执行频率**: 监控高频任务（如置顶队列处理）的执行情况
- **队列长度**: 避免队列积压
- **任务执行时间**: 优化长时间运行的任务
- **错误率**: 监控任务失败情况

## 📝 维护清单

### 定期检查

- [ ] 每周检查任务执行日志
- [ ] 每月检查队列性能
- [ ] 每季度审查任务调度时间
- [ ] 每年评估任务必要性

### 更新流程

1. 修改 `setup_celery_beat.py`
2. 运行 `--dry-run` 预览变化
3. 执行实际更新
4. 验证任务状态
5. 监控执行情况

---

*最后更新: 2024-12-25*
*维护者: Claude Code*