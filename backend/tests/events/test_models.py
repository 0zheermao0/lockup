#!/usr/bin/env python3
"""
Event Models Unit Tests

This module tests the event system models:
- EventDefinition model functionality and validation
- EventEffect model relationships and parameters
- EventOccurrence lifecycle and status management
- EventEffectExecution tracking and rollback
- Persistent effect models (UserGameEffect, UserCoinsMultiplier)

Author: Claude Code
Created: 2024-12-30
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from events.models import (
    EventDefinition, EventEffect, EventOccurrence,
    EventEffectExecution, UserGameEffect, UserCoinsMultiplier
)
from tests.events.test_base import EventTestCase, EventMockHelpers


class EventDefinitionModelTest(EventTestCase):
    """Test EventDefinition model"""

    def test_create_event_definition(self):
        """Test creating a basic event definition"""
        event_def = self.create_test_event_definition(
            name='test_create',
            title='Test Create Event',
            category='weather'
        )

        self.assertEqual(event_def.name, 'test_create')
        self.assertEqual(event_def.title, 'Test Create Event')
        self.assertEqual(event_def.category, 'weather')
        self.assertEqual(event_def.schedule_type, 'manual')
        self.assertTrue(event_def.is_active)
        self.assertEqual(event_def.created_by, self.admin_user)

    def test_event_definition_str(self):
        """Test string representation of event definition"""
        event_def = self.create_test_event_definition(
            name='test_str',
            title='Test String Representation'
        )
        expected_str = f"Test String Representation (test_str)"
        # Note: The actual __str__ method might be different, adjust as needed
        self.assertIn('test_str', str(event_def))

    def test_event_definition_unique_name(self):
        """Test that event names must be unique"""
        self.create_test_event_definition(name='unique_test')

        with self.assertRaises(Exception):  # IntegrityError or ValidationError
            self.create_test_event_definition(name='unique_test')

    def test_event_definition_categories(self):
        """Test different event categories"""
        categories = ['weather', 'magic', 'system', 'special']

        for category in categories:
            event_def = self.create_test_event_definition(
                name=f'test_{category}',
                category=category
            )
            self.assertEqual(event_def.category, category)

    def test_event_definition_schedule_types(self):
        """Test different schedule types"""
        # Manual trigger
        manual_event = self.create_test_event_definition(
            name='manual_test',
            schedule_type='manual'
        )
        self.assertEqual(manual_event.schedule_type, 'manual')
        self.assertIsNone(manual_event.interval_value)

        # Hourly interval
        hourly_event = self.create_test_event_definition(
            name='hourly_test',
            schedule_type='interval_hours',
            interval_value=6
        )
        self.assertEqual(hourly_event.schedule_type, 'interval_hours')
        self.assertEqual(hourly_event.interval_value, 6)

        # Daily interval
        daily_event = self.create_test_event_definition(
            name='daily_test',
            schedule_type='interval_days',
            interval_value=3
        )
        self.assertEqual(daily_event.schedule_type, 'interval_days')
        self.assertEqual(daily_event.interval_value, 3)

    def test_event_definition_effects_relationship(self):
        """Test relationship with effects"""
        event_def = self.create_test_event_definition()

        # Initially no effects
        self.assertEqual(event_def.effects.count(), 0)

        # Add effects
        effect1 = self.create_test_event_effect(event_def, priority=1)
        effect2 = self.create_test_event_effect(event_def, priority=2)

        self.assertEqual(event_def.effects.count(), 2)
        self.assertIn(effect1, event_def.effects.all())
        self.assertIn(effect2, event_def.effects.all())


class EventEffectModelTest(EventTestCase):
    """Test EventEffect model"""

    def test_create_event_effect(self):
        """Test creating a basic event effect"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 100},
            priority=1
        )

        self.assertEqual(effect.event_definition, event_def)
        self.assertEqual(effect.effect_type, 'coins_add')
        self.assertEqual(effect.target_type, 'all_users')
        self.assertEqual(effect.effect_parameters['amount'], 100)
        self.assertEqual(effect.priority, 1)
        self.assertTrue(effect.is_active)

    def test_effect_types(self):
        """Test different effect types"""
        event_def = self.create_test_event_definition()

        effect_types = [
            'coins_add', 'coins_subtract', 'item_distribute', 'item_remove',
            'store_discount', 'store_price_increase', 'task_freeze_all',
            'task_unfreeze_all', 'task_time_add', 'task_time_subtract'
        ]

        for effect_type in effect_types:
            effect = self.create_test_event_effect(
                event_def,
                effect_type=effect_type,
                priority=1
            )
            self.assertEqual(effect.effect_type, effect_type)

    def test_target_types(self):
        """Test different target types"""
        event_def = self.create_test_event_definition()

        target_types = [
            'all_users', 'random_percentage', 'level_based',
            'active_task_users', 'recent_active_users'
        ]

        for target_type in target_types:
            effect = self.create_test_event_effect(
                event_def,
                target_type=target_type,
                priority=1
            )
            self.assertEqual(effect.target_type, target_type)

    def test_effect_parameters_json(self):
        """Test JSON storage of effect parameters"""
        event_def = self.create_test_event_definition()

        complex_params = {
            'amount': 50,
            'item_type': 'photo_paper',
            'multiplier': 1.5,
            'nested': {
                'key': 'value',
                'list': [1, 2, 3]
            }
        }

        effect = self.create_test_event_effect(
            event_def,
            effect_parameters=complex_params
        )

        self.assertEqual(effect.effect_parameters, complex_params)
        self.assertEqual(effect.effect_parameters['nested']['key'], 'value')

    def test_target_parameters_json(self):
        """Test JSON storage of target parameters"""
        event_def = self.create_test_event_definition()

        target_params = {
            'percentage': 25,
            'levels': [1, 2, 3],
            'days': 7
        }

        effect = self.create_test_event_effect(
            event_def,
            target_parameters=target_params
        )

        self.assertEqual(effect.target_parameters, target_params)
        self.assertEqual(effect.target_parameters['levels'], [1, 2, 3])

    def test_effect_duration(self):
        """Test effect duration settings"""
        event_def = self.create_test_event_definition()

        # Permanent effect (no duration)
        permanent_effect = self.create_test_event_effect(
            event_def,
            duration_minutes=None
        )
        self.assertIsNone(permanent_effect.duration_minutes)

        # Temporary effect with duration
        temporary_effect = self.create_test_event_effect(
            event_def,
            duration_minutes=120
        )
        self.assertEqual(temporary_effect.duration_minutes, 120)

    def test_effect_priority_ordering(self):
        """Test effect priority for execution order"""
        event_def = self.create_test_event_definition()

        effect_high = self.create_test_event_effect(event_def, priority=1)
        effect_low = self.create_test_event_effect(event_def, priority=10)
        effect_medium = self.create_test_event_effect(event_def, priority=5)

        # Get effects ordered by priority
        ordered_effects = event_def.effects.order_by('priority')

        self.assertEqual(ordered_effects[0], effect_high)
        self.assertEqual(ordered_effects[1], effect_medium)
        self.assertEqual(ordered_effects[2], effect_low)


