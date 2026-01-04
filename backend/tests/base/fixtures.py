#!/usr/bin/env python3
"""
Test Fixtures for Lockup Backend Unit Tests

This module provides comprehensive test fixtures for the Lockup backend system.
Fixtures are organized by functionality area and provide realistic test data
for comprehensive business logic testing.

Author: Claude Code
Created: 2026-01-04
"""

from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json


class TaskFixtures:
    """Fixtures for task-related testing"""

    @staticmethod
    def get_lock_task_data():
        """Get comprehensive lock task test data"""
        return {
            'easy_task': {
                'difficulty': 'easy',
                'duration_hours': 1,
                'reward_base': 10,
                'penalty_multiplier': 1.0
            },
            'medium_task': {
                'difficulty': 'medium',
                'duration_hours': 2,
                'reward_base': 20,
                'penalty_multiplier': 1.5
            },
            'hard_task': {
                'difficulty': 'hard',
                'duration_hours': 4,
                'reward_base': 40,
                'penalty_multiplier': 2.0
            },
            'extreme_task': {
                'difficulty': 'extreme',
                'duration_hours': 8,
                'reward_base': 80,
                'penalty_multiplier': 3.0
            }
        }

    @staticmethod
    def get_board_task_data():
        """Get board task test data"""
        return {
            'simple_task': {
                'title': 'Simple Test Task',
                'description': 'A simple task for testing',
                'reward_amount': 50,
                'max_participants': 1,
                'deadline_days': 7
            },
            'multi_user_task': {
                'title': 'Multi-User Test Task',
                'description': 'A task requiring multiple participants',
                'reward_amount': 200,
                'max_participants': 5,
                'deadline_days': 14
            },
            'high_reward_task': {
                'title': 'High Reward Test Task',
                'description': 'A high-value task for testing',
                'reward_amount': 1000,
                'max_participants': 3,
                'deadline_days': 30
            }
        }

    @staticmethod
    def get_task_timeline_events():
        """Get task timeline event types for testing"""
        return [
            'task_created',
            'task_started',
            'task_paused',
            'task_resumed',
            'task_completed',
            'task_failed',
            'voting_started',
            'voting_ended',
            'vote_cast',
            'task_frozen',
            'task_unfrozen',
            'time_added',
            'time_reduced',
            'hourly_reward_distributed',
            'penalty_applied',
            'user_pinned',
            'user_unpinned',
            'item_used',
            'difficulty_changed',
            'participant_added',
            'participant_removed',
            'submission_created',
            'submission_approved',
            'submission_rejected',
            'task_expired'
        ]


class UserFixtures:
    """Fixtures for user-related testing"""

    @staticmethod
    def get_user_levels_data():
        """Get user level progression data"""
        return {
            1: {
                'level': 1,
                'min_activity': 0,
                'max_activity': 49,
                'inventory_slots': 5,
                'daily_coin_limit': 100,
                'vote_weight': 1.0
            },
            2: {
                'level': 2,
                'min_activity': 50,
                'max_activity': 149,
                'inventory_slots': 8,
                'daily_coin_limit': 200,
                'vote_weight': 1.2
            },
            3: {
                'level': 3,
                'min_activity': 150,
                'max_activity': 349,
                'inventory_slots': 12,
                'daily_coin_limit': 300,
                'vote_weight': 1.5
            },
            4: {
                'level': 4,
                'min_activity': 350,
                'max_activity': 699,
                'inventory_slots': 18,
                'daily_coin_limit': 500,
                'vote_weight': 2.0
            },
            5: {
                'level': 5,
                'min_activity': 700,
                'max_activity': float('inf'),
                'inventory_slots': 25,
                'daily_coin_limit': 1000,
                'vote_weight': 3.0
            }
        }

    @staticmethod
    def get_fibonacci_decay_sequence():
        """Get Fibonacci sequence for activity decay testing"""
        return [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]

    @staticmethod
    def get_coin_earning_scenarios():
        """Get coin earning test scenarios"""
        return {
            'task_completion': {
                'source': 'task_completion',
                'base_amount': 50,
                'level_multipliers': {1: 1.0, 2: 1.1, 3: 1.2, 4: 1.3, 5: 1.5}
            },
            'hourly_reward': {
                'source': 'hourly_reward',
                'base_amount': 10,
                'difficulty_multipliers': {
                    'easy': 1.0, 'medium': 1.5, 'hard': 2.0, 'extreme': 3.0
                }
            },
            'voting_reward': {
                'source': 'voting_reward',
                'base_amount': 5,
                'accuracy_bonus': 10
            },
            'exploration_reward': {
                'source': 'exploration_reward',
                'base_amount': 20,
                'rarity_multipliers': {
                    'common': 1.0, 'uncommon': 1.5, 'rare': 2.0, 'epic': 3.0
                }
            }
        }


