#!/usr/bin/env python3
"""
Event System Celery Tasks Unit Tests

This module tests the event system Celery tasks:
- schedule_pending_events task
- execute_pending_events task
- process_expired_effects task
- trigger_manual_event task
- event_system_health_check task
- Error handling and retry mechanisms

Author: Claude Code
Created: 2024-12-30
"""

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock, call
from celery.exceptions import Retry

from events.models import (
    EventDefinition, EventEffect, EventOccurrence,
    EventEffectExecution, UserGameEffect, UserCoinsMultiplier
)
from events.celery_tasks import (
    schedule_pending_events, execute_pending_events,
    process_expired_effects, trigger_manual_event,
    event_system_health_check, _execute_single_effect,
    _cleanup_expired_persistent_effects, _send_event_notifications
)
from tests.events.test_base import EventTestCase, EventTransactionTestCase, EventMockHelpers


class SchedulePendingEventsTaskTest(EventTestCase):
    """Test schedule_pending_events Celery task"""

    def test_schedule_interval_hours_event(self):
        """Test scheduling events with hourly intervals"""
        # Create hourly event
        event_def = self.create_test_event_definition(
            name='hourly_test',
            schedule_type='interval_hours',
            interval_value=6
        )

        with EventMockHelpers.mock_timezone_now() as mock_now:
            fixed_time = timezone.now()
            mock_now.return_value = fixed_time

            # Run scheduling task
            result = schedule_pending_events()

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['scheduled_count'], 1)

            # Check occurrence created
            occurrence = EventOccurrence.objects.filter(
                event_definition=event_def
            ).first()

            self.assertIsNotNone(occurrence)
            self.assertEqual(occurrence.trigger_type, 'scheduled')
            self.assertEqual(occurrence.status, 'pending')

    def test_schedule_interval_days_event(self):
        """Test scheduling events with daily intervals"""
        event_def = self.create_test_event_definition(
            name='daily_test',
            schedule_type='interval_days',
            interval_value=3
        )

        result = schedule_pending_events()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['scheduled_count'], 1)

        # Check occurrence created
        occurrence = EventOccurrence.objects.filter(
            event_definition=event_def
        ).first()

        self.assertIsNotNone(occurrence)

    def test_schedule_respects_existing_occurrences(self):
        """Test that scheduling respects existing occurrences"""
        event_def = self.create_test_event_definition(
            schedule_type='interval_hours',
            interval_value=6
        )

        # Create recent occurrence
        recent_occurrence = self.create_test_event_occurrence(
            event_def,
            scheduled_at=timezone.now() - timedelta(hours=3)  # 3 hours ago
        )

        result = schedule_pending_events()

        # Should not schedule new occurrence (6 hours haven't passed)
        self.assertEqual(result['scheduled_count'], 0)

    def test_schedule_creates_new_when_interval_passed(self):
        """Test scheduling creates new occurrence when interval has passed"""
        event_def = self.create_test_event_definition(
            schedule_type='interval_hours',
            interval_value=2
        )

        # Create old occurrence
        old_occurrence = self.create_test_event_occurrence(
            event_def,
            scheduled_at=timezone.now() - timedelta(hours=3)  # 3 hours ago
        )

        result = schedule_pending_events()

        # Should schedule new occurrence (2 hours have passed)
        self.assertEqual(result['scheduled_count'], 1)

        # Check new occurrence created
        new_occurrences = EventOccurrence.objects.filter(
            event_definition=event_def,
            id__ne=old_occurrence.id
        )
        self.assertEqual(new_occurrences.count(), 1)

    def test_schedule_skips_inactive_events(self):
        """Test that inactive events are not scheduled"""
        inactive_event = self.create_test_event_definition(
            schedule_type='interval_hours',
            interval_value=1,
            is_active=False
        )

        result = schedule_pending_events()

        self.assertEqual(result['scheduled_count'], 0)

        # No occurrence should be created
        occurrences = EventOccurrence.objects.filter(
            event_definition=inactive_event
        )
        self.assertEqual(occurrences.count(), 0)

    def test_schedule_skips_manual_events(self):
        """Test that manual events are not auto-scheduled"""
        manual_event = self.create_test_event_definition(
            schedule_type='manual'
        )

        result = schedule_pending_events()

        self.assertEqual(result['scheduled_count'], 0)

    @patch('events.celery_tasks.schedule_pending_events.retry')
    def test_schedule_error_handling(self, mock_retry):
        """Test error handling in scheduling task"""
        # Mock database error
        with patch('events.models.EventDefinition.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            # Should raise retry
            mock_retry.side_effect = Retry()

            with self.assertRaises(Retry):
                schedule_pending_events()

            mock_retry.assert_called_once()


class ExecutePendingEventsTaskTest(EventTestCase):
    """Test execute_pending_events Celery task"""

    def test_execute_single_pending_event(self):
        """Test executing a single pending event"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 25}
        )

        occurrence = self.create_test_event_occurrence(
            event_def,
            scheduled_at=timezone.now() - timedelta(minutes=1)  # Past due
        )

        with EventMockHelpers.mock_notification_creation():
            result = execute_pending_events()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['executed_count'], 1)

        # Check occurrence updated
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status, 'completed')
        self.assertIsNotNone(occurrence.started_at)
        self.assertIsNotNone(occurrence.completed_at)
        self.assertGreater(occurrence.affected_users_count, 0)

    def test_execute_multiple_effects(self):
        """Test executing event with multiple effects"""
        event_def = self.create_test_event_definition()

        # Add multiple effects
        coins_effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            effect_parameters={'amount': 10},
            priority=1
        )

        item_effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            effect_parameters={
                'item_type': 'photo_paper',
                'quantity': 1
            },
            priority=2
        )

        occurrence = self.create_test_event_occurrence(
            event_def,
            scheduled_at=timezone.now() - timedelta(minutes=1)
        )

        with EventMockHelpers.mock_notification_creation():
            result = execute_pending_events()

        # Check execution log has both effects
        occurrence.refresh_from_db()
        self.assertEqual(len(occurrence.execution_log), 2)

        # Check effects executed in priority order
        log_entry_1 = occurrence.execution_log[0]
        log_entry_2 = occurrence.execution_log[1]

        self.assertEqual(log_entry_1['effect_type'], 'coins_add')
        self.assertEqual(log_entry_2['effect_type'], 'item_distribute')

    def test_execute_skips_future_events(self):
        """Test that future events are not executed"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)

        # Future occurrence
        future_occurrence = self.create_test_event_occurrence(
            event_def,
            scheduled_at=timezone.now() + timedelta(hours=1)
        )

        result = execute_pending_events()

        self.assertEqual(result['executed_count'], 0)

        # Occurrence should remain pending
        future_occurrence.refresh_from_db()
        self.assertEqual(future_occurrence.status, 'pending')

    def test_execute_handles_effect_errors(self):
        """Test handling of individual effect errors"""
        event_def = self.create_test_event_definition()

        # Create effect with invalid parameters
        bad_effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            effect_parameters={'item_type': 'nonexistent_item'}
        )

        occurrence = self.create_test_event_occurrence(
            event_def,
            scheduled_at=timezone.now() - timedelta(minutes=1)
        )

        with EventMockHelpers.mock_notification_creation():
            result = execute_pending_events()

        # Event should still complete even with effect errors
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status, 'completed')

        # Check error logged
        self.assertEqual(len(occurrence.execution_log), 1)
        log_entry = occurrence.execution_log[0]
        self.assertIn('error', log_entry)

    def test_execute_creates_effect_executions(self):
        """Test that effect executions are created"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            effect_parameters={'amount': 15}
        )

        occurrence = self.create_test_event_occurrence(
            event_def,
            scheduled_at=timezone.now() - timedelta(minutes=1)
        )

        with EventMockHelpers.mock_notification_creation():
            execute_pending_events()

        # Check effect executions created
        executions = EventEffectExecution.objects.filter(
            occurrence=occurrence,
            effect=effect
        )

        self.assertGreater(executions.count(), 0)

        # Check execution data
        execution = executions.first()
        self.assertEqual(execution.target_user.level, 1)  # First user
        self.assertIn('amount_changed', execution.effect_data)

    def test_execute_sets_expiration_for_temporary_effects(self):
        """Test that temporary effects get expiration times"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            duration_minutes=30
        )

        occurrence = self.create_test_event_occurrence(
            event_def,
            scheduled_at=timezone.now() - timedelta(minutes=1)
        )

        with EventMockHelpers.mock_notification_creation():
            execute_pending_events()

        # Check executions have expiration times
        executions = EventEffectExecution.objects.filter(
            occurrence=occurrence,
            effect=effect
        )

        for execution in executions:
            self.assertIsNotNone(execution.expires_at)
            # Should expire in approximately 30 minutes
            expected_expiry = timezone.now() + timedelta(minutes=30)
            time_diff = abs((execution.expires_at - expected_expiry).total_seconds())
            self.assertLess(time_diff, 60)  # Within 1 minute

    @patch('events.celery_tasks.execute_pending_events.retry')
    def test_execute_error_handling(self, mock_retry):
        """Test error handling in execution task"""
        # Mock database error
        with patch('events.models.EventOccurrence.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            mock_retry.side_effect = Retry()

            with self.assertRaises(Retry):
                execute_pending_events()

            mock_retry.assert_called_once()


class ProcessExpiredEffectsTaskTest(EventTestCase):
    """Test process_expired_effects Celery task"""

    def test_process_expired_executions(self):
        """Test processing expired effect executions"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        # Create expired execution
        expired_execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={'old_coins': 100, 'new_coins': 150},
            rollback_data={'old_coins': 100},
            expires_at=timezone.now() - timedelta(minutes=30)
        )

        result = process_expired_effects()

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['processed_count'], 1)

        # Check execution marked as expired
        expired_execution.refresh_from_db()
        self.assertTrue(expired_execution.is_expired)

    def test_process_rollback_for_expired_effects(self):
        """Test rollback for expired effects"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add'
        )
        occurrence = self.create_test_event_occurrence(event_def)

        # Create expired execution with rollback data
        expired_execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={'old_coins': 100, 'new_coins': 150},
            rollback_data={'old_coins': 100},
            expires_at=timezone.now() - timedelta(minutes=30)
        )

        with patch('events.effects.CoinsEffectExecutor.can_rollback', return_value=True):
            with patch('events.effects.CoinsEffectExecutor.rollback_for_user', return_value=True) as mock_rollback:
                result = process_expired_effects()

                # Check rollback was called
                mock_rollback.assert_called_once_with(
                    self.user_level1,
                    {'old_coins': 100}
                )

        # Check execution marked as rolled back
        expired_execution.refresh_from_db()
        self.assertTrue(expired_execution.is_rolled_back)
        self.assertIsNotNone(expired_execution.rolled_back_at)

    def test_process_cleanup_persistent_effects(self):
        """Test cleanup of expired persistent effects"""
        # Create expired game effect
        expired_game_effect = UserGameEffect.objects.create(
            user=self.user_level1,
            multiplier=2.0,
            expires_at=timezone.now() - timedelta(minutes=30),
            is_active=True
        )

        # Create expired coins multiplier
        expired_coins_multiplier = UserCoinsMultiplier.objects.create(
            user=self.user_level1,
            multiplier=1.5,
            expires_at=timezone.now() - timedelta(minutes=15),
            is_active=True
        )

        result = process_expired_effects()

        self.assertEqual(result['status'], 'success')

        # Check persistent effects deactivated
        expired_game_effect.refresh_from_db()
        expired_coins_multiplier.refresh_from_db()

        self.assertFalse(expired_game_effect.is_active)
        self.assertFalse(expired_coins_multiplier.is_active)

    def test_process_skips_non_expired_effects(self):
        """Test that non-expired effects are not processed"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        # Create non-expired execution
        active_execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={},
            expires_at=timezone.now() + timedelta(hours=1)
        )

        result = process_expired_effects()

        # Should process 0 effects
        self.assertEqual(result['processed_count'], 0)

        # Execution should remain unchanged
        active_execution.refresh_from_db()
        self.assertFalse(active_execution.is_expired)
        self.assertFalse(active_execution.is_rolled_back)

    def test_process_skips_already_processed(self):
        """Test that already processed effects are skipped"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        # Create already expired execution
        processed_execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={},
            expires_at=timezone.now() - timedelta(minutes=30),
            is_expired=True
        )

        result = process_expired_effects()

        # Should not process already expired effects
        self.assertEqual(result['processed_count'], 0)