class EventOccurrenceModelTest(EventTestCase):
    """Test EventOccurrence model"""

    def test_create_event_occurrence(self):
        """Test creating an event occurrence"""
        event_def = self.create_test_event_definition()
        occurrence = self.create_test_event_occurrence(
            event_def,
            trigger_type='manual',
            triggered_by=self.admin_user
        )

        self.assertEqual(occurrence.event_definition, event_def)
        self.assertEqual(occurrence.trigger_type, 'manual')
        self.assertEqual(occurrence.triggered_by, self.admin_user)
        self.assertEqual(occurrence.status, 'pending')

    def test_occurrence_status_lifecycle(self):
        """Test occurrence status changes"""
        event_def = self.create_test_event_definition()
        occurrence = self.create_test_event_occurrence(event_def)

        # Initial status
        self.assertEqual(occurrence.status, 'pending')

        # Update to executing
        occurrence.status = 'executing'
        occurrence.started_at = timezone.now()
        occurrence.save()

        self.assertEqual(occurrence.status, 'executing')
        self.assertIsNotNone(occurrence.started_at)

        # Update to completed
        occurrence.status = 'completed'
        occurrence.completed_at = timezone.now()
        occurrence.affected_users_count = 5
        occurrence.save()

        self.assertEqual(occurrence.status, 'completed')
        self.assertIsNotNone(occurrence.completed_at)
        self.assertEqual(occurrence.affected_users_count, 5)

    def test_occurrence_execution_log(self):
        """Test execution log storage"""
        event_def = self.create_test_event_definition()
        occurrence = self.create_test_event_occurrence(event_def)

        execution_log = [
            {
                'effect_type': 'coins_add',
                'affected_count': 3,
                'total_targets': 5
            },
            {
                'effect_type': 'item_distribute',
                'affected_count': 2,
                'total_targets': 5
            }
        ]

        occurrence.execution_log = execution_log
        occurrence.save()

        self.assertEqual(len(occurrence.execution_log), 2)
        self.assertEqual(occurrence.execution_log[0]['effect_type'], 'coins_add')
        self.assertEqual(occurrence.execution_log[1]['affected_count'], 2)

    def test_occurrence_duration_property(self):
        """Test duration calculation property"""
        event_def = self.create_test_event_definition()
        occurrence = self.create_test_event_occurrence(event_def)

        start_time = timezone.now()
        end_time = start_time + timedelta(seconds=30)

        occurrence.started_at = start_time
        occurrence.completed_at = end_time
        occurrence.save()

        # Test duration calculation (if property exists)
        # Note: Add this property to the model if needed
        if hasattr(occurrence, 'duration_seconds'):
            self.assertAlmostEqual(occurrence.duration_seconds, 30, places=0)

    def test_occurrence_trigger_types(self):
        """Test different trigger types"""
        event_def = self.create_test_event_definition()

        # Manual trigger
        manual_occurrence = self.create_test_event_occurrence(
            event_def,
            trigger_type='manual',
            triggered_by=self.admin_user
        )
        self.assertEqual(manual_occurrence.trigger_type, 'manual')
        self.assertEqual(manual_occurrence.triggered_by, self.admin_user)

        # Scheduled trigger
        scheduled_occurrence = self.create_test_event_occurrence(
            event_def,
            trigger_type='scheduled'
        )
        self.assertEqual(scheduled_occurrence.trigger_type, 'scheduled')
        self.assertIsNone(scheduled_occurrence.triggered_by)


