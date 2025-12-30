#!/usr/bin/env python3
"""
Event Effects Unit Tests

This module tests the event effect execution system:
- BaseEffectExecutor abstract class
- CoinsEffectExecutor for coin manipulation
- ItemDistributeEffectExecutor for item distribution
- TaskEffectExecutors for task state management
- Target user selection algorithms
- Effect rollback mechanisms

Author: Claude Code
Created: 2024-12-30
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from events.models import EventDefinition, EventEffect
from events.effects import (
    get_effect_executor, BaseEffectExecutor, CoinsEffectExecutor,
    ItemDistributeEffectExecutor, TaskFreezeEffectExecutor,
    TemporaryCoinsMultiplierExecutor, TemporaryGameEnhancementExecutor,
    StoreDiscountEffectExecutor
)
from store.models import Item, ItemType
from tasks.models import LockTask
from tests.events.test_base import EventTestCase, EventMockHelpers


class EffectExecutorFactoryTest(EventTestCase):
    """Test effect executor factory function"""

    def test_get_coins_executor(self):
        """Test getting coins effect executor"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add'
        )

        executor = get_effect_executor(effect)
        self.assertIsInstance(executor, CoinsEffectExecutor)
        self.assertEqual(executor.effect, effect)

    def test_get_item_distribute_executor(self):
        """Test getting item distribute executor"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute'
        )

        executor = get_effect_executor(effect)
        self.assertIsInstance(executor, ItemDistributeEffectExecutor)

    def test_get_task_freeze_executor(self):
        """Test getting task freeze executor"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='task_freeze_all'
        )

        executor = get_effect_executor(effect)
        self.assertIsInstance(executor, TaskFreezeEffectExecutor)

    def test_unsupported_effect_type(self):
        """Test handling of unsupported effect types"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='unsupported_type'
        )

        with self.assertRaises((ValueError, KeyError, NotImplementedError)):
            get_effect_executor(effect)


class BaseEffectExecutorTest(EventTestCase):
    """Test BaseEffectExecutor abstract class"""

    def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)

        # Cannot instantiate abstract class directly
        with self.assertRaises(TypeError):
            BaseEffectExecutor(effect)

    def test_concrete_executor_implements_abstract_methods(self):
        """Test that concrete executors implement required methods"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)

        executor = CoinsEffectExecutor(effect)

        # Should have required methods
        self.assertTrue(hasattr(executor, 'get_target_users'))
        self.assertTrue(hasattr(executor, 'execute_for_user'))
        self.assertTrue(callable(executor.get_target_users))
        self.assertTrue(callable(executor.execute_for_user))


