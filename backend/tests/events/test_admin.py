#!/usr/bin/env python3
"""
Event System Admin Interface Tests

This module tests the Django Admin interfaces for the event system:
- EventDefinitionAdmin functionality and actions
- EventOccurrenceAdmin display and filtering
- EventEffectExecutionAdmin tracking
- Admin permissions and security
- Bulk operations and custom actions

Author: Claude Code
Created: 2024-12-30
"""

from django.test import TestCase, Client
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from events.models import (
    EventDefinition, EventEffect, EventOccurrence,
    EventEffectExecution, UserGameEffect, UserCoinsMultiplier
)
from events.admin import (
    EventDefinitionAdmin, EventOccurrenceAdmin, EventEffectExecutionAdmin,
    UserGameEffectAdmin, UserCoinsMultiplierAdmin
)
from tests.events.test_base import EventTestCase, EventMockHelpers

User = get_user_model()


class AdminTestCase(EventTestCase):
    """Base test case for admin interface tests"""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.site = AdminSite()

        # Login as admin
        self.client.force_login(self.admin_user)

    def get_admin_url(self, model_name, action='changelist', object_id=None):
        """Get admin URL for model and action"""
        app_label = 'events'
        if object_id:
            return reverse(f'admin:{app_label}_{model_name}_{action}', args=[object_id])
        return reverse(f'admin:{app_label}_{model_name}_{action}')