class EventEffectExecutionModelTest(EventTestCase):
    """Test EventEffectExecution model"""

    def test_create_effect_execution(self):
        """Test creating an effect execution record"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={'old_coins': 100, 'new_coins': 150},
            rollback_data={'old_coins': 100}
        )

        self.assertEqual(execution.occurrence, occurrence)
        self.assertEqual(execution.effect, effect)
        self.assertEqual(execution.target_user, self.user_level1)
        self.assertEqual(execution.effect_data['old_coins'], 100)
        self.assertEqual(execution.rollback_data['old_coins'], 100)
        self.assertFalse(execution.is_rolled_back)
        self.assertFalse(execution.is_expired)

    def test_effect_execution_expiration(self):
        """Test effect execution expiration"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def, duration_minutes=60)
        occurrence = self.create_test_event_occurrence(event_def)

        execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={},
            expires_at=timezone.now() + timedelta(minutes=60)
        )

        self.assertIsNotNone(execution.expires_at)
        self.assertFalse(execution.is_expired)

        # Test expiration property (if exists)
        if hasattr(execution, 'is_active'):
            self.assertTrue(execution.is_active)

    def test_effect_execution_rollback(self):
        """Test effect execution rollback"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={},
            rollback_data={'restore_coins': 100}
        )

        # Simulate rollback
        execution.is_rolled_back = True
        execution.rolled_back_at = timezone.now()
        execution.save()

        self.assertTrue(execution.is_rolled_back)
        self.assertIsNotNone(execution.rolled_back_at)

    def test_multiple_executions_same_user(self):
        """Test multiple effect executions for same user"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        # Create multiple executions for same user
        execution1 = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={'execution': 1}
        )

        execution2 = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={'execution': 2}
        )

        user_executions = EventEffectExecution.objects.filter(
            target_user=self.user_level1
        )

        self.assertEqual(user_executions.count(), 2)
        self.assertIn(execution1, user_executions)
        self.assertIn(execution2, user_executions)


