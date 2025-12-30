#!/usr/bin/env python3
"""
Event System Integration Tests

This module tests the complete end-to-end event system integration:
- Full event lifecycle from definition to completion
- Cross-system integration (users, tasks, store, notifications)
- Complex event scenarios with multiple effects
- Performance and concurrency testing
- Error recovery and rollback scenarios

Author: Claude Code
Created: 2024-12-30
"""

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.db import transaction

from events.models import (
    EventDefinition, EventEffect, EventOccurrence,
    EventEffectExecution, UserGameEffect, UserCoinsMultiplier
)
from events.celery_tasks import (
    schedule_pending_events, execute_pending_events,
    process_expired_effects, trigger_manual_event
)
from store.models import Item, ItemType
from tasks.models import LockTask
from tests.events.test_base import EventTestCase, EventTransactionTestCase, EventMockHelpers


class EndToEndEventExecutionTest(EventTestCase):
    """Test complete event execution from start to finish"""

    def test_complete_weather_event_lifecycle(self):
        """Test complete weather event from scheduling to completion"""
        # Create weather event with multiple effects
        event_def = self.create_test_event_definition(
            name='blizzard_event',
            category='weather',
            title='大暴雪',
            description='寒冷的暴雪席卷而来，冻结了所有任务',
            schedule_type='interval_hours',
            interval_value=6
        )

        # Add coins compensation effect
        coins_effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 20},
            priority=1
        )

        # Add task freeze effect
        freeze_effect = self.create_test_event_effect(
            event_def,
            effect_type='task_freeze_all',
            target_type='active_task_users',
            priority=2
        )

        # Create active tasks for some users
        task1 = self.create_test_lock_task(self.user_level1, status='active')
        task2 = self.create_test_lock_task(self.user_level2, status='active')

        # Store original coins
        original_coins = {
            self.user_level1.id: self.user_level1.coins,
            self.user_level2.id: self.user_level2.coins,
            self.user_level3.id: self.user_level3.coins,
            self.user_level4.id: self.user_level4.coins,
        }

        # Schedule the event
        with EventMockHelpers.mock_timezone_now():
            schedule_result = schedule_pending_events()

        self.assertEqual(schedule_result['status'], 'success')
        self.assertEqual(schedule_result['scheduled_count'], 1)

        # Verify occurrence created
        occurrence = EventOccurrence.objects.filter(event_definition=event_def).first()
        self.assertIsNotNone(occurrence)
        self.assertEqual(occurrence.status, 'pending')
        self.assertEqual(occurrence.trigger_type, 'scheduled')

        # Execute the event
        with EventMockHelpers.mock_notification_creation():
            execute_result = execute_pending_events()

        self.assertEqual(execute_result['status'], 'success')
        self.assertEqual(execute_result['executed_count'], 1)

        # Verify occurrence completed
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status, 'completed')
        self.assertIsNotNone(occurrence.started_at)
        self.assertIsNotNone(occurrence.completed_at)
        self.assertEqual(len(occurrence.execution_log), 2)

        # Verify coins effect
        for user_id, original_amount in original_coins.items():
            from users.models import User
            user = User.objects.get(id=user_id)
            self.assertEqual(user.coins, original_amount + 20)

        # Verify task freeze effect
        task1.refresh_from_db()
        task2.refresh_from_db()
        self.assertTrue(task1.is_frozen)
        self.assertTrue(task2.is_frozen)
        self.assertIsNotNone(task1.frozen_at)
        self.assertIsNotNone(task2.frozen_at)

        # Verify effect executions created
        executions = EventEffectExecution.objects.filter(occurrence=occurrence)
        self.assertGreater(executions.count(), 0)

        # Verify execution data
        coins_executions = executions.filter(effect=coins_effect)
        self.assertEqual(coins_executions.count(), 5)  # All 5 users

        freeze_executions = executions.filter(effect=freeze_effect)
        self.assertEqual(freeze_executions.count(), 2)  # Only users with active tasks

    def test_magic_event_with_persistent_effects(self):
        """Test magic event with persistent multiplier effects"""
        # Create magic event with temporary multiplier
        event_def = self.create_test_event_definition(
            name='fortune_magic',
            category='magic',
            title='财富魔法',
            description='神秘的魔法增强了积分获取能力'
        )

        multiplier_effect = self.create_test_event_effect(
            event_def,
            effect_type='temporary_coins_multiplier',
            target_type='random_percentage',
            effect_parameters={'multiplier': 2.0},
            target_parameters={'percentage': 50},
            duration_minutes=60,
            priority=1
        )

        # Trigger manual event
        with EventMockHelpers.mock_notification_creation():
            result = trigger_manual_event(str(event_def.id), self.admin_user.id)

        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['affected_users'], 0)

        # Verify persistent effects created
        active_multipliers = UserCoinsMultiplier.objects.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        )
        self.assertGreater(active_multipliers.count(), 0)

        # Verify multiplier properties
        multiplier = active_multipliers.first()
        self.assertEqual(multiplier.multiplier, 2.0)
        self.assertIsNotNone(multiplier.expires_at)

        # Test expiration processing
        # Mock time to future
        future_time = timezone.now() + timedelta(hours=2)
        with patch('django.utils.timezone.now', return_value=future_time):
            expire_result = process_expired_effects()

        self.assertEqual(expire_result['status'], 'success')
        self.assertGreater(expire_result['processed_count'], 0)

        # Verify effects expired
        multiplier.refresh_from_db()
        self.assertFalse(multiplier.is_active)

    def test_complex_system_event_multiple_targets(self):
        """Test complex system event with multiple target types"""
        # Create system event with level-based and random targeting
        event_def = self.create_test_event_definition(
            name='maintenance_compensation',
            category='system',
            title='维护补偿',
            description='系统维护补偿，感谢您的耐心等待'
        )

        # Level-based coins for high-level users
        high_level_coins = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            target_type='level_based',
            effect_parameters={'amount': 100},
            target_parameters={'levels': [3, 4]},
            priority=1
        )

        # Random item distribution
        item_effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            target_type='random_percentage',
            effect_parameters={'item_type': 'photo_paper', 'quantity': 2},
            target_parameters={'percentage': 75},
            priority=2
        )

        # Store original state
        original_coins = {
            user.id: user.coins for user in [
                self.user_level1, self.user_level2,
                self.user_level3, self.user_level4
            ]
        }

        original_items = {
            user.id: Item.objects.filter(
                owner=user,
                item_type=self.photo_paper_type,
                status='available'
            ).count() for user in [
                self.user_level1, self.user_level2,
                self.user_level3, self.user_level4
            ]
        }

        # Execute event
        with EventMockHelpers.mock_notification_creation():
            result = trigger_manual_event(str(event_def.id), self.admin_user.id)

        self.assertEqual(result['status'], 'success')

        # Verify level-based coins effect
        self.user_level1.refresh_from_db()
        self.user_level2.refresh_from_db()
        self.user_level3.refresh_from_db()
        self.user_level4.refresh_from_db()

        # Level 1,2 should not get high-level coins
        self.assertEqual(self.user_level1.coins, original_coins[self.user_level1.id])
        self.assertEqual(self.user_level2.coins, original_coins[self.user_level2.id])

        # Level 3,4 should get high-level coins
        self.assertEqual(self.user_level3.coins, original_coins[self.user_level3.id] + 100)
        self.assertEqual(self.user_level4.coins, original_coins[self.user_level4.id] + 100)

        # Verify item distribution (random, so check if some users got items)
        total_new_items = 0
        for user in [self.user_level1, self.user_level2, self.user_level3, self.user_level4]:
            current_items = Item.objects.filter(
                owner=user,
                item_type=self.photo_paper_type,
                status='available'
            ).count()
            new_items = current_items - original_items[user.id]
            total_new_items += new_items

        self.assertGreater(total_new_items, 0)  # At least some items distributed

    def test_event_error_recovery(self):
        """Test event execution error recovery and partial completion"""
        # Create event with one valid and one invalid effect
        event_def = self.create_test_event_definition(
            name='error_test_event',
            title='Error Test Event'
        )

        # Valid coins effect
        valid_effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            effect_parameters={'amount': 50},
            priority=1
        )

        # Invalid item effect (nonexistent item type)
        invalid_effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            effect_parameters={'item_type': 'nonexistent_item'},
            priority=2
        )

        # Store original coins
        original_coins = self.user_level1.coins

        # Execute event
        with EventMockHelpers.mock_notification_creation():
            result = trigger_manual_event(str(event_def.id))

        # Event should complete despite partial failure
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['execution_log']), 2)

        # Valid effect should succeed
        coins_log = next(log for log in result['execution_log'] if log['effect_type'] == 'coins_add')
        self.assertGreater(coins_log['affected_count'], 0)

        # Invalid effect should fail
        item_log = next(log for log in result['execution_log'] if log['effect_type'] == 'item_distribute')
        self.assertIn('error', item_log)
        self.assertEqual(item_log['affected_count'], 0)

        # Verify coins were still distributed
        self.user_level1.refresh_from_db()
        self.assertEqual(self.user_level1.coins, original_coins + 50)


