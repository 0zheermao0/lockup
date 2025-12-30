#!/usr/bin/env python3
"""
Event System Test Fixtures and Sample Data

This module provides test fixtures and sample data for event system testing:
- Predefined event definitions for common scenarios
- Sample effect configurations
- Test data factories and builders
- Mock data generators for performance testing

Author: Claude Code
Created: 2024-12-30
"""

import json
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from unittest.mock import patch

from events.models import EventDefinition, EventEffect, EventOccurrence
from store.models import ItemType
from tests.events.test_base import EventTestCase

User = get_user_model()


class EventFixtures:
    """Factory class for creating test event fixtures"""

    @staticmethod
    def create_weather_events(admin_user):
        """Create a complete set of weather events"""
        events = []

        # Blizzard Event
        blizzard = EventDefinition.objects.create(
            name='blizzard',
            category='weather',
            title='大暴雪',
            description='寒冷的暴雪席卷而来，冻结了所有任务，但系统会给予积分补偿',
            schedule_type='interval_days',
            interval_value=7,
            is_active=True,
            created_by=admin_user
        )

        # Blizzard effects
        EventEffect.objects.create(
            event_definition=blizzard,
            effect_type='task_freeze_all',
            target_type='active_task_users',
            effect_parameters={},
            target_parameters={},
            duration_minutes=120,  # 2 hours freeze
            priority=1,
            is_active=True
        )

        EventEffect.objects.create(
            event_definition=blizzard,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 30},
            target_parameters={},
            priority=2,
            is_active=True
        )

        events.append(blizzard)

        # Sunny Day Event
        sunny = EventDefinition.objects.create(
            name='sunny_day',
            category='weather',
            title='艳阳天',
            description='温暖的阳光照耀大地，解冻所有冻结的任务，并发放阳光瓶',
            schedule_type='interval_days',
            interval_value=5,
            is_active=True,
            created_by=admin_user
        )

        # Sunny day effects
        EventEffect.objects.create(
            event_definition=sunny,
            effect_type='task_unfreeze_all',
            target_type='active_task_users',
            effect_parameters={},
            target_parameters={},
            priority=1,
            is_active=True
        )

        EventEffect.objects.create(
            event_definition=sunny,
            effect_type='item_distribute',
            target_type='all_users',
            effect_parameters={'item_type': 'photo_paper', 'quantity': 1},
            target_parameters={},
            priority=2,
            is_active=True
        )

        events.append(sunny)

        # Spring Rain Event
        rain = EventDefinition.objects.create(
            name='spring_rain',
            category='weather',
            title='春雨',
            description='细润的春雨滋润着大地，随机用户获得积分奖励',
            schedule_type='interval_hours',
            interval_value=12,
            is_active=True,
            created_by=admin_user
        )

        EventEffect.objects.create(
            event_definition=rain,
            effect_type='coins_add',
            target_type='random_percentage',
            effect_parameters={'amount': 15},
            target_parameters={'percentage': 60},
            priority=1,
            is_active=True
        )

        events.append(rain)

        return events

    @staticmethod
    def create_magic_events(admin_user):
        """Create a complete set of magic events"""
        events = []

        # Time Magic Event
        time_magic = EventDefinition.objects.create(
            name='time_magic',
            category='magic',
            title='时间魔法',
            description='神秘的时间魔法延长了所有活跃任务的时间',
            schedule_type='manual',
            is_active=True,
            created_by=admin_user
        )

        EventEffect.objects.create(
            event_definition=time_magic,
            effect_type='task_time_add',
            target_type='active_task_users',
            effect_parameters={'minutes': 30},
            target_parameters={},
            priority=1,
            is_active=True
        )

        events.append(time_magic)

        # Fortune Magic Event
        fortune_magic = EventDefinition.objects.create(
            name='fortune_magic',
            category='magic',
            title='财富魔法',
            description='神秘的财富魔法增强了积分获取能力，持续一小时',
            schedule_type='manual',
            is_active=True,
            created_by=admin_user
        )

        EventEffect.objects.create(
            event_definition=fortune_magic,
            effect_type='temporary_coins_multiplier',
            target_type='random_percentage',
            effect_parameters={'multiplier': 2.0},
            target_parameters={'percentage': 50},
            duration_minutes=60,
            priority=1,
            is_active=True
        )

        events.append(fortune_magic)

        # Item Magic Event
        item_magic = EventDefinition.objects.create(
            name='item_magic',
            category='magic',
            title='道具魔法',
            description='魔法的力量创造了珍贵的道具',
            schedule_type='manual',
            is_active=True,
            created_by=admin_user
        )

        EventEffect.objects.create(
            event_definition=item_magic,
            effect_type='item_distribute',
            target_type='level_based',
            effect_parameters={'item_type': 'detection_radar', 'quantity': 1},
            target_parameters={'levels': [3, 4]},
            priority=1,
            is_active=True
        )

        events.append(item_magic)

        return events

    @staticmethod
    def create_system_events(admin_user):
        """Create a complete set of system events"""
        events = []

        # Maintenance Compensation
        maintenance = EventDefinition.objects.create(
            name='maintenance_compensation',
            category='system',
            title='维护补偿',
            description='感谢您在系统维护期间的耐心等待，这是我们的补偿',
            schedule_type='manual',
            is_active=True,
            created_by=admin_user
        )

        # Basic compensation for all users
        EventEffect.objects.create(
            event_definition=maintenance,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 50},
            target_parameters={},
            priority=1,
            is_active=True
        )

        # Extra compensation for high-level users
        EventEffect.objects.create(
            event_definition=maintenance,
            effect_type='coins_add',
            target_type='level_based',
            effect_parameters={'amount': 50},
            target_parameters={'levels': [3, 4]},
            priority=2,
            is_active=True
        )

        # Item compensation
        EventEffect.objects.create(
            event_definition=maintenance,
            effect_type='item_distribute',
            target_type='all_users',
            effect_parameters={'item_type': 'photo_paper', 'quantity': 2},
            target_parameters={},
            priority=3,
            is_active=True
        )

        events.append(maintenance)

        # Festival Celebration
        festival = EventDefinition.objects.create(
            name='festival_celebration',
            category='system',
            title='节日庆典',
            description='节日庆典期间，商店全场8折优惠',
            schedule_type='manual',
            is_active=True,
            created_by=admin_user
        )

        EventEffect.objects.create(
            event_definition=festival,
            effect_type='store_discount',
            target_type='all_users',
            effect_parameters={
                'discount_rate': 0.2,  # 20% discount (80% price)
                'item_types': ['detection_radar', 'photo_paper']
            },
            target_parameters={},
            duration_minutes=1440,  # 24 hours
            priority=1,
            is_active=True
        )

        events.append(festival)

        # Lucky Moment
        lucky_moment = EventDefinition.objects.create(
            name='lucky_moment',
            category='system',
            title='幸运时刻',
            description='幸运时刻到来，游戏效果翻倍',
            schedule_type='manual',
            is_active=True,
            created_by=admin_user
        )

        EventEffect.objects.create(
            event_definition=lucky_moment,
            effect_type='temporary_game_enhancement',
            target_type='all_users',
            effect_parameters={'multiplier': 2.0},
            target_parameters={},
            duration_minutes=60,
            priority=1,
            is_active=True
        )

        events.append(lucky_moment)

        return events

    @staticmethod
    def create_special_events(admin_user):
        """Create special limited-time events"""
        events = []

        # New Year Event
        new_year = EventDefinition.objects.create(
            name='new_year_celebration',
            category='special',
            title='新年庆典',
            description='新年快乐！系统为所有用户准备了丰厚的新年礼物',
            schedule_type='manual',
            is_active=False,  # Special events start inactive
            created_by=admin_user
        )

        # Multiple generous effects for special event
        EventEffect.objects.create(
            event_definition=new_year,
            effect_type='coins_add',
            target_type='all_users',
            effect_parameters={'amount': 200},
            target_parameters={},
            priority=1,
            is_active=True
        )

        EventEffect.objects.create(
            event_definition=new_year,
            effect_type='item_distribute',
            target_type='all_users',
            effect_parameters={'item_type': 'detection_radar', 'quantity': 1},
            target_parameters={},
            priority=2,
            is_active=True
        )

        EventEffect.objects.create(
            event_definition=new_year,
            effect_type='temporary_coins_multiplier',
            target_type='all_users',
            effect_parameters={'multiplier': 3.0},
            target_parameters={},
            duration_minutes=180,  # 3 hours
            priority=3,
            is_active=True
        )

        events.append(new_year)

        # Emergency Event
        emergency = EventDefinition.objects.create(
            name='system_emergency',
            category='special',
            title='系统紧急事件',
            description='系统检测到异常情况，临时冻结所有任务以确保安全',
            schedule_type='manual',
            is_active=False,
            created_by=admin_user
        )

        EventEffect.objects.create(
            event_definition=emergency,
            effect_type='task_freeze_all',
            target_type='active_task_users',
            effect_parameters={},
            target_parameters={},
            duration_minutes=60,
            priority=1,
            is_active=True
        )

        EventEffect.objects.create(
            event_definition=emergency,
            effect_type='coins_add',
            target_type='active_task_users',
            effect_parameters={'amount': 100},
            target_parameters={},
            priority=2,
            is_active=True
        )

        events.append(emergency)

        return events


