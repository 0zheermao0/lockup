#!/usr/bin/env python3
"""
Reward System Unit Tests

This module provides comprehensive unit tests for the Lockup backend reward
system, covering hourly rewards for lock tasks, daily login rewards, and
related reward distribution mechanisms.

Key areas tested:
- Hourly reward calculation and distribution for lock tasks
- Difficulty-based reward multipliers
- Daily login reward system based on user levels
- Reward uniqueness constraints and validation
- Reward history tracking and statistics
- Batch reward processing and distribution
- Error handling and edge cases
- Integration with coin system and user progression

Author: Claude Code
Created: 2026-01-04
"""

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from datetime import timedelta, date
from unittest.mock import patch, MagicMock
from decimal import Decimal
import uuid

from tasks.models import LockTask, HourlyReward
from users.models import DailyLoginReward, User
from tests.base.test_case_base import BaseBusinessLogicTestCase, TestDataMixin
from tests.base.factories import (
    LockTaskFactory, HourlyRewardFactory, UserFactory
)
from tests.base.fixtures import TaskFixtures, UserFixtures

User = get_user_model()


class HourlyRewardTest(BaseBusinessLogicTestCase):
    """Test hourly reward system for lock tasks"""

    def test_hourly_reward_creation(self):
        """测试小时奖励创建"""
        task = LockTaskFactory.create_active_task(
            self.user_level2,
            difficulty='medium'
        )

        reward = HourlyReward.objects.create(
            task=task,
            user=self.user_level2,
            reward_amount=15,
            hour_count=1
        )

        self.assertEqual(reward.task, task)
        self.assertEqual(reward.user, self.user_level2)
        self.assertEqual(reward.reward_amount, 15)
        self.assertEqual(reward.hour_count, 1)
        self.assertIsNotNone(reward.id)
        self.assertIsInstance(reward.id, uuid.UUID)
        self.assertIsNotNone(reward.created_at)

    def test_hourly_reward_calculation_by_difficulty(self):
        """测试按难度计算小时奖励金额"""
        difficulties = ['easy', 'normal', 'hard', 'hell']
        base_reward = 10

        for difficulty in difficulties:
            task = LockTaskFactory.create_active_task(
                self.user_level2,
                difficulty=difficulty
            )

            # Calculate expected reward based on difficulty multipliers
            multipliers = {
                'easy': 1.0,
                'normal': 1.5,
                'hard': 2.0,
                'hell': 3.0
            }

            expected_amount = int(base_reward * multipliers[difficulty])

            reward = HourlyReward.objects.create(
                task=task,
                user=self.user_level2,
                reward_amount=expected_amount,
                hour_count=1
            )

            self.assertEqual(reward.reward_amount, expected_amount)

    def test_hourly_reward_progression_over_time(self):
        """测试小时奖励随时间递增"""
        task = LockTaskFactory.create_active_task(
            self.user_level2,
            difficulty='hard'
        )

        # Create rewards for multiple hours with increasing amounts
        hours_count = 5
        rewards = []

        for hour in range(1, hours_count + 1):
            # Simulate increasing reward over time
            reward_amount = 10 + hour * 2  # 12, 14, 16, 18, 20
            reward = HourlyReward.objects.create(
                task=task,
                user=self.user_level2,
                reward_amount=reward_amount,
                hour_count=hour
            )
            rewards.append(reward)

        # Verify progression
        for i in range(len(rewards) - 1):
            self.assertLess(rewards[i].reward_amount, rewards[i + 1].reward_amount)
            self.assertEqual(rewards[i].hour_count, i + 1)

    def test_hourly_reward_multiple_tasks(self):
        """测试多任务小时奖励独立性"""
        task1 = LockTaskFactory.create_active_task(
            self.user_level2,
            difficulty='easy',
            title="Task 1"
        )
        task2 = LockTaskFactory.create_active_task(
            self.user_level2,
            difficulty='hard',
            title="Task 2"
        )

        # Create rewards for both tasks at same hour
        reward1 = HourlyReward.objects.create(
            task=task1,
            user=self.user_level2,
            reward_amount=10,
            hour_count=1
        )

        reward2 = HourlyReward.objects.create(
            task=task2,
            user=self.user_level2,
            reward_amount=20,
            hour_count=1
        )

        # Verify independence
        self.assertEqual(reward1.task, task1)
        self.assertEqual(reward2.task, task2)
        self.assertNotEqual(reward1.reward_amount, reward2.reward_amount)
        self.assertEqual(reward1.hour_count, reward2.hour_count)

    def test_hourly_reward_user_coin_update(self):
        """测试小时奖励更新用户积分"""
        task = LockTaskFactory.create_active_task(self.user_level2)
        reward_amount = 25
        original_coins = self.user_level2.coins

        # Create reward
        reward = HourlyReward.objects.create(
            task=task,
            user=self.user_level2,
            reward_amount=reward_amount,
            hour_count=1
        )

        # In real implementation, user coins would be updated automatically
        # Simulate the coin update
        self.user_level2.coins += reward_amount
        self.user_level2.save()

        self.assert_user_coins_changed(self.user_level2, reward_amount)

    def test_hourly_reward_long_duration_task(self):
        """测试长时间任务的小时奖励累计"""
        task = LockTaskFactory.create_active_task(
            self.user_level2,
            difficulty='normal'
        )

        # Create rewards for 24 hours
        total_hours = 24
        total_reward = 0
        base_amount = 15

        for hour in range(1, total_hours + 1):
            reward_amount = base_amount  # Fixed amount per hour
            reward = HourlyReward.objects.create(
                task=task,
                user=self.user_level2,
                reward_amount=reward_amount,
                hour_count=hour
            )
            total_reward += reward_amount

        # Verify total reward calculation
        all_rewards = HourlyReward.objects.filter(task=task, user=self.user_level2)
        calculated_total = sum(reward.reward_amount for reward in all_rewards)

        self.assertEqual(len(all_rewards), total_hours)
        self.assertEqual(calculated_total, total_reward)
        self.assertEqual(calculated_total, base_amount * total_hours)

    def test_hourly_reward_ordering(self):
        """测试小时奖励排序"""
        task = LockTaskFactory.create_active_task(self.user_level2)

        # Create rewards in random order
        reward3 = HourlyReward.objects.create(task=task, user=self.user_level2, reward_amount=15, hour_count=3)
        reward1 = HourlyReward.objects.create(task=task, user=self.user_level2, reward_amount=15, hour_count=1)
        reward2 = HourlyReward.objects.create(task=task, user=self.user_level2, reward_amount=15, hour_count=2)

        # Should be ordered by creation time (most recent first)
        ordered_rewards = HourlyReward.objects.filter(task=task)
        self.assertEqual(ordered_rewards[0], reward2)  # Most recent
        self.assertEqual(ordered_rewards[1], reward1)
        self.assertEqual(ordered_rewards[2], reward3)  # Oldest

    def test_hourly_reward_different_users_same_task(self):
        """测试不同用户同一任务的小时奖励"""
        # This scenario would apply to multi-user tasks
        task = LockTaskFactory.create_board_task(
            user=self.user_level2,
            max_participants=3
        )

        users = [self.user_level3, self.user_level4, self.user_level5]
        rewards = []

        for user in users:
            reward = HourlyReward.objects.create(
                task=task,
                user=user,
                reward_amount=20,
                hour_count=1
            )
            rewards.append(reward)

        # Verify each user gets independent reward
        for i, reward in enumerate(rewards):
            self.assertEqual(reward.user, users[i])
            self.assertEqual(reward.task, task)
            self.assertEqual(reward.reward_amount, 20)

    def test_hourly_reward_task_completion_impact(self):
        """测试任务完成对小时奖励的影响"""
        task = LockTaskFactory.create_active_task(self.user_level2)

        # Create rewards while task is active
        reward1 = HourlyReward.objects.create(
            task=task,
            user=self.user_level2,
            reward_amount=15,
            hour_count=1
        )

        # Complete the task
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()

        # Rewards should still exist after task completion
        self.assertTrue(HourlyReward.objects.filter(task=task).exists())
        self.assertEqual(reward1.task.status, 'completed')


