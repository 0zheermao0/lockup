#!/usr/bin/env python3
"""
测试新的带锁任务coins奖励计算规则
新规则：
- 每实际一小时奖励1coins（基础时长奖励）
- 根据难度额外奖励：easy(1), normal(2), hard(3), hell(4) coins
"""

from datetime import datetime, timedelta

def calculate_lock_task_completion_reward_test(difficulty, duration_hours):
    """模拟新的奖励计算逻辑"""
    actual_duration_hours = int(duration_hours)

    # 基础时长奖励：每实际一小时1积分
    time_reward = max(0, actual_duration_hours)

    # 难度奖励：只有满1小时才给难度奖励
    difficulty_bonus = 0
    if actual_duration_hours >= 1:
        difficulty_bonus_rewards = {
            'easy': 1,     # 简单：额外1积分
            'normal': 2,   # 普通：额外2积分
            'hard': 3,     # 困难：额外3积分
            'hell': 4      # 地狱：额外4积分
        }
        difficulty_bonus = difficulty_bonus_rewards.get(difficulty, 2)  # 默认2积分

    # 总奖励 = 时长奖励 + 难度奖励
    total_reward = time_reward + difficulty_bonus

    return total_reward, time_reward, difficulty_bonus

def test_reward_calculations():
    """测试各种场景下的奖励计算"""
    print("🧪 测试新的带锁任务coins奖励计算规则")
    print("="*60)
    print("规则说明：")
    print("- 每实际一小时奖励1coins（基础时长奖励）")
    print("- 满1小时后，根据难度额外奖励：easy(1), normal(2), hard(3), hell(4) coins")
    print("- 不满1小时不给难度奖励，只给时长奖励（0coins）")
    print()

    # 测试案例
    test_cases = [
        # (难度, 时长小时, 描述)
        ('easy', 0.5, '简单任务，30分钟'),
        ('easy', 1.0, '简单任务，1小时'),
        ('easy', 2.5, '简单任务，2.5小时'),
        ('normal', 0.8, '普通任务，48分钟'),
        ('normal', 1.0, '普通任务，1小时'),
        ('normal', 3.2, '普通任务，3.2小时'),
        ('hard', 0.3, '困难任务，18分钟'),
        ('hard', 2.0, '困难任务，2小时'),
        ('hard', 5.7, '困难任务，5.7小时'),
        ('hell', 1.0, '地狱任务，1小时'),
        ('hell', 4.0, '地狱任务，4小时'),
        ('hell', 8.3, '地狱任务，8.3小时'),
    ]

    print("📊 测试结果：")
    print("-" * 80)
    print(f"{'难度':<8} {'时长':<12} {'时长奖励':<8} {'难度奖励':<8} {'总奖励':<8} {'描述'}")
    print("-" * 80)

    for difficulty, duration_hours, description in test_cases:
        total_reward, time_reward, difficulty_bonus = calculate_lock_task_completion_reward_test(difficulty, duration_hours)

        duration_str = f"{duration_hours}h"
        print(f"{difficulty:<8} {duration_str:<12} {time_reward:<8} {difficulty_bonus:<8} {total_reward:<8} {description}")

    print("-" * 80)
    print()

    # 对比旧规则
    print("📈 与旧规则对比：")
    print("旧规则：基础奖励(easy:2, normal:5, hard:10, hell:20) + 每30分钟1积分")
    print("新规则：每小时1积分 + 难度奖励(easy:1, normal:2, hard:3, hell:4)")
    print()

    comparison_cases = [
        ('normal', 1.0),   # 普通任务1小时
        ('hard', 2.0),     # 困难任务2小时
        ('hell', 4.0),     # 地狱任务4小时
    ]

    print("对比案例：")
    print("-" * 60)
    print(f"{'难度':<8} {'时长':<10} {'旧规则':<10} {'新规则':<10} {'差异'}")
    print("-" * 60)

    for difficulty, duration_hours in comparison_cases:
        # 新规则
        new_total, new_time, new_diff = calculate_lock_task_completion_reward_test(difficulty, duration_hours)

        # 旧规则模拟
        old_base = {'easy': 2, 'normal': 5, 'hard': 10, 'hell': 20}[difficulty]
        old_duration_bonus = max(0, int(duration_hours * 60) // 30)  # 每30分钟1积分
        old_total = old_base + old_duration_bonus
        old_max = old_base * 3
        old_total = min(old_total, old_max)

        diff = new_total - old_total
        diff_str = f"+{diff}" if diff > 0 else str(diff)

        print(f"{difficulty:<8} {duration_hours}h{'':<6} {old_total:<10} {new_total:<10} {diff_str}")

    print("-" * 60)

if __name__ == "__main__":
    test_reward_calculations()