class EventSystemConcurrencyTest(EventTransactionTestCase):
    """Test event system under concurrent conditions"""

    def test_concurrent_event_execution(self):
        """Test multiple events executing concurrently"""
        # Create multiple events
        event1 = EventDefinition.objects.create(
            name='concurrent_event_1',
            title='Concurrent Event 1',
            category='system',
            schedule_type='manual',
            created_by=self.admin_user
        )

        event2 = EventDefinition.objects.create(
            name='concurrent_event_2',
            title='Concurrent Event 2',
            category='system',
            schedule_type='manual',
            created_by=self.admin_user
        )

        # Add effects to both events
        EventEffect.objects.create(
            event_definition=event1,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 25},
            priority=1
        )

        EventEffect.objects.create(
            event_definition=event2,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 30},
            priority=1
        )

        # Create occurrences for both events
        occurrence1 = EventOccurrence.objects.create(
            event_definition=event1,
            scheduled_at=timezone.now() - timedelta(minutes=1),
            trigger_type='manual'
        )

        occurrence2 = EventOccurrence.objects.create(
            event_definition=event2,
            scheduled_at=timezone.now() - timedelta(minutes=1),
            trigger_type='manual'
        )

        # Store original coins
        original_coins = self.test_user.coins

        # Execute both events
        with EventMockHelpers.mock_notification_creation():
            result = execute_pending_events()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['executed_count'], 2)

        # Verify both effects applied
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.coins, original_coins + 25 + 30)

        # Verify both occurrences completed
        occurrence1.refresh_from_db()
        occurrence2.refresh_from_db()
        self.assertEqual(occurrence1.status, 'completed')
        self.assertEqual(occurrence2.status, 'completed')

    def test_event_rollback_transaction_safety(self):
        """Test transaction safety during event rollback"""
        # Create event with rollback-capable effect
        event_def = EventDefinition.objects.create(
            name='rollback_test',
            title='Rollback Test',
            category='system',
            schedule_type='manual',
            created_by=self.admin_user
        )

        effect = EventEffect.objects.create(
            event_definition=event_def,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 100},
            duration_minutes=30,
            priority=1
        )

        # Execute event
        with EventMockHelpers.mock_notification_creation():
            result = trigger_manual_event(str(event_def.id))

        self.assertEqual(result['status'], 'success')

        # Verify coins added
        original_coins = self.test_user.coins
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.coins, original_coins + 100)

        # Get execution record
        execution = EventEffectExecution.objects.filter(
            effect=effect,
            target_user=self.test_user
        ).first()
        self.assertIsNotNone(execution)

        # Simulate expiration and rollback
        execution.expires_at = timezone.now() - timedelta(minutes=1)
        execution.save()

        # Process expired effects
        result = process_expired_effects()
        self.assertEqual(result['status'], 'success')

        # Verify rollback occurred
        execution.refresh_from_db()
        self.assertTrue(execution.is_expired)
        self.assertTrue(execution.is_rolled_back)

        # Verify coins restored
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.coins, original_coins)