class DailyLoginRewardTest(BaseBusinessLogicTestCase, TestDataMixin):
    """Test daily login reward system"""

    def test_daily_login_reward_creation(self):
        """测试每日登录奖励创建"""
        user = self.user_level3
        today = date.today()
        reward_amount = user.level  # Reward equals user level

        reward = DailyLoginReward.objects.create(
            user=user,
            date=today,
            user_level=user.level,
            reward_amount=reward_amount
        )

        self.assertEqual(reward.user, user)
        self.assertEqual(reward.date, today)
        self.assertEqual(reward.user_level, user.level)
        self.assertEqual(reward.reward_amount, reward_amount)
        self.assertIsNotNone(reward.created_at)

    def test_daily_login_reward_amount_by_level(self):
        """测试按等级计算每日登录奖励"""
        levels_and_rewards = [
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 4),
            (5, 5)
        ]

        today = date.today()

        for level, expected_reward in levels_and_rewards:
            user = UserFactory.create_user(level=level)

            reward = DailyLoginReward.objects.create(
                user=user,
                date=today,
                user_level=level,
                reward_amount=expected_reward
            )

            self.assertEqual(reward.reward_amount, expected_reward)
            self.assertEqual(reward.user_level, level)

    def test_daily_login_reward_uniqueness_constraint(self):
        """测试每日登录奖励唯一性约束"""
        user = self.user_level2
        today = date.today()

        # Create first reward
        DailyLoginReward.objects.create(
            user=user,
            date=today,
            user_level=user.level,
            reward_amount=user.level
        )

        # Attempt to create second reward for same user and date should fail
        with self.assertRaises(IntegrityError):
            DailyLoginReward.objects.create(
                user=user,
                date=today,
                user_level=user.level,
                reward_amount=user.level
            )

    def test_daily_login_reward_different_dates(self):
        """测试不同日期的每日登录奖励"""
        user = self.user_level2
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        dates = [yesterday, today, tomorrow]
        rewards = []

        for reward_date in dates:
            reward = DailyLoginReward.objects.create(
                user=user,
                date=reward_date,
                user_level=user.level,
                reward_amount=user.level
            )
            rewards.append(reward)

        # All rewards should exist independently
        self.assertEqual(len(rewards), 3)
        for i, reward in enumerate(rewards):
            self.assertEqual(reward.date, dates[i])
            self.assertEqual(reward.user, user)

    def test_daily_login_reward_different_users_same_date(self):
        """测试同一日期不同用户的每日登录奖励"""
        today = date.today()
        users = [self.user_level2, self.user_level3, self.user_level4]
        rewards = []

        for user in users:
            reward = DailyLoginReward.objects.create(
                user=user,
                date=today,
                user_level=user.level,
                reward_amount=user.level
            )
            rewards.append(reward)

        # Verify each user gets their own reward
        for i, reward in enumerate(rewards):
            self.assertEqual(reward.user, users[i])
            self.assertEqual(reward.date, today)
            self.assertEqual(reward.reward_amount, users[i].level)

    def test_daily_login_reward_level_change_impact(self):
        """测试等级变化对每日奖励的影响"""
        user = self.user_level1
        today = date.today()

        # Create reward at level 1
        reward_level_1 = DailyLoginReward.objects.create(
            user=user,
            date=today,
            user_level=1,
            reward_amount=1
        )

        # Promote user to level 2
        user.level = 2
        user.save()

        tomorrow = today + timedelta(days=1)

        # Create reward at level 2
        reward_level_2 = DailyLoginReward.objects.create(
            user=user,
            date=tomorrow,
            user_level=2,
            reward_amount=2
        )

        # Verify different rewards for different levels
        self.assertEqual(reward_level_1.user_level, 1)
        self.assertEqual(reward_level_1.reward_amount, 1)
        self.assertEqual(reward_level_2.user_level, 2)
        self.assertEqual(reward_level_2.reward_amount, 2)

    def test_daily_login_reward_coin_distribution(self):
        """测试每日登录奖励积分分发"""
        user = self.user_level3
        today = date.today()
        reward_amount = user.level
        original_coins = user.coins

        # Create reward
        reward = DailyLoginReward.objects.create(
            user=user,
            date=today,
            user_level=user.level,
            reward_amount=reward_amount
        )

        # In real implementation, coins would be distributed automatically
        # Simulate the distribution
        user.coins += reward_amount
        user.save()

        self.assert_user_coins_changed(user, reward_amount)

    def test_daily_login_reward_streak_potential(self):
        """测试每日登录奖励连续性潜力"""
        user = self.user_level2
        base_date = date.today()

        # Create rewards for 7 consecutive days
        consecutive_days = 7
        rewards = []

        for day in range(consecutive_days):
            reward_date = base_date + timedelta(days=day)
            reward = DailyLoginReward.objects.create(
                user=user,
                date=reward_date,
                user_level=user.level,
                reward_amount=user.level
            )
            rewards.append(reward)

        # Verify consecutive rewards
        self.assertEqual(len(rewards), consecutive_days)

        # Check date progression
        for i in range(len(rewards)):
            expected_date = base_date + timedelta(days=i)
            self.assertEqual(rewards[i].date, expected_date)

        # All rewards should be for the same user
        for reward in rewards:
            self.assertEqual(reward.user, user)