class PostFixtures:
    """Fixtures for post and social interaction testing"""

    @staticmethod
    def get_post_types():
        """Get post type test data"""
        return {
            'normal': {
                'type': 'normal',
                'requires_location': False,
                'max_images': 9,
                'voting_enabled': False
            },
            'checkin': {
                'type': 'checkin',
                'requires_location': True,
                'max_images': 9,
                'voting_enabled': True
            },
            'task_share': {
                'type': 'task_share',
                'requires_location': False,
                'max_images': 3,
                'voting_enabled': False
            }
        }

    @staticmethod
    def get_comment_hierarchy_data():
        """Get comment hierarchy test data"""
        return {
            'max_depth': 2,
            'path_separator': '/',
            'sample_paths': [
                '1/',
                '1/2/',
                '3/',
                '3/4/',
                '3/5/',
                '6/'
            ]
        }

    @staticmethod
    def get_voting_scenarios():
        """Get voting test scenarios"""
        return {
            'simple_vote': {
                'voters_count': 3,
                'agree_ratio': 0.67,
                'coin_cost': 5
            },
            'controversial_vote': {
                'voters_count': 10,
                'agree_ratio': 0.5,
                'coin_cost': 5
            },
            'unanimous_vote': {
                'voters_count': 5,
                'agree_ratio': 1.0,
                'coin_cost': 5
            }
        }


class GameFixtures:
    """Fixtures for game-related testing"""

    @staticmethod
    def get_game_types():
        """Get game type configurations"""
        return {
            'time_wheel': {
                'name': 'time_wheel',
                'display_name': '时间轮盘',
                'entry_fee': 20,
                'max_participants': 1,
                'outcomes': [
                    {'type': 'time_add', 'value': 30, 'probability': 0.3},
                    {'type': 'time_reduce', 'value': 15, 'probability': 0.2},
                    {'type': 'coins_add', 'value': 50, 'probability': 0.2},
                    {'type': 'coins_reduce', 'value': 10, 'probability': 0.1},
                    {'type': 'freeze', 'value': 60, 'probability': 0.1},
                    {'type': 'nothing', 'value': 0, 'probability': 0.1}
                ]
            },
            'dice': {
                'name': 'dice',
                'display_name': '骰子游戏',
                'entry_fee': 10,
                'max_participants': 4,
                'winning_conditions': {
                    'single_six': {'multiplier': 2.0, 'probability': 1/6},
                    'double_six': {'multiplier': 10.0, 'probability': 1/36},
                    'triple_six': {'multiplier': 50.0, 'probability': 1/216}
                }
            },
            'rock_paper_scissors': {
                'name': 'rock_paper_scissors',
                'display_name': '石头剪刀布',
                'entry_fee': 15,
                'max_participants': 2,
                'choices': ['rock', 'paper', 'scissors'],
                'win_conditions': {
                    'rock': 'scissors',
                    'paper': 'rock',
                    'scissors': 'paper'
                }
            }
        }

    @staticmethod
    def get_game_session_states():
        """Get game session state transitions"""
        return {
            'pending': ['active', 'cancelled'],
            'active': ['completed', 'cancelled'],
            'completed': [],
            'cancelled': []
        }


class StoreFixtures:
    """Fixtures for store and item testing"""

    @staticmethod
    def get_item_types():
        """Get comprehensive item type data"""
        return {
            'key': {
                'name': 'key',
                'display_name': '钥匙',
                'description': '用于完成带锁任务的钥匙',
                'price': 0,
                'max_quantity': 1,
                'is_consumable': True,
                'level_requirement': 1
            },
            'universal_key': {
                'name': 'universal_key',
                'display_name': '万能钥匙',
                'description': '可以完成任何带锁任务的万能钥匙',
                'price': 100,
                'max_quantity': 5,
                'is_consumable': True,
                'level_requirement': 3
            },
            'time_wheel': {
                'name': 'time_wheel',
                'display_name': '时间轮盘',
                'description': '可以修改任务时间的神奇轮盘',
                'price': 50,
                'max_quantity': 3,
                'is_consumable': True,
                'level_requirement': 2
            },
            'photo_paper': {
                'name': 'photo_paper',
                'display_name': '照片纸',
                'description': '用于拍摄照片的特殊纸张',
                'price': 10,
                'max_quantity': 10,
                'is_consumable': True,
                'level_requirement': 1
            },
            'detection_radar': {
                'name': 'detection_radar',
                'display_name': '探测雷达',
                'description': '探测周围物品的神奇雷达',
                'price': 30,
                'max_quantity': 5,
                'is_consumable': True,
                'level_requirement': 2
            },
            'treasury': {
                'name': 'treasury',
                'display_name': '小金库',
                'description': '可以存储积分的小金库',
                'price': 200,
                'max_quantity': 1,
                'is_consumable': False,
                'level_requirement': 4
            },
            'influence_crown': {
                'name': 'influence_crown',
                'display_name': '影响力皇冠',
                'description': '增加投票权重的皇冠',
                'price': 500,
                'max_quantity': 1,
                'is_consumable': False,
                'level_requirement': 5
            }
        }

    @staticmethod
    def get_treasury_scenarios():
        """Get treasury operation test scenarios"""
        return {
            'deposit': {
                'action': 'deposit',
                'amounts': [10, 50, 100, 500],
                'success_conditions': ['sufficient_coins', 'valid_amount']
            },
            'withdraw': {
                'action': 'withdraw',
                'amounts': [10, 50, 100, 500],
                'success_conditions': ['sufficient_treasury_balance', 'valid_amount']
            },
            'interest': {
                'daily_rate': 0.01,
                'compound_frequency': 'daily',
                'max_balance': 10000
            }
        }


