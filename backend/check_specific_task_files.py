#!/usr/bin/env python
"""
检查特定任务的文件关联情况
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskSubmissionFile, TaskParticipant

def check_specific_task_files():
    """检查特定任务的文件关联情况"""
    task_id = '9ffd36b9-f064-4a7c-b279-b435d58c3043'

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🎯 任务: {task.title}")
        print(f"   发布者: {task.user.username}")
        print(f"   状态: {task.status}")
        print()

        # 检查参与者
        participants = task.participants.all()
        print(f"👥 参与者 ({participants.count()} 个):")
        for p in participants:
            print(f"   {p.participant.username} (ID: {p.id}):")
            print(f"     状态: {p.status}")
            print(f"     提交内容: {p.submission_text[:50] if p.submission_text else '无'}...")

            # 检查该参与者的提交文件
            participant_files = TaskSubmissionFile.objects.filter(participant=p)
            print(f"     关联文件: {participant_files.count()} 个")
            for file in participant_files:
                print(f"       - {file.file_name}")
                print(f"         URL: {file.file_url}")
                print(f"         是图片: {file.is_image}")

            print()

        # 检查所有提交文件
        print("📁 所有提交文件:")
        submission_files = TaskSubmissionFile.objects.filter(task=task)
        for file in submission_files:
            print(f"   文件: {file.file_name}")
            print(f"     上传者: {file.uploader.username}")
            print(f"     关联参与者: {file.participant.participant.username if file.participant else '无'}")
            print(f"     URL: {file.file_url}")
            print()

        # 如果文件没有关联参与者，尝试修复
        unlinked_files = TaskSubmissionFile.objects.filter(task=task, participant__isnull=True)
        if unlinked_files.exists():
            print("⚠️  发现未关联参与者的文件，正在修复...")
            for file in unlinked_files:
                matching_participant = TaskParticipant.objects.filter(
                    task=task,
                    participant=file.uploader
                ).first()

                if matching_participant:
                    file.participant = matching_participant
                    file.save()
                    print(f"   ✅ 已关联 {file.file_name} 到 {matching_participant.participant.username}")

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")

if __name__ == '__main__':
    check_specific_task_files()