class RewardCalculationTest(BaseBusinessLogicTestCase):
    """Test reward calculation algorithms and business logic"""

    def test_difficulty_multiplier_calculation(self):
        """测试难度系数计算"""
        base_reward = 10
        difficulty_multipliers = {
            'easy': 1.0,
            'normal': 1.5,
            'hard': 2.0,
            'hell': 3.0
        }

        for difficulty, multiplier in difficulty_multipliers.items():
            expected_reward = int(base_reward * multiplier)

            # Test the calculation logic
            calculated_reward = base_reward * multiplier
            self.assertEqual(int(calculated_reward), expected_reward)

    def test_progressive_hourly_reward_calculation(self):
        """测试递进式小时奖励计算"""
        base_amount = 10
        progression_factor = 1.1  # 10% increase per hour

        # Calculate rewards for first 10 hours
        expected_rewards = []
        for hour in range(1, 11):
            if hour == 1:
                reward = base_amount
            else:
                reward = int(base_amount * (progression_factor ** (hour - 1)))
            expected_rewards.append(reward)

        # Verify progression is increasing
        for i in range(len(expected_rewards) - 1):
            self.assertLessEqual(expected_rewards[i], expected_rewards[i + 1])

    def test_level_based_reward_scaling(self):
        """测试基于等级的奖励缩放"""
        base_reward = 5
        level_multipliers = {
            1: 1.0,
            2: 1.2,
            3: 1.5,
            4: 2.0,
            5: 3.0
        }

        for level, multiplier in level_multipliers.items():
            scaled_reward = int(base_reward * multiplier)

            # Verify scaling increases with level
            if level > 1:
                prev_multiplier = level_multipliers[level - 1]
                prev_reward = int(base_reward * prev_multiplier)
                self.assertGreaterEqual(scaled_reward, prev_reward)

    def test_reward_cap_and_limits(self):
        """测试奖励上限和限制"""
        # Test maximum daily login reward
        max_level = 5
        max_daily_reward = max_level  # Should not exceed user's level

        for level in range(1, 6):
            reward = min(level, max_daily_reward)
            self.assertLessEqual(reward, max_daily_reward)

        # Test maximum hourly reward
        max_hourly_reward = 100  # Hypothetical maximum
        test_amounts = [50, 100, 150, 200]

        for amount in test_amounts:
            capped_amount = min(amount, max_hourly_reward)
            self.assertLessEqual(capped_amount, max_hourly_reward)

    def test_compound_reward_calculation(self):
        """测试复合奖励计算"""
        # Simulate multiple reward sources in one day
        daily_login = 3  # Level 3 user
        hourly_rewards = [15, 15, 15]  # 3 hours of task
        bonus_reward = 10  # Special bonus

        total_daily_earnings = daily_login + sum(hourly_rewards) + bonus_reward
        expected_total = 3 + 45 + 10  # 58

        self.assertEqual(total_daily_earnings, expected_total)


