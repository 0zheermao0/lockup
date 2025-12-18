#!/usr/bin/env python
"""
检查提交文件数据
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskSubmissionFile, TaskParticipant

def check_submission_files():
    """检查提交文件数据"""
    task_id = 'b4989c58-f7a6-4e09-b998-09fa5ca49f75'

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🎯 任务: {task.title}")
        print(f"   发布者: {task.user.username}")
        print()

        # 检查参与者
        participants = task.participants.all()
        print(f"👥 参与者 ({participants.count()} 个):")
        for p in participants:
            print(f"   {p.participant.username}: {p.status}")
            if p.submission_text:
                print(f"     提交内容: {p.submission_text[:50]}...")

        print()

        # 检查提交文件
        submission_files = TaskSubmissionFile.objects.filter(task=task)
        print(f"📁 提交文件 ({submission_files.count()} 个):")

        if submission_files.exists():
            for file in submission_files:
                participant = file.participant if hasattr(file, 'participant') else None
                uploader_name = participant.participant.username if participant else file.uploader.username
                print(f"   文件: {file.file_name}")
                print(f"     上传者: {uploader_name}")
                print(f"     类型: {file.file_type}")
                print(f"     是否图片: {file.is_image}")
                print(f"     是否主要: {file.is_primary}")
                print(f"     URL: {file.file_url}")
                print()
        else:
            print("   没有找到提交文件")

        # 检查任务级别的提交文件
        task_files = task.submission_files.all()
        print(f"📋 任务级别文件 ({task_files.count()} 个):")
        for file in task_files:
            print(f"   文件: {file.file_name}")
            print(f"     上传者: {file.uploader.username}")
            print(f"     类型: {file.file_type}")
            print()

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_submission_files()