class EventTestDataBuilder:
    """Builder pattern for creating complex test scenarios"""

    def __init__(self, admin_user):
        self.admin_user = admin_user
        self.event_definition = None
        self.effects = []

    def create_event(self, name, category='system', title=None, description=None,
                    schedule_type='manual', **kwargs):
        """Create base event definition"""
        defaults = {
            'name': name,
            'category': category,
            'title': title or f'Test {name.title()}',
            'description': description or f'Test event for {name}',
            'schedule_type': schedule_type,
            'is_active': True,
            'created_by': self.admin_user
        }
        defaults.update(kwargs)

        self.event_definition = EventDefinition.objects.create(**defaults)
        return self

    def add_coins_effect(self, amount, target_type='all_users', target_params=None,
                        priority=1, duration_minutes=None):
        """Add coins effect to event"""
        effect = EventEffect.objects.create(
            event_definition=self.event_definition,
            effect_type='coins_add',
            target_type=target_type,
            effect_parameters={'amount': amount},
            target_parameters=target_params or {},
            duration_minutes=duration_minutes,
            priority=priority,
            is_active=True
        )
        self.effects.append(effect)
        return self

    def add_item_effect(self, item_type, quantity=1, target_type='all_users',
                       target_params=None, priority=1):
        """Add item distribution effect to event"""
        effect = EventEffect.objects.create(
            event_definition=self.event_definition,
            effect_type='item_distribute',
            target_type=target_type,
            effect_parameters={'item_type': item_type, 'quantity': quantity},
            target_parameters=target_params or {},
            priority=priority,
            is_active=True
        )
        self.effects.append(effect)
        return self

    def add_task_freeze_effect(self, duration_minutes=60, target_type='active_task_users',
                              priority=1):
        """Add task freeze effect to event"""
        effect = EventEffect.objects.create(
            event_definition=self.event_definition,
            effect_type='task_freeze_all',
            target_type=target_type,
            effect_parameters={},
            target_parameters={},
            duration_minutes=duration_minutes,
            priority=priority,
            is_active=True
        )
        self.effects.append(effect)
        return self

    def add_multiplier_effect(self, multiplier=2.0, duration_minutes=60,
                             target_type='all_users', target_params=None, priority=1):
        """Add coins multiplier effect to event"""
        effect = EventEffect.objects.create(
            event_definition=self.event_definition,
            effect_type='temporary_coins_multiplier',
            target_type=target_type,
            effect_parameters={'multiplier': multiplier},
            target_parameters=target_params or {},
            duration_minutes=duration_minutes,
            priority=priority,
            is_active=True
        )
        self.effects.append(effect)
        return self

    def build(self):
        """Return the built event and effects"""
        return self.event_definition, self.effects