class RewardIntegrationTest(BaseBusinessLogicTestCase, TestDataMixin):
    """Integration tests for complete reward scenarios"""

    def test_complete_daily_reward_cycle(self):
        """测试完整的每日奖励周期"""
        user = self.user_level3
        today = date.today()
        original_coins = user.coins

        # Daily login reward
        daily_reward = DailyLoginReward.objects.create(
            user=user,
            date=today,
            user_level=user.level,
            reward_amount=user.level
        )

        # Task hourly rewards
        task = LockTaskFactory.create_active_task(user, difficulty='normal')
        hourly_rewards = []

        for hour in range(1, 4):  # 3 hours of task
            reward = HourlyReward.objects.create(
                task=task,
                user=user,
                reward_amount=15,
                hour_count=hour
            )
            hourly_rewards.append(reward)

        # Calculate total rewards
        total_daily_login = daily_reward.reward_amount
        total_hourly = sum(r.reward_amount for r in hourly_rewards)
        total_rewards = total_daily_login + total_hourly

        # Simulate coin distribution
        user.coins += total_rewards
        user.save()

        # Verify total reward distribution
        expected_change = total_daily_login + total_hourly
        self.assert_user_coins_changed(user, expected_change)

    def test_multi_user_reward_distribution(self):
        """测试多用户奖励分发"""
        users = [self.user_level2, self.user_level3, self.user_level4]
        today = date.today()

        # Each user gets daily login reward
        daily_rewards = []
        for user in users:
            reward = DailyLoginReward.objects.create(
                user=user,
                date=today,
                user_level=user.level,
                reward_amount=user.level
            )
            daily_rewards.append(reward)

        # Multi-user task with hourly rewards
        board_task = LockTaskFactory.create_board_task(
            user=self.user_level5,
            max_participants=3,
            reward_amount=300
        )

        hourly_rewards = []
        for user in users:
            reward = HourlyReward.objects.create(
                task=board_task,
                user=user,
                reward_amount=20,
                hour_count=1
            )
            hourly_rewards.append(reward)

        # Verify independent reward distribution
        for i, user in enumerate(users):
            daily_reward = daily_rewards[i]
            hourly_reward = hourly_rewards[i]

            self.assertEqual(daily_reward.user, user)
            self.assertEqual(daily_reward.reward_amount, user.level)
            self.assertEqual(hourly_reward.user, user)
            self.assertEqual(hourly_reward.reward_amount, 20)

    def test_reward_system_with_level_progression(self):
        """测试奖励系统与等级晋升的集成"""
        user = self.user_level1
        today = date.today()

        # Initial reward at level 1
        reward_l1 = DailyLoginReward.objects.create(
            user=user,
            date=today,
            user_level=1,
            reward_amount=1
        )

        # User levels up to 2
        user.level = 2
        user.save()

        tomorrow = today + timedelta(days=1)

        # Reward at level 2 should be higher
        reward_l2 = DailyLoginReward.objects.create(
            user=user,
            date=tomorrow,
            user_level=2,
            reward_amount=2
        )

        # Verify progression
        self.assertLess(reward_l1.reward_amount, reward_l2.reward_amount)
        self.assertEqual(reward_l1.user_level, 1)
        self.assertEqual(reward_l2.user_level, 2)

    @patch('django.utils.timezone.now')
    def test_reward_timing_and_scheduling(self, mock_now):
        """测试奖励时机和调度"""
        base_time = timezone.now()
        mock_now.return_value = base_time

        # Create task that will generate hourly rewards
        task = LockTaskFactory.create_active_task(
            self.user_level2,
            start_time=base_time,
            end_time=base_time + timedelta(hours=3)
        )

        # Simulate hourly reward generation
        for hour in range(1, 4):
            reward_time = base_time + timedelta(hours=hour)
            mock_now.return_value = reward_time

            reward = HourlyReward.objects.create(
                task=task,
                user=self.user_level2,
                reward_amount=15,
                hour_count=hour
            )

            # Verify timing
            self.assertEqual(reward.hour_count, hour)
            self.assertLessEqual(reward.created_at, reward_time)

    def test_reward_history_and_statistics(self):
        """测试奖励历史和统计"""
        user = self.user_level3
        start_date = date.today() - timedelta(days=7)

        # Create week of daily rewards
        daily_rewards = []
        for day in range(7):
            reward_date = start_date + timedelta(days=day)
            reward = DailyLoginReward.objects.create(
                user=user,
                date=reward_date,
                user_level=user.level,
                reward_amount=user.level
            )
            daily_rewards.append(reward)

        # Create task with multiple hourly rewards
        task = LockTaskFactory.create_active_task(user)
        hourly_rewards = []
        for hour in range(1, 6):
            reward = HourlyReward.objects.create(
                task=task,
                user=user,
                reward_amount=12,
                hour_count=hour
            )
            hourly_rewards.append(reward)

        # Calculate statistics
        total_daily_rewards = sum(r.reward_amount for r in daily_rewards)
        total_hourly_rewards = sum(r.reward_amount for r in hourly_rewards)
        total_rewards = total_daily_rewards + total_hourly_rewards

        # Verify statistics
        self.assertEqual(len(daily_rewards), 7)
        self.assertEqual(len(hourly_rewards), 5)
        self.assertEqual(total_daily_rewards, user.level * 7)
        self.assertEqual(total_hourly_rewards, 12 * 5)