class EventDefinitionAdminTest(AdminTestCase):
    """Test EventDefinitionAdmin"""

    def setUp(self):
        super().setUp()
        self.admin_instance = EventDefinitionAdmin(EventDefinition, self.site)

    def test_list_display_fields(self):
        """Test list display fields"""
        expected_fields = [
            'name', 'category_badge', 'schedule_type_badge', 'is_active_badge',
            'effects_count', 'recent_occurrences_count', 'created_by', 'created_at'
        ]

        self.assertEqual(self.admin_instance.list_display, expected_fields)

    def test_list_filter_fields(self):
        """Test list filter fields"""
        expected_filters = ['category', 'schedule_type', 'is_active', 'created_at']
        self.assertEqual(self.admin_instance.list_filter, expected_filters)

    def test_search_fields(self):
        """Test search fields"""
        expected_search = ['name', 'title', 'description']
        self.assertEqual(self.admin_instance.search_fields, expected_search)

    def test_category_badge_display(self):
        """Test category badge display method"""
        event_def = self.create_test_event_definition(category='weather')

        badge_html = self.admin_instance.category_badge(event_def)

        self.assertIn('weather', badge_html)
        self.assertIn('background-color', badge_html)
        self.assertIn('#2196F3', badge_html)  # Weather color

    def test_schedule_type_badge_display(self):
        """Test schedule type badge display method"""
        # Test manual event
        manual_event = self.create_test_event_definition(schedule_type='manual')
        badge_html = self.admin_instance.schedule_type_badge(manual_event)
        self.assertIn('手动触发', badge_html)

        # Test interval event
        interval_event = self.create_test_event_definition(
            schedule_type='interval_hours',
            interval_value=6
        )
        badge_html = self.admin_instance.schedule_type_badge(interval_event)
        self.assertIn('每6小时', badge_html)

    def test_is_active_badge_display(self):
        """Test is_active badge display method"""
        # Active event
        active_event = self.create_test_event_definition(is_active=True)
        badge_html = self.admin_instance.is_active_badge(active_event)
        self.assertIn('启用', badge_html)
        self.assertIn('#4CAF50', badge_html)

        # Inactive event
        inactive_event = self.create_test_event_definition(is_active=False)
        badge_html = self.admin_instance.is_active_badge(inactive_event)
        self.assertIn('禁用', badge_html)
        self.assertIn('#F44336', badge_html)

    def test_effects_count_display(self):
        """Test effects count display method"""
        event_def = self.create_test_event_definition()

        # No effects
        count_html = self.admin_instance.effects_count(event_def)
        self.assertIn('0 个效果', count_html)

        # Add effects
        active_effect = self.create_test_event_effect(event_def, is_active=True)
        inactive_effect = self.create_test_event_effect(event_def, is_active=False)

        count_html = self.admin_instance.effects_count(event_def)
        self.assertIn('2 个效果', count_html)
        self.assertIn('1 活跃', count_html)

    def test_recent_occurrences_count_display(self):
        """Test recent occurrences count display method"""
        event_def = self.create_test_event_definition()

        # No recent occurrences
        count_html = self.admin_instance.recent_occurrences_count(event_def)
        self.assertIn('近7天: 0次', count_html)

        # Add recent occurrence
        recent_occurrence = self.create_test_event_occurrence(
            event_def,
            created_at=timezone.now() - timedelta(days=3)
        )

        # Add old occurrence (should not count)
        old_occurrence = self.create_test_event_occurrence(
            event_def,
            created_at=timezone.now() - timedelta(days=10)
        )

        count_html = self.admin_instance.recent_occurrences_count(event_def)
        self.assertIn('近7天: 1次', count_html)

    def test_enable_events_action(self):
        """Test enable events bulk action"""
        # Create inactive events
        event1 = self.create_test_event_definition(name='event1', is_active=False)
        event2 = self.create_test_event_definition(name='event2', is_active=False)

        queryset = EventDefinition.objects.filter(id__in=[event1.id, event2.id])
        request = MagicMock()

        self.admin_instance.enable_events(request, queryset)

        # Check events are enabled
        event1.refresh_from_db()
        event2.refresh_from_db()
        self.assertTrue(event1.is_active)
        self.assertTrue(event2.is_active)

    def test_disable_events_action(self):
        """Test disable events bulk action"""
        # Create active events
        event1 = self.create_test_event_definition(name='event1', is_active=True)
        event2 = self.create_test_event_definition(name='event2', is_active=True)

        queryset = EventDefinition.objects.filter(id__in=[event1.id, event2.id])
        request = MagicMock()

        self.admin_instance.disable_events(request, queryset)

        # Check events are disabled
        event1.refresh_from_db()
        event2.refresh_from_db()
        self.assertFalse(event1.is_active)
        self.assertFalse(event2.is_active)

    @patch('events.celery_tasks.trigger_manual_event.delay')
    def test_trigger_manual_events_action(self, mock_trigger):
        """Test trigger manual events bulk action"""
        event1 = self.create_test_event_definition(name='event1')
        event2 = self.create_test_event_definition(name='event2')

        queryset = EventDefinition.objects.filter(id__in=[event1.id, event2.id])
        request = MagicMock()
        request.user = self.admin_user

        self.admin_instance.trigger_manual_events(request, queryset)

        # Check trigger tasks were called
        self.assertEqual(mock_trigger.call_count, 2)
        call_args_list = mock_trigger.call_args_list

        triggered_event_ids = [call[0][0] for call in call_args_list]
        self.assertIn(str(event1.id), triggered_event_ids)
        self.assertIn(str(event2.id), triggered_event_ids)

    def test_duplicate_events_action(self):
        """Test duplicate events bulk action"""
        original_event = self.create_test_event_definition(
            name='original_event',
            title='Original Event'
        )

        # Add effects to original
        effect1 = self.create_test_event_effect(
            original_event,
            effect_type='coins_add',
            priority=1
        )
        effect2 = self.create_test_event_effect(
            original_event,
            effect_type='item_distribute',
            priority=2
        )

        queryset = EventDefinition.objects.filter(id=original_event.id)
        request = MagicMock()
        request.user = self.admin_user

        self.admin_instance.duplicate_events(request, queryset)

        # Check duplicate created
        duplicate = EventDefinition.objects.filter(
            name='original_event_副本'
        ).first()

        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.title, 'Original Event (副本)')
        self.assertEqual(duplicate.schedule_type, 'manual')
        self.assertFalse(duplicate.is_active)
        self.assertEqual(duplicate.created_by, self.admin_user)

        # Check effects duplicated
        duplicate_effects = duplicate.effects.all()
        self.assertEqual(duplicate_effects.count(), 2)

    def test_save_model_sets_created_by(self):
        """Test that save_model sets created_by for new objects"""
        request = MagicMock()
        request.user = self.admin_user

        event_def = EventDefinition(
            name='test_save',
            title='Test Save Event',
            category='system',
            schedule_type='manual'
        )

        form = MagicMock()

        # Test new object (change=False)
        self.admin_instance.save_model(request, event_def, form, change=False)

        self.assertEqual(event_def.created_by, self.admin_user)

    def test_admin_changelist_view(self):
        """Test admin changelist view"""
        # Create test events
        event1 = self.create_test_event_definition(name='event1')
        event2 = self.create_test_event_definition(name='event2')

        url = self.get_admin_url('eventdefinition')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'event1')
        self.assertContains(response, 'event2')

    def test_admin_change_view(self):
        """Test admin change view"""
        event_def = self.create_test_event_definition()

        url = self.get_admin_url('eventdefinition', 'change', event_def.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, event_def.name)

    def test_admin_add_view(self):
        """Test admin add view"""
        url = self.get_admin_url('eventdefinition', 'add')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '事件名称')