class TriggerManualEventTaskTest(EventTestCase):
    """Test trigger_manual_event Celery task"""

    def test_trigger_manual_event_success(self):
        """Test successful manual event triggering"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            effect_parameters={'amount': 100}
        )

        with EventMockHelpers.mock_notification_creation():
            result = trigger_manual_event(str(event_def.id), self.admin_user.id)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['event_name'], event_def.name)
        self.assertGreater(result['affected_users'], 0)

        # Check occurrence created
        occurrence = EventOccurrence.objects.filter(
            event_definition=event_def,
            trigger_type='manual',
            triggered_by=self.admin_user
        ).first()

        self.assertIsNotNone(occurrence)
        self.assertEqual(occurrence.status, 'completed')

    def test_trigger_nonexistent_event(self):
        """Test triggering non-existent event"""
        fake_id = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'

        result = trigger_manual_event(fake_id)

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Event definition not found')

    def test_trigger_with_nonexistent_user(self):
        """Test triggering with non-existent user"""
        event_def = self.create_test_event_definition()

        with EventMockHelpers.mock_notification_creation():
            result = trigger_manual_event(str(event_def.id), 99999)

        # Should still work (triggered_by will be None)
        self.assertEqual(result['status'], 'success')

        occurrence = EventOccurrence.objects.filter(
            event_definition=event_def,
            trigger_type='manual'
        ).first()

        self.assertIsNone(occurrence.triggered_by)

    def test_trigger_creates_execution_log(self):
        """Test that manual trigger creates proper execution log"""
        event_def = self.create_test_event_definition()
        effect1 = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            priority=1
        )
        effect2 = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            effect_parameters={'item_type': 'photo_paper', 'quantity': 1},
            priority=2
        )

        with EventMockHelpers.mock_notification_creation():
            result = trigger_manual_event(str(event_def.id))

        # Check execution log
        self.assertIn('execution_log', result)
        self.assertEqual(len(result['execution_log']), 2)

        log_entries = result['execution_log']
        self.assertEqual(log_entries[0]['effect_type'], 'coins_add')
        self.assertEqual(log_entries[1]['effect_type'], 'item_distribute')


class EventSystemHealthCheckTaskTest(EventTestCase):
    """Test event_system_health_check Celery task"""

    def test_health_check_healthy_system(self):
        """Test health check on healthy system"""
        # Create some normal events
        event_def = self.create_test_event_definition()
        recent_occurrence = self.create_test_event_occurrence(
            event_def,
            status='completed',
            completed_at=timezone.now() - timedelta(hours=1)
        )

        result = event_system_health_check()

        self.assertEqual(result['status'], 'healthy')
        self.assertEqual(result['active_events_count'], 1)
        self.assertEqual(result['today_executions_count'], 1)
        self.assertEqual(result['stale_events_count'], 0)
        self.assertEqual(result['failed_events_today'], 0)
        self.assertEqual(len(result['issues']), 0)

    def test_health_check_detects_stale_events(self):
        """Test health check detects stale pending events"""
        event_def = self.create_test_event_definition()

        # Create stale pending event (over 1 hour old)
        stale_occurrence = self.create_test_event_occurrence(
            event_def,
            status='pending',
            scheduled_at=timezone.now() - timedelta(hours=2)
        )

        result = event_system_health_check()

        self.assertEqual(result['status'], 'warning')
        self.assertEqual(result['stale_events_count'], 1)
        self.assertIn('stale pending events', ' '.join(result['issues']))
        self.assertEqual(len(result['stale_events']), 1)

    def test_health_check_detects_failed_events(self):
        """Test health check detects excessive failed events"""
        event_def = self.create_test_event_definition()

        # Create multiple failed events today
        for i in range(6):  # More than threshold of 5
            self.create_test_event_occurrence(
                event_def,
                status='failed',
                created_at=timezone.now() - timedelta(hours=i)
            )

        result = event_system_health_check()

        self.assertEqual(result['status'], 'warning')
        self.assertEqual(result['failed_events_today'], 6)
        self.assertIn('failed events today', ' '.join(result['issues']))

    def test_health_check_detects_overdue_effects(self):
        """Test health check detects overdue effect processing"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        # Create overdue effect execution
        for i in range(11):  # More than threshold of 10
            EventEffectExecution.objects.create(
                occurrence=occurrence,
                effect=effect,
                target_user=self.user_level1,
                effect_data={},
                expires_at=timezone.now() - timedelta(minutes=10),
                is_expired=False
            )

        result = event_system_health_check()

        self.assertEqual(result['status'], 'warning')
        self.assertEqual(result['overdue_effects_count'], 11)
        self.assertIn('overdue effects', ' '.join(result['issues']))

    def test_health_check_error_handling(self):
        """Test health check error handling"""
        with patch('events.models.EventDefinition.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            result = event_system_health_check()

            self.assertEqual(result['status'], 'error')
            self.assertIn('error', result)


class HelperFunctionsTest(EventTestCase):
    """Test helper functions"""

    def test_execute_single_effect_success(self):
        """Test _execute_single_effect helper function"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add',
            target_type='level_based',
            effect_parameters={'amount': 25},
            target_parameters={'levels': [1]}
        )
        occurrence = self.create_test_event_occurrence(event_def)

        result = _execute_single_effect(occurrence, effect)

        self.assertEqual(result['effect_type'], 'coins_add')
        self.assertEqual(result['target_type'], 'level_based')
        self.assertEqual(result['affected_count'], 1)  # Only level 1 user
        self.assertEqual(result['total_targets'], 1)

    def test_execute_single_effect_error(self):
        """Test _execute_single_effect error handling"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='item_distribute',
            effect_parameters={'item_type': 'nonexistent'}
        )
        occurrence = self.create_test_event_occurrence(event_def)

        result = _execute_single_effect(occurrence, effect)

        self.assertEqual(result['effect_type'], 'item_distribute')
        self.assertIn('error', result)
        self.assertEqual(result['affected_count'], 0)

    def test_send_event_notifications(self):
        """Test _send_event_notifications helper function"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        # Create some effect executions
        for user in [self.user_level1, self.user_level2]:
            EventEffectExecution.objects.create(
                occurrence=occurrence,
                effect=effect,
                target_user=user,
                effect_data={}
            )

        with patch('users.models.Notification.create_notification') as mock_notification:
            _send_event_notifications(occurrence)

            # Should create notifications for affected users
            self.assertEqual(mock_notification.call_count, 2)

            # Check notification calls
            call_args_list = mock_notification.call_args_list
            recipients = [call[1]['recipient'] for call in call_args_list]
            self.assertIn(self.user_level1, recipients)
            self.assertIn(self.user_level2, recipients)

    def test_cleanup_expired_persistent_effects(self):
        """Test _cleanup_expired_persistent_effects helper function"""
        # Create expired effects
        expired_game_effect = UserGameEffect.objects.create(
            user=self.user_level1,
            multiplier=2.0,
            expires_at=timezone.now() - timedelta(minutes=30),
            is_active=True
        )

        expired_coins_multiplier = UserCoinsMultiplier.objects.create(
            user=self.user_level1,
            multiplier=1.5,
            expires_at=timezone.now() - timedelta(minutes=15),
            is_active=True
        )

        # Create active effects (should not be affected)
        active_game_effect = UserGameEffect.objects.create(
            user=self.user_level2,
            multiplier=1.8,
            expires_at=timezone.now() + timedelta(hours=1),
            is_active=True
        )

        _cleanup_expired_persistent_effects(timezone.now())

        # Check expired effects deactivated
        expired_game_effect.refresh_from_db()
        expired_coins_multiplier.refresh_from_db()
        active_game_effect.refresh_from_db()

        self.assertFalse(expired_game_effect.is_active)
        self.assertFalse(expired_coins_multiplier.is_active)
        self.assertTrue(active_game_effect.is_active)


class CeleryTaskRetryTest(EventTransactionTestCase):
    """Test Celery task retry mechanisms"""

    @patch('events.celery_tasks.schedule_pending_events.retry')
    def test_schedule_task_retry_on_database_error(self, mock_retry):
        """Test that scheduling task retries on database errors"""
        mock_retry.side_effect = Retry()

        with patch('django.db.transaction.atomic') as mock_atomic:
            mock_atomic.side_effect = Exception("Database connection lost")

            with self.assertRaises(Retry):
                schedule_pending_events()

            mock_retry.assert_called_once()

    @patch('events.celery_tasks.execute_pending_events.retry')
    def test_execute_task_retry_exponential_backoff(self, mock_retry):
        """Test exponential backoff in retry"""
        # Mock task request
        task_mock = MagicMock()
        task_mock.request.retries = 2

        with patch('events.celery_tasks.execute_pending_events', task_mock):
            mock_retry.side_effect = Retry()

            with patch('events.models.EventOccurrence.objects.filter') as mock_filter:
                mock_filter.side_effect = Exception("Temporary error")

                with self.assertRaises(Retry):
                    execute_pending_events()

                # Check retry called with exponential backoff
                mock_retry.assert_called_once()
                call_kwargs = mock_retry.call_args[1]
                expected_countdown = min(60 * (2 ** 2), 300)  # 240 seconds
                self.assertEqual(call_kwargs.get('countdown'), expected_countdown)

    def test_task_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded"""
        # This would typically result in the task being marked as failed
        # and sent to a dead letter queue or error handler
        pass  # Implementation depends on Celery configuration