class EventSampleDataTest(EventTestCase):
    """Test sample data creation and validation"""

    def test_weather_events_creation(self):
        """Test creation of weather event fixtures"""
        events = EventFixtures.create_weather_events(self.admin_user)

        self.assertEqual(len(events), 3)

        # Test blizzard event
        blizzard = events[0]
        self.assertEqual(blizzard.name, 'blizzard')
        self.assertEqual(blizzard.category, 'weather')
        self.assertEqual(blizzard.schedule_type, 'interval_days')
        self.assertEqual(blizzard.interval_value, 7)

        blizzard_effects = blizzard.effects.all()
        self.assertEqual(blizzard_effects.count(), 2)

        freeze_effect = blizzard_effects.filter(effect_type='task_freeze_all').first()
        self.assertIsNotNone(freeze_effect)
        self.assertEqual(freeze_effect.duration_minutes, 120)

        coins_effect = blizzard_effects.filter(effect_type='coins_add').first()
        self.assertIsNotNone(coins_effect)
        self.assertEqual(coins_effect.effect_parameters['amount'], 30)

    def test_magic_events_creation(self):
        """Test creation of magic event fixtures"""
        events = EventFixtures.create_magic_events(self.admin_user)

        self.assertEqual(len(events), 3)

        # Test fortune magic event
        fortune_magic = next(e for e in events if e.name == 'fortune_magic')
        self.assertEqual(fortune_magic.category, 'magic')

        multiplier_effect = fortune_magic.effects.first()
        self.assertEqual(multiplier_effect.effect_type, 'temporary_coins_multiplier')
        self.assertEqual(multiplier_effect.effect_parameters['multiplier'], 2.0)
        self.assertEqual(multiplier_effect.duration_minutes, 60)

    def test_system_events_creation(self):
        """Test creation of system event fixtures"""
        events = EventFixtures.create_system_events(self.admin_user)

        self.assertGreater(len(events), 0)

        # Test maintenance compensation event
        maintenance = next(e for e in events if e.name == 'maintenance_compensation')
        self.assertEqual(maintenance.category, 'system')

        effects = maintenance.effects.all()
        self.assertGreater(effects.count(), 1)

        # Should have both general and level-based coins effects
        coins_effects = effects.filter(effect_type='coins_add')
        self.assertGreaterEqual(coins_effects.count(), 2)

    def test_special_events_creation(self):
        """Test creation of special event fixtures"""
        events = EventFixtures.create_special_events(self.admin_user)

        self.assertGreater(len(events), 0)

        # Test new year event
        new_year = next(e for e in events if e.name == 'new_year_celebration')
        self.assertEqual(new_year.category, 'special')
        self.assertFalse(new_year.is_active)  # Special events start inactive

        effects = new_year.effects.all()
        self.assertGreater(effects.count(), 2)  # Multiple generous effects

    def test_event_builder_pattern(self):
        """Test event builder pattern"""
        builder = EventTestDataBuilder(self.admin_user)

        event, effects = (builder
                         .create_event('test_builder', category='system', title='Builder Test')
                         .add_coins_effect(100, target_type='level_based',
                                          target_params={'levels': [1, 2]})
                         .add_item_effect('photo_paper', quantity=2)
                         .add_task_freeze_effect(duration_minutes=30)
                         .build())

        self.assertEqual(event.name, 'test_builder')
        self.assertEqual(event.title, 'Builder Test')
        self.assertEqual(len(effects), 3)

        # Verify effects
        coins_effect = next(e for e in effects if e.effect_type == 'coins_add')
        self.assertEqual(coins_effect.effect_parameters['amount'], 100)
        self.assertEqual(coins_effect.target_parameters['levels'], [1, 2])

        item_effect = next(e for e in effects if e.effect_type == 'item_distribute')
        self.assertEqual(item_effect.effect_parameters['quantity'], 2)

        freeze_effect = next(e for e in effects if e.effect_type == 'task_freeze_all')
        self.assertEqual(freeze_effect.duration_minutes, 30)

    def test_complex_event_scenario(self):
        """Test complex multi-effect event scenario"""
        builder = EventTestDataBuilder(self.admin_user)

        # Create a complex event with multiple targeting strategies
        event, effects = (builder
                         .create_event('complex_scenario',
                                     title='Complex Multi-Effect Event',
                                     description='A complex event testing multiple effects')
                         # Basic reward for all users
                         .add_coins_effect(25, target_type='all_users', priority=1)
                         # Bonus for high-level users
                         .add_coins_effect(50, target_type='level_based',
                                          target_params={'levels': [3, 4]}, priority=2)
                         # Random item distribution
                         .add_item_effect('photo_paper', quantity=1,
                                         target_type='random_percentage',
                                         target_params={'percentage': 30}, priority=3)
                         # Task freeze for active users
                         .add_task_freeze_effect(duration_minutes=45, priority=4)
                         # Temporary multiplier for random users
                         .add_multiplier_effect(multiplier=1.5, duration_minutes=90,
                                              target_type='random_percentage',
                                              target_params={'percentage': 40}, priority=5)
                         .build())

        self.assertEqual(len(effects), 5)

        # Verify priority ordering
        sorted_effects = sorted(effects, key=lambda e: e.priority)
        self.assertEqual(sorted_effects[0].effect_type, 'coins_add')
        self.assertEqual(sorted_effects[0].target_type, 'all_users')
        self.assertEqual(sorted_effects[4].effect_type, 'temporary_coins_multiplier')

        # Verify complex targeting parameters
        random_item_effect = next(e for e in effects
                                 if e.effect_type == 'item_distribute')
        self.assertEqual(random_item_effect.target_type, 'random_percentage')
        self.assertEqual(random_item_effect.target_parameters['percentage'], 30)


