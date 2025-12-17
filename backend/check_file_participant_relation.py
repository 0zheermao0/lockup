#!/usr/bin/env python
"""
检查文件与参与者的关联关系
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskSubmissionFile, TaskParticipant

def check_file_participant_relation():
    """检查文件与参与者的关联关系"""
    task_id = 'b4989c58-f7a6-4e09-b998-09fa5ca49f75'

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🎯 任务: {task.title}")
        print()

        # 检查所有参与者
        participants = task.participants.all()
        print(f"👥 参与者详情:")
        for p in participants:
            print(f"   {p.participant.username} (ID: {p.id}):")
            print(f"     状态: {p.status}")
            print(f"     提交内容: {p.submission_text[:50] if p.submission_text else '无'}...")

            # 检查该参与者的提交文件
            participant_files = TaskSubmissionFile.objects.filter(participant=p)
            print(f"     关联文件: {participant_files.count()} 个")
            for file in participant_files:
                print(f"       - {file.file_name} (上传者: {file.uploader.username})")

            print()

        # 检查所有提交文件
        print("📁 所有提交文件:")
        submission_files = TaskSubmissionFile.objects.filter(task=task)
        for file in submission_files:
            print(f"   文件: {file.file_name}")
            print(f"     上传者: {file.uploader.username}")
            print(f"     关联参与者: {file.participant.participant.username if file.participant else '无'}")
            print(f"     是否图片: {file.is_image}")
            print()

        # 检查是否有文件没有关联参与者
        unlinked_files = TaskSubmissionFile.objects.filter(task=task, participant__isnull=True)
        if unlinked_files.exists():
            print("⚠️  发现未关联参与者的文件:")
            for file in unlinked_files:
                print(f"   - {file.file_name} (上传者: {file.uploader.username})")

                # 尝试找到对应的参与者
                matching_participant = TaskParticipant.objects.filter(
                    task=task,
                    participant=file.uploader
                ).first()

                if matching_participant:
                    print(f"     建议关联到参与者: {matching_participant.participant.username}")

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_file_participant_relation()