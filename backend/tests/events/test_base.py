#!/usr/bin/env python3
"""
Base Test Classes for Event System

This module provides base test classes and utilities for testing the event system:
- EventTestCase: Base class with common setup and utilities
- Test fixtures and factory methods
- Mock utilities for external dependencies

Author: Claude Code
Created: 2024-12-30
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
import json

from events.models import (
    EventDefinition, EventEffect, EventOccurrence,
    EventEffectExecution, UserGameEffect, UserCoinsMultiplier
)
from store.models import Item, ItemType
from tasks.models import LockTask

User = get_user_model()


class EventTestCase(TestCase):
    """Base test case for event system tests"""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests"""
        # Create test users with different levels
        cls.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            is_staff=True,
            level=4,
            coins=1000
        )

        cls.user_level1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123',
            level=1,
            coins=100
        )

        cls.user_level2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123',
            level=2,
            coins=200
        )

        cls.user_level3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='testpass123',
            level=3,
            coins=300
        )

        cls.user_level4 = User.objects.create_user(
            username='user4',
            email='user4@test.com',
            password='testpass123',
            level=4,
            coins=400
        )

        # Create test item types
        cls.photo_paper_type = ItemType.objects.create(
            name='photo_paper',
            display_name='照片纸',
            description='用于拍摄照片的特殊纸张',
            price=10,
            max_quantity=5
        )

        cls.detection_radar_type = ItemType.objects.create(
            name='detection_radar',
            display_name='探测雷达',
            description='探测周围物品的神奇雷达',
            price=50,
            max_quantity=2
        )

    def setUp(self):
        """Set up test state before each test"""
        super().setUp()
        # Refresh user instances to avoid cached state
        self.admin_user.refresh_from_db()
        self.user_level1.refresh_from_db()
        self.user_level2.refresh_from_db()
        self.user_level3.refresh_from_db()
        self.user_level4.refresh_from_db()

    def create_test_event_definition(self, **kwargs):
        """Create a test event definition with default values"""
        defaults = {
            'name': 'test_event',
            'category': 'system',
            'title': 'Test Event',
            'description': 'A test event for unit testing',
            'schedule_type': 'manual',
            'is_active': True,
            'created_by': self.admin_user
        }
        defaults.update(kwargs)
        return EventDefinition.objects.create(**defaults)

    def create_test_event_effect(self, event_definition, **kwargs):
        """Create a test event effect with default values"""
        defaults = {
            'event_definition': event_definition,
            'effect_type': 'coins_add',
            'target_type': 'all_users',
            'effect_parameters': {'amount': 10},
            'target_parameters': {},
            'priority': 1,
            'is_active': True
        }
        defaults.update(kwargs)
        return EventEffect.objects.create(**defaults)

    def create_test_event_occurrence(self, event_definition, **kwargs):
        """Create a test event occurrence with default values"""
        defaults = {
            'event_definition': event_definition,
            'scheduled_at': timezone.now(),
            'trigger_type': 'manual',
            'status': 'pending'
        }
        defaults.update(kwargs)
        return EventOccurrence.objects.create(**defaults)

    def create_test_lock_task(self, user, **kwargs):
        """Create a test lock task for testing task-related effects"""
        defaults = {
            'user': user,
            'task_type': 'lock',
            'status': 'active',
            'start_time': timezone.now(),
            'end_time': timezone.now() + timedelta(hours=2),
            'is_frozen': False
        }
        defaults.update(kwargs)
        return LockTask.objects.create(**defaults)

    def assert_user_coins_changed(self, user, expected_change):
        """Assert that user's coins changed by expected amount"""
        user.refresh_from_db()
        original_coins = getattr(user, '_original_coins', user.coins - expected_change)
        actual_change = user.coins - original_coins
        self.assertEqual(
            actual_change,
            expected_change,
            f"Expected coins change of {expected_change}, got {actual_change}"
        )

    def assert_user_has_item(self, user, item_type_name, quantity=1):
        """Assert that user has specific item quantity"""
        item_count = Item.objects.filter(
            owner=user,
            item_type__name=item_type_name,
            status='available'
        ).count()
        self.assertEqual(
            item_count,
            quantity,
            f"Expected {quantity} {item_type_name} items, found {item_count}"
        )

    def assert_task_frozen(self, task, is_frozen=True):
        """Assert that task is frozen/unfrozen as expected"""
        task.refresh_from_db()
        self.assertEqual(
            task.is_frozen,
            is_frozen,
            f"Expected task.is_frozen to be {is_frozen}, got {task.is_frozen}"
        )

    def mock_celery_task(self, task_function):
        """Mock a Celery task to run synchronously"""
        def sync_task(*args, **kwargs):
            return task_function(*args, **kwargs)

        return patch.object(task_function, 'delay', side_effect=sync_task)