class CrossSystemIntegrationTest(EventTestCase):
    """Test integration with other system components"""

    def test_notification_system_integration(self):
        """Test integration with notification system"""
        event_def = self.create_test_event_definition(
            name='notification_test',
            title='通知测试事件'
        )

        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            effect_parameters={'amount': 10}
        )

        # Mock notification creation to verify calls
        with patch('users.models.Notification.create_notification') as mock_notification:
            result = trigger_manual_event(str(event_def.id))

        self.assertEqual(result['status'], 'success')

        # Verify notifications were created for affected users
        self.assertGreater(mock_notification.call_count, 0)

        # Check notification parameters
        call_args = mock_notification.call_args_list[0][1]
        self.assertEqual(call_args['notification_type'], 'system_event_occurred')
        self.assertIn('event_title', call_args['extra_data'])
        self.assertEqual(call_args['extra_data']['event_title'], '通知测试事件')

    def test_task_system_integration(self):
        """Test integration with task management system"""
        # Create active tasks
        task1 = self.create_test_lock_task(
            self.user_level1,
            status='active',
            is_frozen=False
        )
        task2 = self.create_test_lock_task(
            self.user_level2,
            status='active',
            is_frozen=False
        )

        # Create task freeze event
        event_def = self.create_test_event_definition(
            name='task_freeze_test',
            title='任务冻结测试'
        )

        freeze_effect = self.create_test_event_effect(
            event_def,
            effect_type='task_freeze_all',
            target_type='active_task_users'
        )

        # Mock timeline event creation
        with patch('tasks.models.TaskTimelineEvent.objects.create') as mock_timeline:
            with EventMockHelpers.mock_notification_creation():
                result = trigger_manual_event(str(event_def.id))

        self.assertEqual(result['status'], 'success')

        # Verify tasks were frozen
        task1.refresh_from_db()
        task2.refresh_from_db()
        self.assertTrue(task1.is_frozen)
        self.assertTrue(task2.is_frozen)

        # Verify timeline events were created
        self.assertEqual(mock_timeline.call_count, 2)

        # Check timeline event parameters
        call_args = mock_timeline.call_args_list[0][1]
        self.assertEqual(call_args['event_type'], 'system_freeze')
        self.assertIn('event_id', call_args['metadata'])

    def test_store_system_integration(self):
        """Test integration with store and inventory system"""
        # Create event that distributes items
        event_def = self.create_test_event_definition(
            name='item_distribution_test',
            title='道具分发测试'
        )

        item_effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            target_type='all_users',
            effect_parameters={
                'item_type': 'photo_paper',
                'quantity': 3
            }
        )

        # Store original item counts
        original_counts = {}
        for user in [self.user_level1, self.user_level2, self.user_level3, self.user_level4]:
            original_counts[user.id] = Item.objects.filter(
                owner=user,
                item_type=self.photo_paper_type,
                status='available'
            ).count()

        # Execute event
        with EventMockHelpers.mock_notification_creation():
            result = trigger_manual_event(str(event_def.id))

        self.assertEqual(result['status'], 'success')

        # Verify items were distributed
        for user in [self.user_level1, self.user_level2, self.user_level3, self.user_level4]:
            current_count = Item.objects.filter(
                owner=user,
                item_type=self.photo_paper_type,
                status='available'
            ).count()
            self.assertEqual(current_count, original_counts[user.id] + 3)

        # Verify item properties include event metadata
        new_items = Item.objects.filter(
            properties__source='event',
            properties__event_id=str(event_def.id)
        )
        self.assertGreater(new_items.count(), 0)

    def test_user_level_based_targeting(self):
        """Test user level-based targeting integration"""
        event_def = self.create_test_event_definition(
            name='level_targeting_test',
            title='等级定向测试'
        )

        # Create effects for different levels
        low_level_effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            target_type='level_based',
            effect_parameters={'amount': 50},
            target_parameters={'levels': [1, 2]},
            priority=1
        )

        high_level_effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            target_type='level_based',
            effect_parameters={'amount': 100},
            target_parameters={'levels': [3, 4]},
            priority=2
        )

        # Store original coins
        original_coins = {
            self.user_level1.id: self.user_level1.coins,
            self.user_level2.id: self.user_level2.coins,
            self.user_level3.id: self.user_level3.coins,
            self.user_level4.id: self.user_level4.coins,
        }

        # Execute event
        with EventMockHelpers.mock_notification_creation():
            result = trigger_manual_event(str(event_def.id))

        self.assertEqual(result['status'], 'success')

        # Verify level-based targeting
        self.user_level1.refresh_from_db()
        self.user_level2.refresh_from_db()
        self.user_level3.refresh_from_db()
        self.user_level4.refresh_from_db()

        # Low level users get 50 coins
        self.assertEqual(self.user_level1.coins, original_coins[self.user_level1.id] + 50)
        self.assertEqual(self.user_level2.coins, original_coins[self.user_level2.id] + 50)

        # High level users get 100 coins
        self.assertEqual(self.user_level3.coins, original_coins[self.user_level3.id] + 100)
        self.assertEqual(self.user_level4.coins, original_coins[self.user_level4.id] + 100)