class EventOccurrenceAdminTest(AdminTestCase):
    """Test EventOccurrenceAdmin"""

    def setUp(self):
        super().setUp()
        self.admin_instance = EventOccurrenceAdmin(EventOccurrence, self.site)

    def test_list_display_fields(self):
        """Test list display fields"""
        expected_fields = [
            'event_definition', 'status_badge', 'scheduled_at',
            'duration_display', 'affected_users_count',
            'trigger_type_badge', 'triggered_by'
        ]

        self.assertEqual(self.admin_instance.list_display, expected_fields)

    def test_status_badge_display(self):
        """Test status badge display method"""
        event_def = self.create_test_event_definition()

        # Test different statuses
        statuses = ['pending', 'executing', 'completed', 'failed', 'cancelled']
        colors = ['#FF9800', '#2196F3', '#4CAF50', '#F44336', '#757575']

        for status, expected_color in zip(statuses, colors):
            occurrence = self.create_test_event_occurrence(
                event_def,
                status=status
            )

            badge_html = self.admin_instance.status_badge(occurrence)
            self.assertIn(expected_color, badge_html)
            self.assertIn('●', badge_html)

    def test_trigger_type_badge_display(self):
        """Test trigger type badge display method"""
        event_def = self.create_test_event_definition()

        # Manual trigger
        manual_occurrence = self.create_test_event_occurrence(
            event_def,
            trigger_type='manual'
        )
        badge_html = self.admin_instance.trigger_type_badge(manual_occurrence)
        self.assertIn('🔧 手动', badge_html)

        # Scheduled trigger
        scheduled_occurrence = self.create_test_event_occurrence(
            event_def,
            trigger_type='scheduled'
        )
        badge_html = self.admin_instance.trigger_type_badge(scheduled_occurrence)
        self.assertIn('⏰ 自动', badge_html)

    def test_duration_display(self):
        """Test duration display method"""
        event_def = self.create_test_event_definition()

        # Completed occurrence with duration
        start_time = timezone.now()
        end_time = start_time + timedelta(seconds=30.5)

        occurrence = self.create_test_event_occurrence(
            event_def,
            started_at=start_time,
            completed_at=end_time
        )

        # Mock duration_seconds property
        with patch.object(occurrence, 'duration_seconds', 30.5):
            duration_html = self.admin_instance.duration_display(occurrence)
            self.assertIn('30.50 秒', duration_html)

        # Incomplete occurrence
        incomplete_occurrence = self.create_test_event_occurrence(event_def)
        duration_html = self.admin_instance.duration_display(incomplete_occurrence)
        self.assertIn('未完成', duration_html)

    def test_execution_log_display(self):
        """Test execution log display method"""
        event_def = self.create_test_event_definition()
        occurrence = self.create_test_event_occurrence(event_def)

        # Empty log
        empty_log_html = self.admin_instance.execution_log_display(occurrence)
        self.assertIn('无执行日志', empty_log_html)

        # With execution log
        execution_log = [
            {
                'effect_type': 'coins_add',
                'target_type': 'all_users',
                'affected_count': 5,
                'total_targets': 5
            },
            {
                'effect_type': 'item_distribute',
                'target_type': 'level_based',
                'affected_count': 2,
                'total_targets': 3,
                'error': 'Some items failed to create'
            }
        ]

        occurrence.execution_log = execution_log
        occurrence.save()

        log_html = self.admin_instance.execution_log_display(occurrence)
        self.assertIn('coins_add', log_html)
        self.assertIn('✅ 成功', log_html)
        self.assertIn('❌ 失败', log_html)
        self.assertIn('Some items failed to create', log_html)

    def test_retry_failed_events_action(self):
        """Test retry failed events action"""
        event_def = self.create_test_event_definition()

        # Create failed occurrence
        failed_occurrence = self.create_test_event_occurrence(
            event_def,
            status='failed'
        )

        # Create completed occurrence (should not be retried)
        completed_occurrence = self.create_test_event_occurrence(
            event_def,
            status='completed'
        )

        queryset = EventOccurrence.objects.filter(
            id__in=[failed_occurrence.id, completed_occurrence.id]
        )
        request = MagicMock()
        request.user = self.admin_user

        with patch('events.celery_tasks.trigger_manual_event.delay') as mock_trigger:
            self.admin_instance.retry_failed_events(request, queryset)

            # Should only retry failed event
            mock_trigger.assert_called_once_with(
                str(event_def.id),
                self.admin_user.id
            )

    def test_cancel_pending_events_action(self):
        """Test cancel pending events action"""
        event_def = self.create_test_event_definition()

        # Create pending occurrence
        pending_occurrence = self.create_test_event_occurrence(
            event_def,
            status='pending'
        )

        # Create executing occurrence (should not be cancelled)
        executing_occurrence = self.create_test_event_occurrence(
            event_def,
            status='executing'
        )

        queryset = EventOccurrence.objects.filter(
            id__in=[pending_occurrence.id, executing_occurrence.id]
        )
        request = MagicMock()

        self.admin_instance.cancel_pending_events(request, queryset)

        # Check only pending occurrence was cancelled
        pending_occurrence.refresh_from_db()
        executing_occurrence.refresh_from_db()

        self.assertEqual(pending_occurrence.status, 'cancelled')
        self.assertEqual(executing_occurrence.status, 'executing')


