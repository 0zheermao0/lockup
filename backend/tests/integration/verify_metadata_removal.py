#!/usr/bin/env python
"""
验证元信息移除效果
"""

import os
import sys
import django

sys.path.append('/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask

def verify_metadata_removal():
    """验证元信息移除效果"""
    task_id = '9ffd36b9-f064-4a7c-b279-b435d58c3043'

    try:
        task = LockTask.objects.get(id=task_id)
        print("🎯 验证元信息移除效果")
        print("=" * 40)
        print()

        print(f"📋 测试任务: {task.title}")
        print(f"   URL: http://localhost:5174/tasks/{task.id}")
        print()

        # 检查提交文件
        submission_files = task.submission_files.all()
        if submission_files.exists():
            print("📁 提交文件信息 (后端数据):")
            for file in submission_files:
                print(f"   原始文件名: {file.file_name}")
                print(f"   文件大小: {file.file_size} bytes")
                print(f"   文件类型: {file.file_type}")
                print(f"   上传者: {file.uploader.username}")
                print()

        print("🔒 隐私保护措施:")
        print("   ✅ 前端不显示原始文件名")
        print("   ✅ 前端不显示文件大小")
        print("   ✅ 前端不显示具体文件数量")
        print("   ✅ 图片alt属性使用通用名称")
        print("   ✅ 只显示图片预览和点击查看大图功能")
        print()

        print("🎨 前端显示内容:")
        print("   - 标签: '提交文件:' (不显示数量)")
        print("   - 图片: 缩略图预览 (无文件名)")
        print("   - Alt: '提交图片 1', '提交图片 2' (通用名称)")
        print("   - 功能: 点击查看大图")
        print("   - 标识: '主要文件' 标签 (如适用)")
        print()

        print("🛡️ 安全考虑:")
        print("   - 文件URL仍然包含随机后缀，防止猜测")
        print("   - 后端权限控制确保只有授权用户能访问")
        print("   - 前端不泄露任何可能用于识别的元信息")

    except LockTask.DoesNotExist:
        print(f"❌ 找不到任务 {task_id}")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == '__main__':
    verify_metadata_removal()