class EventSystemPerformanceTest(EventTestCase):
    """Test event system performance with large datasets"""

    def test_large_user_base_performance(self):
        """Test event execution with large number of users"""
        from users.models import User

        # Create additional test users (simulate larger user base)
        additional_users = []
        for i in range(50):
            user = User.objects.create_user(
                username=f'perf_user_{i}',
                email=f'perf_user_{i}@test.com',
                password='testpass123',
                level=1,
                coins=100
            )
            additional_users.append(user)

        # Create event affecting all users
        event_def = self.create_test_event_definition(
            name='performance_test',
            title='性能测试事件'
        )

        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 10}
        )

        # Measure execution time
        import time
        start_time = time.time()

        with EventMockHelpers.mock_notification_creation():
            result = trigger_manual_event(str(event_def.id))

        execution_time = time.time() - start_time

        # Verify success and performance
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['affected_users'], 50)  # At least our additional users
        self.assertLess(execution_time, 10)  # Should complete within 10 seconds

        # Clean up additional users
        User.objects.filter(username__startswith='perf_user_').delete()

    def test_multiple_effects_performance(self):
        """Test performance with multiple effects in single event"""
        event_def = self.create_test_event_definition(
            name='multi_effect_performance',
            title='多效果性能测试'
        )

        # Create 10 different effects
        effects = []
        for i in range(10):
            effect = self.create_test_event_effect(
                event_def,
                effect_type='coins_add',
                target_type='all_users',
                effect_parameters={'amount': i + 1},
                priority=i + 1
            )
            effects.append(effect)

        # Execute event
        import time
        start_time = time.time()

        with EventMockHelpers.mock_notification_creation():
            result = trigger_manual_event(str(event_def.id))

        execution_time = time.time() - start_time

        # Verify all effects executed
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['execution_log']), 10)
        self.assertLess(execution_time, 5)  # Should complete within 5 seconds

        # Verify total coins added (1+2+3+...+10 = 55 per user)
        self.user_level1.refresh_from_db()
        expected_total = sum(range(1, 11))  # 55
        self.assertEqual(self.user_level1.coins, 100 + expected_total)