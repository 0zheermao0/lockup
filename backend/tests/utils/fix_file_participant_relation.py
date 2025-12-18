#!/usr/bin/env python
"""
修复文件与参与者的关联关系
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskSubmissionFile, TaskParticipant

def fix_file_participant_relation():
    """修复文件与参与者的关联关系"""
    task_id = 'b4989c58-f7a6-4e09-b998-09fa5ca49f75'

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"🔧 修复任务: {task.title}")
        print()

        # 查找未关联参与者的文件
        unlinked_files = TaskSubmissionFile.objects.filter(task=task, participant__isnull=True)

        if not unlinked_files.exists():
            print("✅ 所有文件都已正确关联参与者")
            return

        print(f"🔍 找到 {unlinked_files.count()} 个未关联的文件，开始修复...")
        print()

        fixed_count = 0
        for file in unlinked_files:
            print(f"📁 处理文件: {file.file_name}")
            print(f"   上传者: {file.uploader.username}")

            # 查找对应的参与者
            matching_participant = TaskParticipant.objects.filter(
                task=task,
                participant=file.uploader
            ).first()

            if matching_participant:
                # 关联文件到参与者
                file.participant = matching_participant
                file.save()

                print(f"   ✅ 已关联到参与者: {matching_participant.participant.username}")
                fixed_count += 1
            else:
                print(f"   ❌ 找不到对应的参与者")

            print()

        print(f"🎉 修复完成！共修复了 {fixed_count} 个文件的关联关系")
        print()

        # 验证修复结果
        print("🔍 验证修复结果:")
        participants = task.participants.all()
        for p in participants:
            participant_files = TaskSubmissionFile.objects.filter(participant=p)
            print(f"   {p.participant.username}: {participant_files.count()} 个文件")
            for file in participant_files:
                print(f"     - {file.file_name}")

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_file_participant_relation()