#!/usr/bin/env python
"""
检查当前任务和提交文件状态
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskSubmissionFile, TaskParticipant

def check_current_tasks():
    """检查当前任务和提交文件状态"""
    print("🎯 检查当前任务和提交文件状态")
    print("=" * 50)
    print()

    # 查找有提交文件的任务
    tasks_with_files = LockTask.objects.filter(
        task_type='board',
        submission_files__isnull=False
    ).distinct()

    print(f"📋 找到 {tasks_with_files.count()} 个有提交文件的任务:")
    print()

    for task in tasks_with_files:
        print(f"📋 任务: {task.title} (ID: {task.id})")
        print(f"   状态: {task.status}")
        print(f"   发布者: {task.user.username}")
        print(f"   URL: http://localhost:5174/tasks/{task.id}")

        # 检查参与者
        participants = task.participants.all()
        print(f"   参与者: {participants.count()}/{task.max_participants}")
        for p in participants:
            print(f"     - {p.participant.username}: {p.status}")

        # 检查提交文件
        submission_files = task.submission_files.all()
        print(f"   提交文件: {submission_files.count()} 个")
        for file in submission_files:
            participant_name = "未知"
            if hasattr(file, 'participant') and file.participant:
                participant_name = file.participant.participant.username
            elif file.uploader:
                participant_name = f"{file.uploader.username} (上传者)"

            print(f"     - {file.file_name}")
            print(f"       上传者: {participant_name}")
            print(f"       类型: {file.file_type}")
            print(f"       是图片: {file.is_image}")
            print(f"       URL: {file.file_url}")

        print()
        print("-" * 50)
        print()

    # 如果没有找到，查找所有任务板任务
    if tasks_with_files.count() == 0:
        print("没有找到有提交文件的任务，查看所有任务板任务:")
        board_tasks = LockTask.objects.filter(task_type='board').order_by('-created_at')[:5]

        for task in board_tasks:
            print(f"📋 {task.title} (ID: {task.id})")
            print(f"   状态: {task.status}")
            print(f"   参与者: {task.participants.count()}")
            print(f"   提交文件: {task.submission_files.count()}")
            print()

if __name__ == '__main__':
    check_current_tasks()