class MockDataGenerators:
    """Utilities for generating mock data for testing"""

    @staticmethod
    def create_large_user_base(count=100, base_username='test_user'):
        """Create a large number of test users for performance testing"""
        users = []
        for i in range(count):
            user = User.objects.create_user(
                username=f'{base_username}_{i}',
                email=f'{base_username}_{i}@test.com',
                password='testpass123',
                level=(i % 4) + 1,  # Distribute across levels 1-4
                coins=100 + (i * 10)  # Varying coin amounts
            )
            users.append(user)
        return users

    @staticmethod
    def create_random_event_occurrences(event_definition, count=10):
        """Create multiple random event occurrences for testing"""
        occurrences = []
        base_time = timezone.now() - timedelta(days=30)

        for i in range(count):
            occurrence = EventOccurrence.objects.create(
                event_definition=event_definition,
                scheduled_at=base_time + timedelta(days=i * 3),
                trigger_type='scheduled' if i % 2 == 0 else 'manual',
                status=['pending', 'completed', 'failed'][i % 3]
            )
            occurrences.append(occurrence)

        return occurrences

    @staticmethod
    def cleanup_test_data():
        """Clean up all test data created by generators"""
        # Clean up test users
        User.objects.filter(username__startswith='test_user_').delete()
        User.objects.filter(username__startswith='perf_user_').delete()

        # Clean up test events
        EventDefinition.objects.filter(name__startswith='test_').delete()
        EventDefinition.objects.filter(name__startswith='perf_').delete()