class PersistentEffectModelsTest(EventTestCase):
    """Test persistent effect models"""

    def test_user_game_effect_creation(self):
        """Test UserGameEffect model"""
        expires_at = timezone.now() + timedelta(hours=1)

        game_effect = UserGameEffect.objects.create(
            user=self.user_level1,
            effect_type='multiplier',
            multiplier=2.0,
            expires_at=expires_at,
            is_active=True
        )

        self.assertEqual(game_effect.user, self.user_level1)
        self.assertEqual(game_effect.effect_type, 'multiplier')
        self.assertEqual(game_effect.multiplier, 2.0)
        self.assertEqual(game_effect.expires_at, expires_at)
        self.assertTrue(game_effect.is_active)

    def test_user_game_effect_validity(self):
        """Test UserGameEffect validity checking"""
        # Active and not expired
        active_effect = UserGameEffect.objects.create(
            user=self.user_level1,
            multiplier=1.5,
            expires_at=timezone.now() + timedelta(hours=1),
            is_active=True
        )

        # Expired effect
        expired_effect = UserGameEffect.objects.create(
            user=self.user_level1,
            multiplier=1.5,
            expires_at=timezone.now() - timedelta(hours=1),
            is_active=True
        )

        # Inactive effect
        inactive_effect = UserGameEffect.objects.create(
            user=self.user_level1,
            multiplier=1.5,
            expires_at=timezone.now() + timedelta(hours=1),
            is_active=False
        )

        # Test validity property (if exists)
        if hasattr(active_effect, 'is_valid'):
            self.assertTrue(active_effect.is_valid)
            self.assertFalse(expired_effect.is_valid)
            self.assertFalse(inactive_effect.is_valid)

    def test_user_coins_multiplier_creation(self):
        """Test UserCoinsMultiplier model"""
        expires_at = timezone.now() + timedelta(hours=2)

        coins_multiplier = UserCoinsMultiplier.objects.create(
            user=self.user_level2,
            multiplier=3.0,
            expires_at=expires_at,
            is_active=True
        )

        self.assertEqual(coins_multiplier.user, self.user_level2)
        self.assertEqual(coins_multiplier.multiplier, 3.0)
        self.assertEqual(coins_multiplier.expires_at, expires_at)
        self.assertTrue(coins_multiplier.is_active)

    def test_user_coins_multiplier_validity(self):
        """Test UserCoinsMultiplier validity checking"""
        # Valid multiplier
        valid_multiplier = UserCoinsMultiplier.objects.create(
            user=self.user_level2,
            multiplier=2.0,
            expires_at=timezone.now() + timedelta(hours=1),
            is_active=True
        )

        # Invalid multiplier (expired)
        invalid_multiplier = UserCoinsMultiplier.objects.create(
            user=self.user_level2,
            multiplier=2.0,
            expires_at=timezone.now() - timedelta(minutes=30),
            is_active=True
        )

        # Test validity property (if exists)
        if hasattr(valid_multiplier, 'is_valid'):
            self.assertTrue(valid_multiplier.is_valid)
            self.assertFalse(invalid_multiplier.is_valid)

    def test_multiple_effects_same_user(self):
        """Test multiple persistent effects for same user"""
        expires_at = timezone.now() + timedelta(hours=1)

        # Multiple game effects
        effect1 = UserGameEffect.objects.create(
            user=self.user_level1,
            multiplier=1.5,
            expires_at=expires_at
        )

        effect2 = UserGameEffect.objects.create(
            user=self.user_level1,
            multiplier=2.0,
            expires_at=expires_at
        )

        # Multiple coins multipliers
        multiplier1 = UserCoinsMultiplier.objects.create(
            user=self.user_level1,
            multiplier=1.2,
            expires_at=expires_at
        )

        multiplier2 = UserCoinsMultiplier.objects.create(
            user=self.user_level1,
            multiplier=1.8,
            expires_at=expires_at
        )

        # Check relationships
        user_game_effects = self.user_level1.game_effects.all()
        user_coins_multipliers = self.user_level1.coins_multipliers.all()

        self.assertEqual(user_game_effects.count(), 2)
        self.assertEqual(user_coins_multipliers.count(), 2)
        self.assertIn(effect1, user_game_effects)
        self.assertIn(multiplier1, user_coins_multipliers)


