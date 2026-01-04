"""
任务验证器单元测试
"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from rest_framework import status

from tasks.models import LockTask
from tasks.validators import validate_task_completion_conditions
from store.models import ItemType, Item

User = get_user_model()


class TaskValidationTestCase(TestCase):
    """任务验证条件测试"""

    def setUp(self):
        """设置测试数据"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )

        # 创建钥匙道具类型
        self.key_item_type = ItemType.objects.create(
            name='key',
            display_name='钥匙',
            description='任务钥匙',
            category='tools'
        )

    def create_lock_task(self, **kwargs):
        """创建带锁任务的辅助方法"""
        defaults = {
            'user': self.user,
            'title': '测试任务',
            'description': '测试描述',
            'task_type': 'lock',
            'status': 'active',
            'difficulty': 'easy',
            'duration_type': 'fixed',
            'duration_value': 60,
            'end_time': timezone.now() + timedelta(hours=1)
        }
        defaults.update(kwargs)
        return LockTask.objects.create(**defaults)

    def create_task_key(self, task, owner=None):
        """创建任务钥匙的辅助方法"""
        if owner is None:
            owner = self.user

        return Item.objects.create(
            item_type=self.key_item_type,
            owner=owner,
            original_owner=self.user,
            status='available',
            properties={'task_id': str(task.id)}
        )

    def test_normal_task_completion_with_key(self):
        """测试正常情况下有钥匙的任务完成验证"""
        task = self.create_lock_task(
            end_time=timezone.now() - timedelta(minutes=1)  # 已过期
        )
        self.create_task_key(task, self.user)

        can_complete, error_response = validate_task_completion_conditions(
            task, self.user, require_has_key=True
        )

        self.assertTrue(can_complete)
        self.assertIsNone(error_response)

    def test_frozen_task_cannot_complete(self):
        """测试冻结状态的任务不能完成"""
        task = self.create_lock_task(
            is_frozen=True,
            end_time=timezone.now() - timedelta(minutes=1)
        )
        self.create_task_key(task, self.user)

        can_complete, error_response = validate_task_completion_conditions(
            task, self.user, require_has_key=True
        )

        self.assertFalse(can_complete)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('冻结状态', error_response.data['error'])

    def test_task_with_time_remaining_cannot_complete(self):
        """测试倒计时未结束的任务不能完成"""
        task = self.create_lock_task(
            end_time=timezone.now() + timedelta(hours=1)  # 还有1小时
        )
        self.create_task_key(task, self.user)

        can_complete, error_response = validate_task_completion_conditions(
            task, self.user, require_has_key=True
        )

        self.assertFalse(can_complete)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('倒计时结束', error_response.data['error'])

    def test_user_without_key_cannot_complete(self):
        """测试没有钥匙的用户不能完成任务"""
        task = self.create_lock_task(
            end_time=timezone.now() - timedelta(minutes=1)
        )
        # 不创建钥匙

        can_complete, error_response = validate_task_completion_conditions(
            task, self.user, require_has_key=True
        )

        self.assertFalse(can_complete)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('钥匙道具', error_response.data['error'])

    def test_user_with_transferred_key_cannot_complete(self):
        """测试转让钥匙后原用户不能完成任务"""
        task = self.create_lock_task(
            end_time=timezone.now() - timedelta(minutes=1)
        )
        # 创建钥匙但转让给其他用户
        key = self.create_task_key(task, self.other_user)
        key.original_owner = self.user  # 设置原始拥有者
        key.save()

        can_complete, error_response = validate_task_completion_conditions(
            task, self.user, require_has_key=True
        )

        self.assertFalse(can_complete)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('转让给他人', error_response.data['error'])

    def test_current_key_holder_can_complete(self):
        """测试当前钥匙持有者可以完成任务"""
        task = self.create_lock_task(
            end_time=timezone.now() - timedelta(minutes=1)
        )
        # 创建钥匙并转让给其他用户
        key = self.create_task_key(task, self.other_user)
        key.original_owner = self.user
        key.save()

        can_complete, error_response = validate_task_completion_conditions(
            task, self.other_user, require_has_key=True
        )

        self.assertTrue(can_complete)
        self.assertIsNone(error_response)

    def test_universal_key_scenario_no_key_required(self):
        """测试万能钥匙场景（不需要验证钥匙）"""
        task = self.create_lock_task(
            end_time=timezone.now() - timedelta(minutes=1)
        )
        # 不创建钥匙

        can_complete, error_response = validate_task_completion_conditions(
            task, self.user, require_has_key=False
        )

        self.assertTrue(can_complete)
        self.assertIsNone(error_response)

    def test_vote_task_without_voting(self):
        """测试投票解锁任务未发起投票时不能完成"""
        task = self.create_lock_task(
            unlock_type='vote',
            end_time=timezone.now() - timedelta(minutes=1)
        )
        self.create_task_key(task, self.user)

        can_complete, error_response = validate_task_completion_conditions(
            task, self.user, require_has_key=True
        )

        self.assertFalse(can_complete)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('发起投票', error_response.data['error'])

    def test_vote_task_with_voting_passed_status(self):
        """测试投票通过状态的任务可以完成"""
        task = self.create_lock_task(
            unlock_type='vote',
            status='voting_passed',
            end_time=timezone.now() - timedelta(minutes=1)
        )
        self.create_task_key(task, self.user)

        can_complete, error_response = validate_task_completion_conditions(
            task, self.user, require_has_key=True
        )

        self.assertTrue(can_complete)
        self.assertIsNone(error_response)

    def test_task_without_end_time_can_complete(self):
        """测试没有结束时间的任务可以完成"""
        task = self.create_lock_task(end_time=None)
        self.create_task_key(task, self.user)

        can_complete, error_response = validate_task_completion_conditions(
            task, self.user, require_has_key=True
        )

        self.assertTrue(can_complete)
        self.assertIsNone(error_response)


class BackwardCompatibilityTestCase(TestCase):
    """向后兼容性测试"""

    def test_old_function_name_still_works(self):
        """测试旧函数名仍然可用"""
        from tasks.validators import _can_complete_lock_task

        # 确保别名存在且指向正确的函数
        self.assertEqual(_can_complete_lock_task, validate_task_completion_conditions)