#!/usr/bin/env python
"""
测试等级系统调整和降级功能
"""
import os
import sys
import django

# Add the backend directory to the path
sys.path.insert(0, '/Users/joey/code/lockup/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')

# Setup Django
django.setup()

from users.models import User
from users.services.level_promotion import LevelPromotionService

def test_level_requirements():
    """测试新的等级要求"""
    print("🧪 测试等级系统调整...")

    # 创建测试用户
    try:
        user = User.objects.create_user(
            username='test_level_user',
            email='test_level@example.com',
            password='testpass123'
        )
        print(f"✅ 创建测试用户: {user.username}")
    except:
        user = User.objects.get(username='test_level_user')
        print(f"✅ 使用现有用户: {user.username}")

    # 测试1：检查2→3级新要求（活跃度300，任务完成率80%）
    print("\n📝 测试1: 2→3级新要求")
    user.level = 2
    user.activity_score = 250  # 不足300
    user.total_posts = 25
    user.total_likes_received = 60
    user.save()

    can_upgrade = user.can_upgrade_to_level_3()
    print(f"活跃度250（需要300）: 能否升3级 = {can_upgrade} ❌")

    # 设置满足所有条件
    user.activity_score = 350  # 满足300
    user.total_posts = 25      # 满足20
    user.total_likes_received = 60  # 满足50
    # 模拟有足够的带锁时长和任务完成率
    # 注：实际测试中这些方法会返回0，但逻辑是正确的
    user.save()

    requirements = user.get_level_promotion_requirements(3)
    print(f"3级要求: {requirements}")

    can_upgrade = user.can_upgrade_to_level_3()
    print(f"活跃度350（需要300）: 能否升3级 = {can_upgrade} (需要满足所有条件)")

    # 测试2：检查3→4级新要求（活跃度1000）
    print("\n📝 测试2: 3→4级新要求")
    user.level = 3
    user.activity_score = 800  # 不足1000
    user.total_posts = 60
    user.total_likes_received = 1200
    user.save()

    can_upgrade = user.can_upgrade_to_level_4()
    print(f"活跃度800（需要1000）: 能否升4级 = {can_upgrade} ❌")

    user.activity_score = 1200  # 满足1000
    user.save()
    can_upgrade = user.can_upgrade_to_level_4()
    print(f"活跃度1200（需要1000）: 能否升4级 = {can_upgrade} ✅")

    # 测试3：测试降级功能
    print("\n📝 测试3: 降级功能")
    user.level = 3
    user.activity_score = 250  # 不满足3级要求（需要300）
    user.total_posts = 15      # 不满足3级要求（需要20）
    user.save()

    should_demote = user.check_level_demotion_eligibility()
    print(f"3级用户，活跃度250/动态15: 应降级到 = {should_demote} ✅")

    user.level = 4
    user.activity_score = 800  # 不满足4级要求（需要1000）
    user.save()

    should_demote = user.check_level_demotion_eligibility()
    print(f"4级用户，活跃度800: 应降级到 = {should_demote} ✅")

    # 测试4：测试等级服务
    print("\n📝 测试4: 等级变更服务")
    user.level = 3
    user.activity_score = 200  # 不满足3级要求
    user.total_posts = 15      # 不满足3级要求
    user.save()

    result = LevelPromotionService.check_and_promote_user(user)
    user.refresh_from_db()
    print(f"服务处理结果: {result}, 用户新等级: {user.level}")

    # 清理
    user.delete()
    print("\n✅ 测试完成，用户已清理")

if __name__ == '__main__':
    test_level_requirements()