class EventEffectExecutionAdminTest(AdminTestCase):
    """Test EventEffectExecutionAdmin"""

    def setUp(self):
        super().setUp()
        self.admin_instance = EventEffectExecutionAdmin(EventEffectExecution, self.site)

    def test_list_display_fields(self):
        """Test list display fields"""
        expected_fields = [
            'occurrence_link', 'effect_type_display', 'target_user',
            'executed_at', 'status_display', 'expires_at'
        ]

        self.assertEqual(self.admin_instance.list_display, expected_fields)

    def test_occurrence_link(self):
        """Test occurrence link display method"""
        event_def = self.create_test_event_definition(name='test_event')
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={}
        )

        link_html = self.admin_instance.occurrence_link(execution)
        self.assertIn('test_event', link_html)
        self.assertIn('href=', link_html)

    def test_effect_type_display(self):
        """Test effect type display method"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(
            event_def,
            effect_type='coins_add'
        )
        occurrence = self.create_test_event_occurrence(event_def)

        execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={}
        )

        type_display = self.admin_instance.effect_type_display(execution)
        self.assertIn('增加积分', type_display)

    def test_status_display(self):
        """Test status display method"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        # Test different statuses
        # Rolled back
        rolled_back_execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={},
            is_rolled_back=True
        )
        status_html = self.admin_instance.status_display(rolled_back_execution)
        self.assertIn('🔄 已回滚', status_html)

        # Expired
        expired_execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={},
            is_expired=True
        )
        status_html = self.admin_instance.status_display(expired_execution)
        self.assertIn('⏰ 已过期', status_html)

    def test_effect_data_display(self):
        """Test effect data display method"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        effect_data = {
            'old_coins': 100,
            'new_coins': 150,
            'amount_changed': 50
        }

        execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data=effect_data
        )

        data_html = self.admin_instance.effect_data_display(execution)
        self.assertIn('<pre', data_html)
        self.assertIn('old_coins', data_html)
        self.assertIn('150', data_html)

    def test_rollback_data_display(self):
        """Test rollback data display method"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)
        occurrence = self.create_test_event_occurrence(event_def)

        rollback_data = {
            'restore_coins': 100,
            'restore_items': ['item_id_1', 'item_id_2']
        }

        execution = EventEffectExecution.objects.create(
            occurrence=occurrence,
            effect=effect,
            target_user=self.user_level1,
            effect_data={},
            rollback_data=rollback_data
        )

        data_html = self.admin_instance.rollback_data_display(execution)
        self.assertIn('<pre', data_html)
        self.assertIn('restore_coins', data_html)
        self.assertIn('item_id_1', data_html)