class ExplorationFixtures:
    """Fixtures for exploration-related testing"""

    @staticmethod
    def get_treasure_data():
        """Get buried treasure test data"""
        return {
            'common_treasure': {
                'difficulty': 'easy',
                'bury_cost': 20,
                'min_reward': 30,
                'max_reward': 50,
                'discovery_radius': 100
            },
            'rare_treasure': {
                'difficulty': 'medium',
                'bury_cost': 50,
                'min_reward': 80,
                'max_reward': 120,
                'discovery_radius': 50
            },
            'epic_treasure': {
                'difficulty': 'hard',
                'bury_cost': 100,
                'min_reward': 200,
                'max_reward': 300,
                'discovery_radius': 25
            }
        }

    @staticmethod
    def get_drift_bottle_data():
        """Get drift bottle test data"""
        return {
            'simple_bottle': {
                'message_length': 100,
                'coin_cost': 10,
                'discovery_time_hours': 24
            },
            'premium_bottle': {
                'message_length': 500,
                'coin_cost': 50,
                'discovery_time_hours': 72,
                'includes_item': True
            }
        }

    @staticmethod
    def get_location_data():
        """Get location test data"""
        return {
            'beijing': {
                'latitude': 39.9042,
                'longitude': 116.4074,
                'city': 'Beijing',
                'country': 'China'
            },
            'shanghai': {
                'latitude': 31.2304,
                'longitude': 121.4737,
                'city': 'Shanghai',
                'country': 'China'
            },
            'guangzhou': {
                'latitude': 23.1291,
                'longitude': 113.2644,
                'city': 'Guangzhou',
                'country': 'China'
            }
        }


class NotificationFixtures:
    """Fixtures for notification testing"""

    @staticmethod
    def get_notification_types():
        """Get notification type data"""
        return {
            'task_completed': {
                'type': 'task_completed',
                'template': 'Your task "{task_title}" has been completed!',
                'priority': 'high',
                'channels': ['in_app', 'telegram']
            },
            'vote_received': {
                'type': 'vote_received',
                'template': 'You received a vote on your task "{task_title}"',
                'priority': 'medium',
                'channels': ['in_app', 'telegram']
            },
            'coins_earned': {
                'type': 'coins_earned',
                'template': 'You earned {amount} coins!',
                'priority': 'low',
                'channels': ['in_app']
            },
            'item_received': {
                'type': 'item_received',
                'template': 'You received a new item: {item_name}',
                'priority': 'medium',
                'channels': ['in_app', 'telegram']
            }
        }


class TimeFixtures:
    """Fixtures for time-related testing"""

    @staticmethod
    def get_timezone_data():
        """Get timezone test data"""
        return {
            'utc': timezone.utc,
            'beijing': timezone.get_fixed_timezone(8 * 60),  # UTC+8
            'new_york': timezone.get_fixed_timezone(-5 * 60),  # UTC-5
            'london': timezone.get_fixed_timezone(0)  # UTC
        }

    @staticmethod
    def get_time_scenarios():
        """Get time-based test scenarios"""
        base_time = timezone.now()
        return {
            'past_hour': base_time - timedelta(hours=1),
            'past_day': base_time - timedelta(days=1),
            'past_week': base_time - timedelta(weeks=1),
            'future_hour': base_time + timedelta(hours=1),
            'future_day': base_time + timedelta(days=1),
            'future_week': base_time + timedelta(weeks=1)
        }