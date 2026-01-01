#!/bin/bash

# Celery Beat启动脚本
# 确保使用DatabaseScheduler来读取数据库中的定时任务

# 设置工作目录
cd "$(dirname "$0")/.."

# 激活虚拟环境
source venv/bin/activate

# 创建日志目录
mkdir -p logs

# 停止现有的Celery Beat进程
echo "停止现有的Celery Beat进程..."
pkill -f "celery.*beat" || true

# 等待进程完全停止
sleep 2

# 启动Celery Beat，明确指定DatabaseScheduler
echo "启动Celery Beat (使用DatabaseScheduler)..."
celery -A lockup_backend beat \
    --scheduler=django_celery_beat.schedulers:DatabaseScheduler \
    --loglevel=info \
    --logfile=logs/celery_beat.log \
    --pidfile=logs/celery_beat.pid \
    --detach

echo "Celery Beat已启动"

# 验证进程是否正在运行
sleep 2
if pgrep -f "celery.*beat" > /dev/null; then
    echo "✅ Celery Beat运行正常"
    echo "日志文件: logs/celery_beat.log"
    echo "PID文件: logs/celery_beat.pid"
else
    echo "❌ Celery Beat启动失败"
    exit 1
fi