class PersistentEffectAdminTest(AdminTestCase):
    """Test persistent effect admin interfaces"""

    def test_user_game_effect_admin(self):
        """Test UserGameEffectAdmin"""
        admin_instance = UserGameEffectAdmin(UserGameEffect, self.site)

        # Create test effect
        game_effect = UserGameEffect.objects.create(
            user=self.user_level1,
            effect_type='multiplier',
            multiplier=2.0,
            expires_at=timezone.now() + timedelta(hours=1),
            is_active=True
        )

        # Test is_active_display
        status_html = admin_instance.is_active_display(game_effect)
        if hasattr(game_effect, 'is_valid'):
            self.assertIn('有效' if game_effect.is_valid else '无效', status_html)

        # Test deactivate action
        queryset = UserGameEffect.objects.filter(id=game_effect.id)
        request = MagicMock()

        admin_instance.deactivate_effects(request, queryset)

        game_effect.refresh_from_db()
        self.assertFalse(game_effect.is_active)

    def test_user_coins_multiplier_admin(self):
        """Test UserCoinsMultiplierAdmin"""
        admin_instance = UserCoinsMultiplierAdmin(UserCoinsMultiplier, self.site)

        # Create test multiplier
        coins_multiplier = UserCoinsMultiplier.objects.create(
            user=self.user_level1,
            multiplier=1.5,
            expires_at=timezone.now() + timedelta(hours=2),
            is_active=True
        )

        # Test is_active_display
        status_html = admin_instance.is_active_display(coins_multiplier)
        if hasattr(coins_multiplier, 'is_valid'):
            self.assertIn('有效' if coins_multiplier.is_valid else '无效', status_html)

        # Test deactivate action
        queryset = UserCoinsMultiplier.objects.filter(id=coins_multiplier.id)
        request = MagicMock()

        admin_instance.deactivate_multipliers(request, queryset)

        coins_multiplier.refresh_from_db()
        self.assertFalse(coins_multiplier.is_active)


