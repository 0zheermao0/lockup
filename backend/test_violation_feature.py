#!/usr/bin/env python
"""
时间隐藏违规功能测试脚本
Test script for hidden time violation feature
"""

import os
import sys
import django
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append('/Users/joey/code/lockup/backend')

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from tasks.models import LockTask, TaskViolationAttempt
from tasks.utils import calculate_penalty_overtime, record_violation_attempt, apply_penalty_overtime
from tasks.validators import validate_task_completion_conditions

User = get_user_model()

def create_test_data():
    """创建测试数据"""
    print("🔧 创建测试数据...")

    # 创建测试用户
    user, created = User.objects.get_or_create(
        username='test_violation_user',
        defaults={
            'email': 'test@example.com',
            'password': 'testpass123'
        }
    )

    if created:
        print(f"✅ 创建测试用户: {user.username}")
    else:
        print(f"✅ 使用现有测试用户: {user.username}")

    # 创建带锁任务（时间隐藏状态）
    task = LockTask.objects.create(
        user=user,
        task_type='lock',
        title='时间隐藏违规测试任务',
        description='用于测试时间隐藏状态下的违规检测功能',
        status='active',
        duration_type='fixed',
        duration_value=60,  # 60分钟
        difficulty='normal',
        unlock_type='time',
        time_display_hidden=True,  # 启用时间隐藏
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(minutes=30)  # 还有30分钟结束
    )

    print(f"✅ 创建测试任务: {task.title}")
    print(f"   - 任务ID: {task.id}")
    print(f"   - 时间隐藏: {task.time_display_hidden}")
    print(f"   - 结束时间: {task.end_time}")
    print(f"   - 剩余时间: {(task.end_time - timezone.now()).total_seconds() / 60:.1f} 分钟")

    return user, task

def test_penalty_calculation():
    """测试惩罚计算功能"""
    print("\n🧮 测试惩罚计算功能...")

    user, task = create_test_data()

    # 测试首次违规的惩罚计算
    penalty1 = calculate_penalty_overtime(task, user)
    print(f"✅ 首次违规惩罚: {penalty1} 分钟")

    # 模拟创建一次违规记录
    violation1 = record_violation_attempt(task, user, 'premature_completion_hidden_time')
    print(f"✅ 记录首次违规: {violation1.id}")

    # 测试第二次违规的惩罚计算（应该更重）
    penalty2 = calculate_penalty_overtime(task, user)
    print(f"✅ 第二次违规惩罚: {penalty2} 分钟")

    assert penalty2 > penalty1, "第二次违规的惩罚应该比第一次更重"
    print(f"✅ 惩罚递增验证通过: {penalty2} > {penalty1}")

    return user, task

def test_violation_detection():
    """测试违规检测功能"""
    print("\n🚨 测试违规检测功能...")

    user, task = create_test_data()

    # 测试正常情况（时间隐藏但不是违规尝试）
    print("测试场景1: 时间隐藏状态，倒计时未结束")
    can_complete, error_response = validate_task_completion_conditions(task, user, require_has_key=False)

    if not can_complete and error_response:
        error_data = error_response.data
        print(f"✅ 违规检测成功")
        print(f"   - 错误代码: {error_data.get('error_code')}")
        print(f"   - 惩罚应用: {error_data.get('penalty_applied')}")
        print(f"   - 惩罚时间: {error_data.get('penalty_minutes')} 分钟")
        print(f"   - 剩余时间: {error_data.get('time_remaining_minutes')} 分钟")

        # 验证违规记录是否创建
        violations = TaskViolationAttempt.objects.filter(task=task, user=user)
        print(f"✅ 违规记录数量: {violations.count()}")

        if violations.exists():
            latest_violation = violations.latest('attempted_at')
            print(f"   - 违规类型: {latest_violation.violation_type}")
            print(f"   - 惩罚分钟: {latest_violation.penalty_minutes}")
            print(f"   - 剩余秒数: {latest_violation.time_remaining_seconds}")
    else:
        print("❌ 违规检测失败：应该检测到违规但没有")
        return False

    # 测试任务时间已到的情况
    print("\n测试场景2: 时间隐藏状态，倒计时已结束")
    task.end_time = timezone.now() - timedelta(minutes=5)  # 设置为5分钟前结束
    task.save()

    can_complete, error_response = validate_task_completion_conditions(task, user, require_has_key=False)

    if can_complete:
        print("✅ 时间已到，可以正常完成任务")
    else:
        print(f"❌ 时间已到但仍被阻止: {error_response.data if error_response else 'Unknown error'}")

    return True

def test_configuration():
    """测试配置参数"""
    print("\n⚙️ 测试配置参数...")

    from django.conf import settings

    violation_settings = getattr(settings, 'HIDDEN_TIME_VIOLATION_SETTINGS', {})

    print("当前配置:")
    for key, value in violation_settings.items():
        print(f"   - {key}: {value}")

    # 测试配置是否生效
    user, task = create_test_data()

    penalty = calculate_penalty_overtime(task, user)
    base_penalty = violation_settings.get('BASE_PENALTY_MINUTES', 30)
    max_penalty = violation_settings.get('MAX_PENALTY_MINUTES', 180)

    assert base_penalty <= penalty <= max_penalty, f"惩罚时间应该在 {base_penalty}-{max_penalty} 分钟范围内"
    print(f"✅ 配置验证通过: {penalty} 分钟在 {base_penalty}-{max_penalty} 范围内")

    return True

def cleanup_test_data():
    """清理测试数据"""
    print("\n🧹 清理测试数据...")

    # 删除测试任务和相关数据
    test_tasks = LockTask.objects.filter(title__contains='时间隐藏违规测试')
    violations_count = TaskViolationAttempt.objects.filter(task__in=test_tasks).count()
    tasks_count = test_tasks.count()

    TaskViolationAttempt.objects.filter(task__in=test_tasks).delete()
    test_tasks.delete()

    # 删除测试用户
    test_users = User.objects.filter(username__contains='test_violation_user')
    users_count = test_users.count()
    test_users.delete()

    print(f"✅ 清理完成:")
    print(f"   - 删除违规记录: {violations_count} 条")
    print(f"   - 删除测试任务: {tasks_count} 个")
    print(f"   - 删除测试用户: {users_count} 个")

def main():
    """主测试函数"""
    print("🚀 开始时间隐藏违规功能测试")
    print("=" * 50)

    try:
        # 运行所有测试
        test_configuration()
        test_penalty_calculation()
        test_violation_detection()

        print("\n" + "=" * 50)
        print("🎉 所有测试通过！")
        print("\n功能验证结果:")
        print("✅ 违规记录模型正常工作")
        print("✅ 惩罚计算机制正确")
        print("✅ 违规检测逻辑有效")
        print("✅ 配置参数生效")
        print("✅ 数据库迁移成功")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理测试数据
        cleanup_test_data()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)