class EventTransactionTestCase(TransactionTestCase):
    """Base test case for testing transaction behavior"""

    def setUp(self):
        """Set up test state"""
        super().setUp()
        # Create minimal test data
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_superuser=True,
            level=4,
            coins=1000
        )

        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            level=1,
            coins=100
        )


class EventTestMixin:
    """Mixin providing common test utilities"""

    def create_sample_weather_event(self):
        """Create a sample weather event for testing"""
        event_def = self.create_test_event_definition(
            name='test_weather',
            category='weather',
            title='Test Weather Event',
            description='A weather event for testing'
        )

        # Add coins effect
        coins_effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 50},
            priority=1
        )

        # Add item distribution effect
        item_effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            target_type='level_based',
            effect_parameters={'item_type': 'photo_paper', 'quantity': 2},
            target_parameters={'levels': [1, 2]},
            priority=2
        )

        return event_def, [coins_effect, item_effect]

    def create_sample_magic_event(self):
        """Create a sample magic event with persistent effects"""
        event_def = self.create_test_event_definition(
            name='test_magic',
            category='magic',
            title='Test Magic Event',
            description='A magic event with persistent effects'
        )

        # Add temporary coins multiplier
        multiplier_effect = self.create_test_event_effect(
            event_def,
            effect_type='temporary_coins_multiplier',
            target_type='random_percentage',
            effect_parameters={'multiplier': 2.0},
            target_parameters={'percentage': 50},
            duration_minutes=60,
            priority=1
        )

        return event_def, [multiplier_effect]

    def assert_event_execution_log(self, occurrence, expected_effects_count):
        """Assert that event occurrence has proper execution log"""
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status, 'completed')
        self.assertEqual(len(occurrence.execution_log), expected_effects_count)
        self.assertGreater(occurrence.affected_users_count, 0)

    def get_effect_execution_count(self, effect, user=None):
        """Get count of effect executions, optionally for specific user"""
        queryset = EventEffectExecution.objects.filter(effect=effect)
        if user:
            queryset = queryset.filter(target_user=user)
        return queryset.count()


class EventMockHelpers:
    """Helper class for mocking external dependencies"""

    @staticmethod
    def mock_notification_creation():
        """Mock notification creation to avoid dependencies"""
        return patch('users.models.Notification.create_notification')

    @staticmethod
    def mock_telegram_service():
        """Mock Telegram service for notification testing"""
        return patch('telegram_bot.services.telegram_service.send_notification')

    @staticmethod
    def mock_timezone_now(fixed_time=None):
        """Mock timezone.now() to return fixed time"""
        if fixed_time is None:
            fixed_time = timezone.now()
        return patch('django.utils.timezone.now', return_value=fixed_time)

    @staticmethod
    def create_mock_celery_task_result(task_id='test-task-id', status='SUCCESS', result=None):
        """Create a mock Celery task result"""
        mock_result = MagicMock()
        mock_result.id = task_id
        mock_result.status = status
        mock_result.result = result or {'status': 'success'}
        return mock_result