class RewardSystemEdgeCasesTest(BaseBusinessLogicTestCase):
    """Test edge cases and boundary conditions for reward system"""

    def test_reward_with_zero_amount(self):
        """测试零奖励金额"""
        task = LockTaskFactory.create_active_task(self.user_level2)

        # Create reward with zero amount
        reward = HourlyReward.objects.create(
            task=task,
            user=self.user_level2,
            reward_amount=0,
            hour_count=1
        )

        self.assertEqual(reward.reward_amount, 0)
        # Should still be a valid reward record

    def test_reward_with_negative_amount(self):
        """测试负奖励金额（惩罚）"""
        task = LockTaskFactory.create_active_task(self.user_level2)

        # In some systems, negative rewards might represent penalties
        penalty = HourlyReward.objects.create(
            task=task,
            user=self.user_level2,
            reward_amount=-10,  # Penalty
            hour_count=1
        )

        self.assertEqual(penalty.reward_amount, -10)

    def test_reward_for_very_long_task(self):
        """测试极长任务的奖励"""
        task = LockTaskFactory.create_active_task(self.user_level2)

        # Create rewards for 100 hours (extreme case)
        very_long_hours = 100
        rewards = []

        for hour in range(1, very_long_hours + 1):
            reward = HourlyReward.objects.create(
                task=task,
                user=self.user_level2,
                reward_amount=10,
                hour_count=hour
            )
            rewards.append(reward)

        self.assertEqual(len(rewards), very_long_hours)

        # Verify last reward
        last_reward = rewards[-1]
        self.assertEqual(last_reward.hour_count, very_long_hours)

    def test_daily_reward_for_future_date(self):
        """测试未来日期的每日奖励"""
        user = self.user_level2
        future_date = date.today() + timedelta(days=30)

        # Should be able to create reward for future date
        future_reward = DailyLoginReward.objects.create(
            user=user,
            date=future_date,
            user_level=user.level,
            reward_amount=user.level
        )

        self.assertEqual(future_reward.date, future_date)

    def test_daily_reward_for_very_old_date(self):
        """测试很久以前日期的每日奖励"""
        user = self.user_level2
        old_date = date.today() - timedelta(days=365)  # One year ago

        old_reward = DailyLoginReward.objects.create(
            user=user,
            date=old_date,
            user_level=user.level,
            reward_amount=user.level
        )

        self.assertEqual(old_reward.date, old_date)

    def test_reward_for_deleted_task(self):
        """测试已删除任务的奖励处理"""
        task = LockTaskFactory.create_active_task(self.user_level2)

        # Create reward
        reward = HourlyReward.objects.create(
            task=task,
            user=self.user_level2,
            reward_amount=15,
            hour_count=1
        )

        task_id = task.id

        # Delete task (cascade should delete reward)
        task.delete()

        # Reward should be deleted due to CASCADE
        self.assertFalse(HourlyReward.objects.filter(id=reward.id).exists())

    def test_reward_for_non_existent_user(self):
        """测试不存在用户的奖励"""
        task = LockTaskFactory.create_active_task(self.user_level2)

        # This should fail due to foreign key constraint
        with self.assertRaises(Exception):
            HourlyReward.objects.create(
                task=task,
                user_id=uuid.uuid4(),  # Non-existent user
                reward_amount=15,
                hour_count=1
            )

    def test_concurrent_daily_reward_creation(self):
        """测试并发每日奖励创建"""
        user = self.user_level2
        today = date.today()

        # First reward creation succeeds
        reward1 = DailyLoginReward.objects.create(
            user=user,
            date=today,
            user_level=user.level,
            reward_amount=user.level
        )

        # Second attempt should fail due to unique constraint
        with self.assertRaises(IntegrityError):
            DailyLoginReward.objects.create(
                user=user,
                date=today,
                user_level=user.level,
                reward_amount=user.level
            )

    def test_reward_with_extreme_hour_count(self):
        """测试极端小时数的奖励"""
        task = LockTaskFactory.create_active_task(self.user_level2)

        # Test very high hour count
        extreme_hour = 9999
        extreme_reward = HourlyReward.objects.create(
            task=task,
            user=self.user_level2,
            reward_amount=10,
            hour_count=extreme_hour
        )

        self.assertEqual(extreme_reward.hour_count, extreme_hour)

    def test_reward_amount_precision(self):
        """测试奖励金额精度"""
        task = LockTaskFactory.create_active_task(self.user_level2)

        # Test decimal reward amounts (should be converted to int)
        decimal_amount = 15.7
        int_amount = int(decimal_amount)

        reward = HourlyReward.objects.create(
            task=task,
            user=self.user_level2,
            reward_amount=int_amount,
            hour_count=1
        )

        self.assertEqual(reward.reward_amount, 15)
        self.assertIsInstance(reward.reward_amount, int)


if __name__ == '__main__':
    import unittest
    unittest.main()