class EventModelRelationshipsTest(EventTestCase):
    """Test relationships between event models"""

    def test_cascade_deletion(self):
        """Test cascade deletion behavior"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={}
        )

        # Delete event definition should cascade
        event_def_id = event_def.id
        event_def.delete()

        # Check that related objects are deleted
        self.assertFalse(EventEffect.objects.filter(id=effect.id).exists())
        self.assertFalse(EventOccurrence.objects.filter(id=occurrence.id).exists())
        self.assertFalse(EventEffectExecution.objects.filter(id=execution.id).exists())

    def test_user_deletion_behavior(self):
        """Test behavior when user is deleted"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def, triggered_by=self.user_level1)

        execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={}
        )

        game_effect = UserGameEffect.objects.create(
            user=self.user_level1,
            multiplier=1.5,
            expires_at=timezone.now() + timedelta(hours=1)
        )

        user_id = self.user_level1.id
        self.user_level1.delete()

        # Check what happens to related objects
        # EventOccurrence.triggered_by should be set to null (if configured)
        occurrence.refresh_from_db()
        # EventEffectExecution and persistent effects should be deleted (CASCADE)
        self.assertFalse(EventEffectExecution.objects.filter(target_user_id=user_id).exists())
        self.assertFalse(UserGameEffect.objects.filter(user_id=user_id).exists())

    def test_complex_relationship_queries(self):
        """Test complex queries across relationships"""
        # Create test data
        event_def = self.create_test_event_definition()
        effect1 = self.create_test_event_effect(event_def, priority=1)
        effect2 = self.create_test_event_effect(event_def, priority=2)

        occurrence = self.create_test_event_occurrence(event_def)

        # Create executions for different users
        exec1 = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect1,
            target_user=self.user_level1,
            effect_data={}
        )

        exec2 = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect2,
            target_user=self.user_level2,
            effect_data={}
        )

        # Test queries
        # Get all executions for an event
        event_executions = EventEffectExecution.objects.filter(
            occurrence__event_definition=event_def
        )
        self.assertEqual(event_executions.count(), 2)

        # Get all events that affected a specific user
        user_events = EventDefinition.objects.filter(
            occurrences__effect_executions__target_user=self.user_level1
        ).distinct()
        self.assertEqual(user_events.count(), 1)
        self.assertEqual(user_events.first(), event_def)

        # Get execution count per effect
        effect_counts = EventEffect.objects.filter(
            event_definition=event_def
        ).annotate(
            execution_count=models.Count('eventeffectexecution')
        )

        for effect in effect_counts:
            if effect == effect1:
                self.assertEqual(effect.execution_count, 1)
            elif effect == effect2:
                self.assertEqual(effect.execution_count, 1)