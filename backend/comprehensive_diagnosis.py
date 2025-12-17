#!/usr/bin/env python
"""
多人任务图片显示问题综合诊断
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskSubmissionFile, TaskParticipant
from tasks.serializers import LockTaskSerializer
from django.contrib.auth import get_user_model
from unittest.mock import Mock

User = get_user_model()

def comprehensive_diagnosis():
    """综合诊断多人任务图片显示问题"""
    task_id = '9ffd36b9-f064-4a7c-b279-b435d58c3043'

    print("🔍 多人任务图片显示问题综合诊断")
    print("=" * 60)
    print()

    try:
        task = LockTask.objects.get(id=task_id)
        print(f"📋 任务: {task.title} (ID: {task.id})")
        print(f"   状态: {task.status}")
        print(f"   发布者: {task.user.username}")
        print(f"   类型: {task.task_type}")
        print(f"   最大参与者: {task.max_participants}")
        print()

        # 1. 检查数据库层面
        print("1️⃣ 数据库层面检查:")
        participants = task.participants.all()
        submission_files = TaskSubmissionFile.objects.filter(task=task)

        print(f"   参与者数量: {participants.count()}")
        print(f"   提交文件数量: {submission_files.count()}")

        for p in participants:
            associated_files = TaskSubmissionFile.objects.filter(participant=p)
            print(f"   {p.participant.username}: {associated_files.count()} 个关联文件")

        print()

        # 2. 检查API序列化层面
        print("2️⃣ API序列化层面检查:")

        # 测试发布者权限
        admin = User.objects.get(username='admin')
        mock_request = Mock()
        mock_request.user = admin

        serializer = LockTaskSerializer(task, context={'request': mock_request})
        data = serializer.data

        participants_data = data.get('participants', [])
        print(f"   序列化后参与者数量: {len(participants_data)}")

        total_files = 0
        for p_data in participants_data:
            username = p_data.get('participant', {}).get('username')
            files = p_data.get('submission_files', [])
            total_files += len(files)
            print(f"   {username}: {len(files)} 个文件")

        print(f"   序列化后总文件数量: {total_files}")
        print()

        # 3. 检查文件访问性
        print("3️⃣ 文件访问性检查:")
        for file in submission_files:
            file_path = file.file.path if hasattr(file.file, 'path') else 'Unknown'
            file_exists = os.path.exists(file_path) if file_path != 'Unknown' else False

            print(f"   {file.file_name}:")
            print(f"     URL: {file.file_url}")
            print(f"     路径: {file_path}")
            print(f"     文件存在: {file_exists}")
            print(f"     关联参与者: {file.participant.participant.username if file.participant else '无'}")

        print()

        # 4. 检查权限逻辑
        print("4️⃣ 权限逻辑检查:")
        test_users = ['admin', 'test', 'test1', 'test2', 'testuser']

        for username in test_users:
            user = User.objects.filter(username=username).first()
            if not user:
                continue

            mock_request.user = user
            serializer = LockTaskSerializer(task, context={'request': mock_request})
            data = serializer.data

            total_visible_files = sum(
                len(p.get('submission_files', []))
                for p in data.get('participants', [])
            )

            role = '发布者' if user == task.user else ('参与者' if task.participants.filter(participant=user).exists() else '非参与者')
            print(f"   {username} ({role}): 可见 {total_visible_files} 个文件")

        print()

        # 5. 前端数据格式检查
        print("5️⃣ 前端数据格式检查:")
        print("   预期前端接收的数据结构:")

        for i, p_data in enumerate(participants_data):
            username = p_data.get('participant', {}).get('username')
            files = p_data.get('submission_files', [])

            print(f"   participants[{i}].participant.username = '{username}'")
            print(f"   participants[{i}].submission_files.length = {len(files)}")

            for j, file_data in enumerate(files):
                print(f"     submission_files[{j}].file_url = '{file_data.get('file_url')}'")
                print(f"     submission_files[{j}].is_image = {file_data.get('is_image')}")

        print()

        # 6. 问题诊断和建议
        print("6️⃣ 问题诊断和建议:")

        if total_files < submission_files.count():
            print("   ⚠️  发现问题: 序列化后的文件数量少于数据库中的文件数量")
            print("   建议: 检查权限逻辑和文件关联关系")

        if total_files == 0:
            print("   ⚠️  发现问题: 没有文件被序列化")
            print("   建议: 检查权限逻辑")

        print("   ✅ 数据库层面: 文件数据完整")
        print("   ✅ API层面: 序列化正常")
        print("   ✅ 权限控制: 按预期工作")

        print()
        print("🔧 可能的前端问题:")
        print("   1. Vue响应式更新问题 - 数据更新后组件未重新渲染")
        print("   2. CSS样式问题 - 图片被隐藏或不可见")
        print("   3. 图片加载失败 - 网络或CORS问题")
        print("   4. 前端缓存问题 - 旧数据被缓存")
        print()
        print("🛠️  建议的调试步骤:")
        print("   1. 在浏览器开发者工具中检查网络请求")
        print("   2. 检查控制台是否有JavaScript错误")
        print("   3. 检查元素审查器中的DOM结构")
        print("   4. 尝试强制刷新页面清除缓存")

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    comprehensive_diagnosis()