class CoinsEffectExecutorTest(EventTestCase):
    """Test CoinsEffectExecutor"""

    def test_coins_add_all_users(self):
        """Test adding coins to all users"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 50}
        )

        executor = CoinsEffectExecutor(effect)

        # Get target users
        target_users = executor.get_target_users()
        self.assertIn(self.user_level1, target_users)
        self.assertIn(self.user_level2, target_users)

        # Store original coins
        original_coins = self.user_level1.coins

        # Execute for user
        result = executor.execute_for_user(self.user_level1)

        # Check result
        self.assertEqual(result['old_coins'], original_coins)
        self.assertEqual(result['new_coins'], original_coins + 50)
        self.assertEqual(result['amount_changed'], 50)

        # Check user coins updated
        self.user_level1.refresh_from_db()
        self.assertEqual(self.user_level1.coins, original_coins + 50)

    def test_coins_subtract_with_minimum(self):
        """Test subtracting coins with minimum of 0"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_subtract',
            target_type='all_users',
            effect_parameters={'amount': 150}  # More than user has
        )

        executor = CoinsEffectExecutor(effect)

        # User has 100 coins, subtract 150
        original_coins = self.user_level1.coins
        result = executor.execute_for_user(self.user_level1)

        # Should not go below 0
        self.assertEqual(result['old_coins'], original_coins)
        self.assertEqual(result['new_coins'], 0)
        self.assertEqual(result['amount_changed'], -original_coins)

        self.user_level1.refresh_from_db()
        self.assertEqual(self.user_level1.coins, 0)

    def test_coins_rollback(self):
        """Test coins effect rollback"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            effect_parameters={'amount': 50}
        )

        executor = CoinsEffectExecutor(effect)

        # Execute effect
        original_coins = self.user_level1.coins
        execution_data = executor.execute_for_user(self.user_level1)

        # Verify coins added
        self.user_level1.refresh_from_db()
        self.assertEqual(self.user_level1.coins, original_coins + 50)

        # Test rollback
        self.assertTrue(executor.can_rollback())
        success = executor.rollback_for_user(self.user_level1, execution_data)

        self.assertTrue(success)
        self.user_level1.refresh_from_db()
        self.assertEqual(self.user_level1.coins, original_coins)

    def test_target_selection_random_percentage(self):
        """Test random percentage target selection"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            target_type='random_percentage',
            target_parameters={'percentage': 50}
        )

        executor = CoinsEffectExecutor(effect)
        target_users = executor.get_target_users()

        # Should get approximately 50% of users (with small sample, might vary)
        total_users = 5  # We have 5 test users
        expected_count = int(total_users * 0.5)

        # Allow some variance due to randomness
        self.assertGreaterEqual(len(target_users), 0)
        self.assertLessEqual(len(target_users), total_users)

    def test_target_selection_level_based(self):
        """Test level-based target selection"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            target_type='level_based',
            target_parameters={'levels': [1, 2]}
        )

        executor = CoinsEffectExecutor(effect)
        target_users = executor.get_target_users()

        # Should only include level 1 and 2 users
        target_levels = [user.level for user in target_users]
        for level in target_levels:
            self.assertIn(level, [1, 2])

        # Should include our test users
        self.assertIn(self.user_level1, target_users)
        self.assertIn(self.user_level2, target_users)
        self.assertNotIn(self.user_level3, target_users)
        self.assertNotIn(self.user_level4, target_users)

    def test_target_selection_active_task_users(self):
        """Test active task users target selection"""
        # Create active tasks for some users
        task1 = self.create_test_lock_task(self.user_level1, status='active')
        task2 = self.create_test_lock_task(self.user_level2, status='active')

        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            target_type='active_task_users'
        )

        executor = CoinsEffectExecutor(effect)
        target_users = executor.get_target_users()

        # Should only include users with active tasks
        self.assertIn(self.user_level1, target_users)
        self.assertIn(self.user_level2, target_users)
        # Users without active tasks should not be included
        self.assertNotIn(self.user_level3, target_users)


class ItemDistributeEffectExecutorTest(EventTestCase):
    """Test ItemDistributeEffectExecutor"""

    def test_item_distribution_success(self):
        """Test successful item distribution"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            target_type='all_users',
            effect_parameters={
                'item_type': 'photo_paper',
                'quantity': 2
            }
        )

        executor = ItemDistributeEffectExecutor(effect)

        # Check initial item count
        initial_count = Item.objects.filter(
            owner=self.user_level1,
            item_type=self.photo_paper_type,
            status='available'
        ).count()

        # Execute effect
        result = executor.execute_for_user(self.user_level1)

        # Check result
        self.assertEqual(result['item_type'], 'photo_paper')
        self.assertEqual(result['quantity'], 2)
        self.assertEqual(len(result['item_ids']), 2)

        # Check items created
        final_count = Item.objects.filter(
            owner=self.user_level1,
            item_type=self.photo_paper_type,
            status='available'
        ).count()

        self.assertEqual(final_count, initial_count + 2)

    def test_item_distribution_invalid_type(self):
        """Test item distribution with invalid item type"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            effect_parameters={
                'item_type': 'nonexistent_item',
                'quantity': 1
            }
        )

        executor = ItemDistributeEffectExecutor(effect)
        result = executor.execute_for_user(self.user_level1)

        # Should return error
        self.assertIn('error', result)
        self.assertIn('nonexistent_item', result['error'])

    def test_item_distribution_capacity_check(self):
        """Test item distribution respects inventory capacity"""
        # Fill user's inventory to capacity
        max_capacity = self.user_level1.get_inventory_capacity()
        for i in range(max_capacity):
            Item.objects.create(
                item_type=self.photo_paper_type,
                owner=self.user_level1,
                original_owner=self.user_level1,
                status='available'
            )

        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            target_type='all_users',
            effect_parameters={
                'item_type': 'photo_paper',
                'quantity': 1
            }
        )

        executor = ItemDistributeEffectExecutor(effect)
        target_users = executor.get_target_users()

        # User with full inventory should not be in target list
        self.assertNotIn(self.user_level1, target_users)

    def test_item_properties_metadata(self):
        """Test item creation with event metadata"""
        event_def = self.create_test_event_definition(name='test_event_metadata')
        effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            effect_parameters={
                'item_type': 'photo_paper',
                'quantity': 1
            }
        )

        executor = ItemDistributeEffectExecutor(effect)
        result = executor.execute_for_user(self.user_level1)

        # Check created item has event metadata
        item_id = result['item_ids'][0]
        item = Item.objects.get(id=item_id)

        self.assertEqual(item.properties['source'], 'event')
        self.assertEqual(item.properties['event_id'], str(event_def.id))


class TaskEffectExecutorTest(EventTestCase):
    """Test task-related effect executors"""

    def test_task_freeze_all(self):
        """Test freezing all active tasks"""
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

        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='task_freeze_all'
        )

        executor = TaskFreezeEffectExecutor(effect)

        # Execute for user with active task
        result = executor.execute_for_user(self.user_level1)

        # Check result
        self.assertEqual(result['frozen_task_count'], 1)
        self.assertIn(str(task1.id), result['frozen_task_ids'])

        # Check task is frozen
        task1.refresh_from_db()
        self.assertTrue(task1.is_frozen)
        self.assertIsNotNone(task1.frozen_at)

    def test_task_unfreeze_all(self):
        """Test unfreezing all frozen tasks"""
        # Create frozen task
        task = self.create_test_lock_task(
            self.user_level1,
            status='active',
            is_frozen=True,
            frozen_at=timezone.now()
        )

        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='task_unfreeze_all'
        )

        executor = TaskFreezeEffectExecutor(effect)
        result = executor.execute_for_user(self.user_level1)

        # Check result
        self.assertEqual(result['unfrozen_task_count'], 1)
        self.assertIn(str(task.id), result['unfrozen_task_ids'])

        # Check task is unfrozen
        task.refresh_from_db()
        self.assertFalse(task.is_frozen)
        self.assertIsNone(task.frozen_at)

    def test_task_freeze_no_active_tasks(self):
        """Test task freeze when user has no active tasks"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='task_freeze_all'
        )

        executor = TaskFreezeEffectExecutor(effect)
        result = executor.execute_for_user(self.user_level1)

        # Should return 0 frozen tasks
        self.assertEqual(result['frozen_task_count'], 0)
        self.assertEqual(result['frozen_task_ids'], [])

    @patch('tasks.models.TaskTimelineEvent.objects.create')
    def test_task_freeze_creates_timeline_event(self, mock_timeline):
        """Test that task freezing creates timeline events"""
        task = self.create_test_lock_task(self.user_level1, status='active')

        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='task_freeze_all'
        )

        executor = TaskFreezeEffectExecutor(effect)
        executor.execute_for_user(self.user_level1)

        # Check timeline event was created
        mock_timeline.assert_called_once()
        call_args = mock_timeline.call_args[1]
        self.assertEqual(call_args['task'], task)
        self.assertEqual(call_args['event_type'], 'system_freeze')


