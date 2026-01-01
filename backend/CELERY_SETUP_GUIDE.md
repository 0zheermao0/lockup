# Celery Beat 统一设置指南

本文档介绍如何使用统一的 `setup_celery_beat` 命令来初始化和管理所有系统定时任务。

## 📋 概述

`setup_celery_beat` 命令现在可以一次性设置所有系统需要的定时任务，包括：

### 🕐 定时任务清单

| 任务名称 | 执行频率 | 队列 | 功能描述 |
|---------|---------|------|----------|
| **process-hourly-rewards** | 每小时 | rewards | 处理活跃带锁任务的小时奖励 |
| **auto-freeze-strict-mode-tasks** | 每日 4:15 AM (Asia/Shanghai) | default | 自动冻结24小时内无打卡的严格模式任务 |
| **process-level-promotions** | 每周三 4:30 AM (Asia/Shanghai) | default | 批量处理用户等级晋升 |
| **process-activity-decay** | 每日 4:45 AM (Asia/Shanghai) | activity | 基于斐波那契数列的活跃度衰减处理 |
| **process-checkin-voting-results** | 每日 4:00 AM (Asia/Shanghai) | default | 处理过期的打卡投票会话 |
| **process-pinning-queue** | 每分钟 | default | 处理用户置顶队列，移除过期用户，激活等待用户 |
| **pinning-health-check** | 每5分钟 | default | 监控置顶系统健康状态并检测问题 |
| **process-deadline-reminders-8h** | 每30分钟 | default | 处理8小时截止提醒通知 |
| **schedule-pending-events** | 每分钟 | events | 调度待处理的事件系统事件 |
| **execute-pending-events** | 每小时 | events | 执行待处理的事件系统事件 |
| **process-expired-effects** | 每5分钟 | events | 处理过期的事件效果 |
| **event-system-health-check** | 每5分钟 | events | 事件系统健康状态检查 |

## 📋 队列说明

| 队列名称 | 用途 | 特点 | 默认并发数 |
|---------|------|------|-----------|
| **default** | 默认队列，处理常规任务 | 通用任务处理 | 1 |
| **rewards** | 奖励处理队列 | 高频率，涉及积分发放 | 1 |
| **activity** | 活跃度处理队列 | 低频率，用户活跃度计算 | 1 |
| **events** | 事件处理队列 | 高频率，实时事件处理 | 1 |
| **settlements** | 结算处理队列 | 财务操作，要求高可靠性 | 1 |
| **voting** | 投票处理队列 | 社区操作，投票结果处理 | 1 |

### 队列任务分配

- **rewards**: `process_hourly_rewards`
- **activity**: `process_activity_decay`
- **events**: `process_pinning_queue`
- **settlements**: `auto_settle_expired_board_task`, `process_expired_board_tasks`
- **voting**: `process_checkin_voting_results`
- **default**: 其他所有任务

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

events 队列:
├── schedule-pending-events (事件调度)
├── execute-pending-events (事件执行)
├── process-expired-effects (效果处理)
└── event-system-health-check (事件系统监控)

default 队列:
├── auto-freeze-strict-mode-tasks
├── process-level-promotions
├── process-checkin-voting-results
├── process-pinning-queue
├── pinning-health-check
└── process-deadline-reminders-8h
```

### 时间安排设计

```
每日时间线 (Asia/Shanghai):
04:00 - 打卡投票结果处理
04:15 - 自动冻结严格模式任务
04:30 - 用户等级晋升 (仅周三)
04:45 - 活跃度衰减处理

高频任务:
每分钟 - 置顶队列处理、事件调度
每5分钟 - 置顶系统健康检查、事件系统健康检查、过期效果处理
每30分钟 - 截止提醒处理
每小时 - 小时奖励处理、事件执行
```

## 🔧 开发者使用指南

### 新项目部署

```bash
# 1. 初始化数据库迁移
python manage.py migrate

# 2. 设置所有定时任务
python manage.py setup_celery_beat

# 3. 启动 Celery Beat 调度器 (必须指定DatabaseScheduler)
celery -A lockup_backend beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# 4. 启动 Celery Worker (所有队列)
celery -A lockup_backend worker -l info -Q default,rewards,activity,events,settlements,voting -c 1

# 5. 使用脚本启动 (推荐)
./scripts/celery_start_all.sh                    # 启动所有组件
./scripts/celery_workers_multi.sh -d             # 启动多队列专用workers (后台运行)

# 6. 或者手动按队列启动多个 Worker
celery -A lockup_backend worker -Q rewards -c 2 -l info &       # 奖励处理队列
celery -A lockup_backend worker -Q activity -c 1 -l info &      # 活跃度处理队列
celery -A lockup_backend worker -Q events -c 2 -l info &        # 事件处理队列 (高频)
celery -A lockup_backend worker -Q settlements -c 1 -l info &   # 结算处理队列 (可靠性)
celery -A lockup_backend worker -Q voting -c 1 -l info &        # 投票处理队列
celery -A lockup_backend worker -Q default -c 4 -l info &       # 默认队列
```

### 脚本使用方法

#### 🚀 一键启动所有组件
```bash
# 启动所有组件 (worker + beat + flower)
./scripts/celery_start_all.sh

# 后台运行所有组件
./scripts/celery_start_all.sh -d

# 仅启动worker
./scripts/celery_start_all.sh worker

# 开发模式 (更详细日志)
./scripts/celery_start_all.sh --dev
```

#### ⚡ 多队列专用Workers
```bash
# 启动多队列专用workers (推荐生产环境)
./scripts/celery_workers_multi.sh -d

# 检查worker状态
./scripts/celery_workers_multi.sh --status

# 停止所有workers
./scripts/celery_workers_multi.sh --stop

# 重启所有workers
./scripts/celery_workers_multi.sh --restart
```

#### 📊 单独启动组件
```bash
# 仅启动Beat调度器
./scripts/celery_beat.sh

# 仅启动Worker (所有队列)
./scripts/celery_worker.sh

# 仅启动Flower监控
./scripts/celery_flower.sh
```

### 更新现有部署

```bash
# 1. 更新定时任务配置
python manage.py setup_celery_beat

# 2. 重启 Celery 服务
./scripts/celery_workers_multi.sh --restart
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
celery -A lockup_backend beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# 查看 Worker 日志
celery -A lockup_backend worker -l info

# 查看特定队列的 Worker 日志
celery -A lockup_backend worker -Q rewards -l info
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
   celery -A lockup_backend inspect active

   # 重启特定队列的 Worker
   celery -A lockup_backend worker -Q rewards --purge
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
celery -A lockup_backend worker -Q rewards -c 2 -l info    # 奖励队列：低并发
celery -A lockup_backend worker -Q activity -c 1 -l info   # 活跃度队列：单线程
celery -A lockup_backend worker -Q events -c 1 -l info     # 事件队列：单线程
celery -A lockup_backend worker -Q default -c 4 -l info    # 默认队列：高并发
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