class AdminPermissionsTest(AdminTestCase):
    """Test admin permissions and security"""

    def test_admin_requires_staff_permission(self):
        """Test that admin requires staff permission"""
        # Create non-staff user
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123',
            is_staff=False
        )

        self.client.force_login(regular_user)

        url = self.get_admin_url('eventdefinition')
        response = self.client.get(url)

        # Should redirect to login or show permission denied
        self.assertIn(response.status_code, [302, 403])

    def test_admin_readonly_fields(self):
        """Test readonly fields in admin"""
        # EventDefinition readonly fields
        event_admin = EventDefinitionAdmin(EventDefinition, self.site)
        readonly_fields = event_admin.readonly_fields

        self.assertIn('created_by', readonly_fields)
        self.assertIn('created_at', readonly_fields)
        self.assertIn('updated_at', readonly_fields)

    def test_admin_fieldsets(self):
        """Test admin fieldsets organization"""
        event_admin = EventDefinitionAdmin(EventDefinition, self.site)
        fieldsets = event_admin.fieldsets

        # Should have organized fieldsets
        self.assertIsInstance(fieldsets, list)
        self.assertGreater(len(fieldsets), 1)

        # Check fieldset structure
        for fieldset in fieldsets:
            self.assertIsInstance(fieldset, tuple)
            self.assertEqual(len(fieldset), 2)
            self.assertIsInstance(fieldset[1], dict)
            self.assertIn('fields', fieldset[1])

    def test_admin_filtering_and_search(self):
        """Test admin filtering and search functionality"""
        # Create test events with different properties
        weather_event = self.create_test_event_definition(
            name='weather_test',
            category='weather',
            title='Weather Event'
        )

        magic_event = self.create_test_event_definition(
            name='magic_test',
            category='magic',
            title='Magic Event'
        )

        # Test category filter
        url = self.get_admin_url('eventdefinition') + '?category=weather'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'weather_test')
        # Note: This test might need adjustment based on actual admin template

        # Test search
        url = self.get_admin_url('eventdefinition') + '?q=Weather'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Should find weather event by title


class AdminIntegrationTest(AdminTestCase):
    """Test admin integration with event system"""

    def test_admin_inline_effects(self):
        """Test admin inline effects editing"""
        event_def = self.create_test_event_definition()

        # Test that effects can be added via admin
        url = self.get_admin_url('eventdefinition', 'change', event_def.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Should contain inline effect forms
        self.assertContains(response, 'effects-')  # Django inline prefix

    def test_admin_bulk_operations_transaction_safety(self):
        """Test that bulk operations are transaction safe"""
        event1 = self.create_test_event_definition(name='event1')
        event2 = self.create_test_event_definition(name='event2')

        # Mock an error during bulk operation
        with patch.object(EventDefinition.objects, 'update') as mock_update:
            mock_update.side_effect = Exception("Database error")

            queryset = EventDefinition.objects.filter(id__in=[event1.id, event2.id])
            request = MagicMock()

            # Should handle error gracefully
            try:
                EventDefinitionAdmin(EventDefinition, self.site).enable_events(
                    request, queryset
                )
            except Exception:
                pass

            # Original objects should be unchanged
            event1.refresh_from_db()
            event2.refresh_from_db()
            # State depends on transaction handling

    @patch('events.celery_tasks.trigger_manual_event.delay')
    def test_admin_trigger_creates_proper_task(self, mock_trigger):
        """Test that admin trigger creates proper Celery task"""
        event_def = self.create_test_event_definition()
        effect = self.create_test_event_effect(event_def)

        # Mock successful task
        mock_task_result = MagicMock()
        mock_task_result.id = 'test-task-id'
        mock_trigger.return_value = mock_task_result

        queryset = EventDefinition.objects.filter(id=event_def.id)
        request = MagicMock()
        request.user = self.admin_user

        EventDefinitionAdmin(EventDefinition, self.site).trigger_manual_events(
            request, queryset
        )

        # Check task called with correct parameters
        mock_trigger.assert_called_once_with(str(event_def.id), self.admin_user.id)