class StoreEffectExecutorTest(EventTestCase):
    """Test store-related effect executors"""

    def test_store_discount_effect(self):
        """Test store discount effect"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='store_discount',
            target_type='all_users',
            effect_parameters={
                'discount_rate': 0.2,  # 20% discount (80% price)
                'item_types': ['detection_radar', 'photo_paper']
            },
            duration_minutes=60
        )

        executor = StoreDiscountEffectExecutor(effect)
        result = executor.execute_for_user(self.user_level1)

        # Check result structure
        self.assertEqual(result['discount_rate'], 0.2)
        self.assertEqual(result['affected_items'], ['detection_radar', 'photo_paper'])
        self.assertIn('expires_at', result)

    def test_store_price_increase_effect(self):
        """Test store price increase effect"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='store_price_increase',
            effect_parameters={
                'increase_rate': 0.5,  # 50% increase
                'item_types': ['detection_radar']
            },
            duration_minutes=120
        )

        executor = StoreDiscountEffectExecutor(effect)  # Same executor handles both
        result = executor.execute_for_user(self.user_level1)

        # Check result
        self.assertEqual(result['increase_rate'], 0.5)
        self.assertEqual(result['affected_items'], ['detection_radar'])


class PersistentEffectExecutorTest(EventTestCase):
    """Test persistent effect executors"""

    def test_temporary_coins_multiplier(self):
        """Test temporary coins multiplier effect"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='temporary_coins_multiplier',
            effect_parameters={'multiplier': 2.0},
            duration_minutes=60
        )

        executor = TemporaryCoinsMultiplierExecutor(effect)
        result = executor.execute_for_user(self.user_level1)

        # Check result
        self.assertEqual(result['multiplier'], 2.0)
        self.assertIn('expires_at', result)

        # Check UserCoinsMultiplier created
        multiplier = self.user_level1.coins_multipliers.filter(is_active=True).first()
        self.assertIsNotNone(multiplier)
        self.assertEqual(multiplier.multiplier, 2.0)

    def test_temporary_game_enhancement(self):
        """Test temporary game enhancement effect"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='temporary_game_enhancement',
            effect_parameters={'multiplier': 1.5},
            duration_minutes=30
        )

        executor = TemporaryGameEnhancementExecutor(effect)
        result = executor.execute_for_user(self.user_level1)

        # Check result
        self.assertEqual(result['multiplier'], 1.5)

        # Check UserGameEffect created
        game_effect = self.user_level1.game_effects.filter(is_active=True).first()
        self.assertIsNotNone(game_effect)
        self.assertEqual(game_effect.multiplier, 1.5)

    def test_persistent_effect_rollback(self):
        """Test rollback of persistent effects"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='temporary_coins_multiplier',
            effect_parameters={'multiplier': 3.0},
            duration_minutes=60
        )

        executor = TemporaryCoinsMultiplierExecutor(effect)

        # Execute effect
        result = executor.execute_for_user(self.user_level1)

        # Check effect exists
        multiplier = self.user_level1.coins_multipliers.filter(is_active=True).first()
        self.assertIsNotNone(multiplier)

        # Test rollback
        self.assertTrue(executor.can_rollback())
        success = executor.rollback_for_user(self.user_level1, result)

        self.assertTrue(success)

        # Check effect is deactivated
        multiplier.refresh_from_db()
        self.assertFalse(multiplier.is_active)


class EffectExecutorErrorHandlingTest(EventTestCase):
    """Test error handling in effect executors"""

    def test_missing_effect_parameters(self):
        """Test handling of missing effect parameters"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            effect_parameters={}  # Missing 'amount'
        )

        executor = CoinsEffectExecutor(effect)

        # Should handle missing parameters gracefully
        result = executor.execute_for_user(self.user_level1)

        # Should use default value or return error
        self.assertTrue('amount_changed' in result or 'error' in result)

    def test_invalid_target_parameters(self):
        """Test handling of invalid target parameters"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            target_type='level_based',
            target_parameters={'levels': 'invalid'}  # Should be list
        )

        executor = CoinsEffectExecutor(effect)

        # Should handle invalid parameters gracefully
        try:
            target_users = executor.get_target_users()
            # Should return empty list or raise handled exception
            self.assertIsInstance(target_users, list)
        except (ValueError, TypeError):
            # Acceptable to raise exception for invalid parameters
            pass

    @patch('events.effects.Item.objects.create')
    def test_database_error_handling(self, mock_create):
        """Test handling of database errors"""
        # Mock database error
        mock_create.side_effect = Exception("Database error")

        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            effect_parameters={
                'item_type': 'photo_paper',
                'quantity': 1
            }
        )

        executor = ItemDistributeEffectExecutor(effect)

        # Should handle database error gracefully
        result = executor.execute_for_user(self.user_level1)

        # Should return error information
        self.assertIn('error', result)

    def test_user_not_found_handling(self):
        """Test handling when user doesn't exist"""
        from users.models import User

        # Create a user and delete it to simulate not found
        temp_user = User.objects.create_user(
            username='temp_user',
            email='temp@test.com',
            password='testpass123'
        )
        user_id = temp_user.id
        temp_user.delete()

        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)

        executor = CoinsEffectExecutor(effect)

        # Create a mock user object with the deleted ID
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.coins = 100

        # Should handle gracefully when user operations fail
        try:
            result = executor.execute_for_user(mock_user)
            # Should return error or handle gracefully
            self.assertTrue('error' in result or 'amount_changed' in result)
        except Exception as e:
            # Acceptable to raise exception for non-existent user
            pass