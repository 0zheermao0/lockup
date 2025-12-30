#!/usr/bin/env python3
"""
Django Management Command to Initialize Sample Events

This command creates sample event definitions for testing and demonstration:
- Weather events (snowstorm, sunny day, spring rain)
- Magic events (magic hour, fortune blessing)
- System events (maintenance compensation, festival celebration)

Author: Claude Code
Created: 2024-12-30
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from events.models import EventDefinition, EventEffect
from users.models import User
import json


class Command(BaseCommand):
    help = 'Initialize sample event definitions for testing and demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing events with same names'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        overwrite = options['overwrite']

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('[DRY RUN] Sample events that would be created:')
            )

        # Get or create admin user for event creation
        admin_user = self._get_admin_user()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR('No admin user found. Please create a superuser first.')
            )
            return

        sample_events = self._get_sample_events()

        with transaction.atomic():
            created_count = 0
            updated_count = 0

            for event_data in sample_events:
                event_name = event_data['definition']['name']

                if dry_run:
                    self._display_event_preview(event_data)
                    continue

                # Check if event exists
                existing_event = EventDefinition.objects.filter(name=event_name).first()

                if existing_event:
                    if overwrite:
                        # Delete existing event and its effects
                        existing_event.delete()
                        self.stdout.write(f'Deleted existing event: {event_name}')
                        updated_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'Event already exists: {event_name} (use --overwrite to replace)')
                        )
                        continue

                # Create event definition
                definition_data = event_data['definition'].copy()
                definition_data['created_by'] = admin_user

                event_def = EventDefinition.objects.create(**definition_data)

                # Create effects
                for effect_data in event_data['effects']:
                    effect_data['event_definition'] = event_def
                    EventEffect.objects.create(**effect_data)

                self.stdout.write(
                    self.style.SUCCESS(f'Created event: {event_name} with {len(event_data["effects"])} effects')
                )
                created_count += 1

            if not dry_run:
                self.stdout.write('\n' + '=' * 60)
                self.stdout.write(
                    self.style.SUCCESS(f'Sample events initialization completed!')
                )
                self.stdout.write(f'Created: {created_count} events')
                self.stdout.write(f'Updated: {updated_count} events')
            else:
                self.stdout.write('\n[DRY RUN] No changes made')

    def _get_admin_user(self):
        """Get the first admin user"""
        return User.objects.filter(is_superuser=True).first()

    def _display_event_preview(self, event_data):
        """Display preview of event to be created"""
        definition = event_data['definition']
        effects = event_data['effects']

        self.stdout.write(f'\n--- {definition["name"]} ---')
        self.stdout.write(f'Title: {definition["title"]}')
        self.stdout.write(f'Category: {definition["category"]}')
        self.stdout.write(f'Schedule: {definition["schedule_type"]}')
        if definition.get('interval_value'):
            self.stdout.write(f'Interval: {definition["interval_value"]}')

        self.stdout.write(f'Effects ({len(effects)}):')
        for i, effect in enumerate(effects, 1):
            self.stdout.write(f'  {i}. {effect["effect_type"]} -> {effect["target_type"]}')
            if effect.get('duration_minutes'):
                self.stdout.write(f'     Duration: {effect["duration_minutes"]} minutes')

    def _get_sample_events(self):
        """Get sample event definitions"""
        return [
            {
                'definition': {
                    'name': 'heavy_snowstorm',
                    'category': 'weather',
                    'title': '大暴雪来袭',
                    'description': '暴风雪席卷而来，所有户外活动被迫暂停，任务被冻结2小时',
                    'schedule_type': 'interval_days',
                    'interval_value': 7,
                    'is_active': True
                },
                'effects': [
                    {
                        'effect_type': 'task_freeze_all',
                        'target_type': 'active_task_users',
                        'effect_parameters': {},
                        'target_parameters': {},
                        'duration_minutes': 120,
                        'priority': 1,
                        'is_active': True
                    },
                    {
                        'effect_type': 'item_distribute',
                        'target_type': 'all_users',
                        'effect_parameters': {
                            'item_type': 'photo_paper',
                            'quantity': 1
                        },
                        'target_parameters': {},
                        'duration_minutes': None,
                        'priority': 2,
                        'is_active': True
                    }
                ]
            },
            {
                'definition': {
                    'name': 'sunny_day',
                    'category': 'weather',
                    'title': '阳光明媚',
                    'description': '阳光普照大地，所有人心情愉悦，获得额外积分奖励',
                    'schedule_type': 'interval_days',
                    'interval_value': 5,
                    'is_active': True
                },
                'effects': [
                    {
                        'effect_type': 'coins_add',
                        'target_type': 'all_users',
                        'effect_parameters': {
                            'amount': 20
                        },
                        'target_parameters': {},
                        'duration_minutes': None,
                        'priority': 1,
                        'is_active': True
                    },
                    {
                        'effect_type': 'task_unfreeze_all',
                        'target_type': 'active_task_users',
                        'effect_parameters': {},
                        'target_parameters': {},
                        'duration_minutes': None,
                        'priority': 2,
                        'is_active': True
                    }
                ]
            },
            {
                'definition': {
                    'name': 'spring_rain',
                    'category': 'weather',
                    'title': '春雨降临',
                    'description': '温暖的春雨滋润大地，随机50%的用户获得好运',
                    'schedule_type': 'interval_hours',
                    'interval_value': 12,
                    'is_active': True
                },
                'effects': [
                    {
                        'effect_type': 'coins_add',
                        'target_type': 'random_percentage',
                        'effect_parameters': {
                            'amount': 30
                        },
                        'target_parameters': {
                            'percentage': 50
                        },
                        'duration_minutes': None,
                        'priority': 1,
                        'is_active': True
                    }
                ]
            },
            {
                'definition': {
                    'name': 'magic_hour',
                    'category': 'magic',
                    'title': '魔法时刻',
                    'description': '神秘的魔法力量降临，积分获得翻倍效果持续1小时',
                    'schedule_type': 'interval_hours',
                    'interval_value': 24,
                    'is_active': True
                },
                'effects': [
                    {
                        'effect_type': 'temporary_coins_multiplier',
                        'target_type': 'random_percentage',
                        'effect_parameters': {
                            'multiplier': 2.0
                        },
                        'target_parameters': {
                            'percentage': 30
                        },
                        'duration_minutes': 60,
                        'priority': 1,
                        'is_active': True
                    }
                ]
            },
            {
                'definition': {
                    'name': 'fortune_blessing',
                    'category': 'magic',
                    'title': '幸运祝福',
                    'description': '幸运女神的祝福降临，高级用户获得特殊道具',
                    'schedule_type': 'interval_days',
                    'interval_value': 3,
                    'is_active': True
                },
                'effects': [
                    {
                        'effect_type': 'item_distribute',
                        'target_type': 'level_based',
                        'effect_parameters': {
                            'item_type': 'detection_radar',
                            'quantity': 1
                        },
                        'target_parameters': {
                            'levels': [3, 4]
                        },
                        'duration_minutes': None,
                        'priority': 1,
                        'is_active': True
                    }
                ]
            },
            {
                'definition': {
                    'name': 'maintenance_compensation',
                    'category': 'system',
                    'title': '维护补偿',
                    'description': '系统维护期间的补偿奖励，所有用户获得积分和道具',
                    'schedule_type': 'manual',
                    'interval_value': None,
                    'is_active': True
                },
                'effects': [
                    {
                        'effect_type': 'coins_add',
                        'target_type': 'all_users',
                        'effect_parameters': {
                            'amount': 100
                        },
                        'target_parameters': {},
                        'duration_minutes': None,
                        'priority': 1,
                        'is_active': True
                    },
                    {
                        'effect_type': 'item_distribute',
                        'target_type': 'all_users',
                        'effect_parameters': {
                            'item_type': 'photo_paper',
                            'quantity': 3
                        },
                        'target_parameters': {},
                        'duration_minutes': None,
                        'priority': 2,
                        'is_active': True
                    }
                ]
            },
            {
                'definition': {
                    'name': 'festival_celebration',
                    'category': 'special',
                    'title': '节日庆典',
                    'description': '节日庆典活动，商店全场8折优惠持续24小时',
                    'schedule_type': 'manual',
                    'interval_value': None,
                    'is_active': True
                },
                'effects': [
                    {
                        'effect_type': 'store_discount',
                        'target_type': 'all_users',
                        'effect_parameters': {
                            'discount_rate': 0.2,
                            'item_types': ['detection_radar', 'photo_paper', 'invisible_cloak']
                        },
                        'target_parameters': {},
                        'duration_minutes': 1440,  # 24 hours
                        'priority': 1,
                        'is_active': True
                    }
                ]
            },
            {
                'definition': {
                    'name': 'coins_rain',
                    'category': 'special',
                    'title': '积分雨',
                    'description': '天空下起了积分雨，所有用户都能收集到额外积分',
                    'schedule_type': 'manual',
                    'interval_value': None,
                    'is_active': True
                },
                'effects': [
                    {
                        'effect_type': 'coins_add',
                        'target_type': 'all_users',
                        'effect_parameters': {
                            'amount': 50
                        },
                        'target_parameters': {},
                        'duration_minutes': None,
                        'priority': 1,
                        'is_active': True
                    }
                ]
            }
        ]