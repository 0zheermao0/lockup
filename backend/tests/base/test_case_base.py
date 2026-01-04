#!/usr/bin/env python3
"""
Base Test Classes for Lockup Backend Unit Tests

This module provides comprehensive base test classes and utilities for testing
the Lockup backend system's core business logic:
- BaseBusinessLogicTestCase: Base class for business logic testing
- BaseCeleryTestCase: Base class for Celery task testing
- BaseViewTestCase: Base class for view testing
- Test fixtures and factory methods
- Mock utilities for external dependencies

Author: Claude Code
Created: 2026-01-04
"""

from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, datetime
from unittest.mock import patch, MagicMock
from decimal import Decimal
import json

from tasks.models import LockTask, TaskVote, TaskTimelineEvent, HourlyReward, PinnedUser
from posts.models import Post, Comment, PostLike, CheckinVote, CheckinVotingSession
from store.models import Item, ItemType, Game, GameParticipant, GameSession, BuriedTreasure, DriftBottle
from users.models import User

User = get_user_model()


class BaseBusinessLogicTestCase(TestCase):
    """Base test case for business logic unit tests"""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests"""
        # Create comprehensive test users with different levels and states
        cls.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@lockup.test',
            password='secure_test_pass_123',
            is_superuser=True,
            is_staff=True,
            level=5,
            coins=10000,
            activity_score=1000
        )

        cls.user_level1 = User.objects.create_user(
            username='level1_user',
            email='level1@lockup.test',
            password='test_pass_123',
            level=1,
            coins=50,
            activity_score=10
        )

        cls.user_level2 = User.objects.create_user(
            username='level2_user',
            email='level2@lockup.test',
            password='test_pass_123',
            level=2,
            coins=150,
            activity_score=50
        )

        cls.user_level3 = User.objects.create_user(
            username='level3_user',
            email='level3@lockup.test',
            password='test_pass_123',
            level=3,
            coins=300,
            activity_score=150
        )

        cls.user_level4 = User.objects.create_user(
            username='level4_user',
            email='level4@lockup.test',
            password='test_pass_123',
            level=4,
            coins=500,
            activity_score=300
        )

        cls.user_level5 = User.objects.create_user(
            username='level5_user',
            email='level5@lockup.test',
            password='test_pass_123',
            level=5,
            coins=1000,
            activity_score=500
        )

        # Create test item types for comprehensive testing
        cls.key_item_type = ItemType.objects.create(
            name='key',
            display_name='钥匙',
            description='用于完成带锁任务的钥匙',
            price=0,
            max_quantity=1,
            is_consumable=True
        )

        cls.universal_key_type = ItemType.objects.create(
            name='universal_key',
            display_name='万能钥匙',
            description='可以完成任何带锁任务的万能钥匙',
            price=100,
            max_quantity=5,
            is_consumable=True
        )

        cls.time_wheel_type = ItemType.objects.create(
            name='time_wheel',
            display_name='时间轮盘',
            description='可以修改任务时间的神奇轮盘',
            price=50,
            max_quantity=3,
            is_consumable=True
        )

        cls.photo_paper_type = ItemType.objects.create(
            name='photo_paper',
            display_name='照片纸',
            description='用于拍摄照片的特殊纸张',
            price=10,
            max_quantity=10,
            is_consumable=True
        )

        cls.detection_radar_type = ItemType.objects.create(
            name='detection_radar',
            display_name='探测雷达',
            description='探测周围物品的神奇雷达',
            price=30,
            max_quantity=5,
            is_consumable=True
        )

        cls.treasury_type = ItemType.objects.create(
            name='treasury',
            display_name='小金库',
            description='可以存储积分的小金库',
            price=200,
            max_quantity=1,
            is_consumable=False
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
        self.user_level5.refresh_from_db()

        # Store original coins for change tracking
        self._store_original_coins()

    def _store_original_coins(self):
        """Store original coin amounts for change tracking"""
        for user in [self.admin_user, self.user_level1, self.user_level2,
                    self.user_level3, self.user_level4, self.user_level5]:
            setattr(user, '_original_coins', user.coins)

    # Factory methods for creating test data
    def create_test_lock_task(self, user, **kwargs):
        """Create a test lock task with sensible defaults"""
        defaults = {
            'user': user,
            'task_type': 'lock',
            'status': 'pending',
            'difficulty': 'medium',
            'start_time': timezone.now(),
            'end_time': timezone.now() + timedelta(hours=2),
            'is_frozen': False,
            'unlock_type': 'time',
            'vote_threshold': 1,
            'vote_agreement_ratio': 0.5
        }
        defaults.update(kwargs)
        return LockTask.objects.create(**defaults)

    def create_test_board_task(self, creator, **kwargs):
        """Create a test board task with sensible defaults"""
        defaults = {
            'user': creator,
            'task_type': 'board',
            'status': 'pending',
            'difficulty': 'easy',
            'reward_amount': 50,
            'max_participants': 5,
            'deadline': timezone.now() + timedelta(days=7)
        }
        defaults.update(kwargs)
        return LockTask.objects.create(**defaults)

    def create_test_post(self, author, **kwargs):
        """Create a test post with sensible defaults"""
        defaults = {
            'author': author,
            'content': 'Test post content for unit testing',
            'post_type': 'normal',
            'is_public': True
        }
        defaults.update(kwargs)
        return Post.objects.create(**defaults)

    def create_test_comment(self, post, author, **kwargs):
        """Create a test comment with sensible defaults"""
        defaults = {
            'post': post,
            'author': author,
            'content': 'Test comment content'
        }
        defaults.update(kwargs)
        return Comment.objects.create(**defaults)

    def create_test_item(self, owner, item_type, **kwargs):
        """Create a test item with sensible defaults"""
        defaults = {
            'owner': owner,
            'original_owner': owner,
            'item_type': item_type,
            'status': 'available',
            'properties': {}
        }
        defaults.update(kwargs)
        return Item.objects.create(**defaults)

    def create_test_game_session(self, game_type, **kwargs):
        """Create a test game session with sensible defaults"""
        defaults = {
            'game_type': game_type,
            'status': 'pending',
            'max_participants': 4,
            'entry_fee': 10
        }
        defaults.update(kwargs)
        return GameSession.objects.create(**defaults)

    # Assertion helpers
    def assert_user_coins_changed(self, user, expected_change):
        """Assert that user's coins changed by expected amount"""
        user.refresh_from_db()
        original_coins = getattr(user, '_original_coins', user.coins - expected_change)
        actual_change = user.coins - original_coins
        self.assertEqual(
            actual_change,
            expected_change,
            f"Expected coins change of {expected_change}, got {actual_change}. "
            f"Original: {original_coins}, Current: {user.coins}"
        )

    def assert_user_has_item(self, user, item_type_name, quantity=1, status='available'):
        """Assert that user has specific item quantity"""
        item_count = Item.objects.filter(
            owner=user,
            item_type__name=item_type_name,
            status=status
        ).count()
        self.assertEqual(
            item_count,
            quantity,
            f"Expected {quantity} {item_type_name} items with status '{status}', found {item_count}"
        )

    def assert_task_status(self, task, expected_status):
        """Assert that task has expected status"""
        task.refresh_from_db()
        self.assertEqual(
            task.status,
            expected_status,
            f"Expected task status '{expected_status}', got '{task.status}'"
        )

    def assert_task_frozen(self, task, is_frozen=True):
        """Assert that task is frozen/unfrozen as expected"""
        task.refresh_from_db()
        self.assertEqual(
            task.is_frozen,
            is_frozen,
            f"Expected task.is_frozen to be {is_frozen}, got {task.is_frozen}"
        )

    def assert_timeline_event_created(self, task, event_type, user=None):
        """Assert that a timeline event was created for the task"""
        events = TaskTimelineEvent.objects.filter(
            task=task,
            event_type=event_type
        )
        if user:
            events = events.filter(user=user)

        self.assertTrue(
            events.exists(),
            f"Expected timeline event '{event_type}' for task {task.id}"
            f"{f' by user {user.username}' if user else ''}"
        )

    def assert_vote_exists(self, task, user, vote_type):
        """Assert that a vote exists for the task"""
        vote = TaskVote.objects.filter(
            task=task,
            user=user,
            vote_type=vote_type
        ).exists()
        self.assertTrue(
            vote,
            f"Expected {vote_type} vote by {user.username} for task {task.id}"
        )

    def assert_hourly_reward_created(self, task, user, amount):
        """Assert that an hourly reward was created"""
        reward = HourlyReward.objects.filter(
            task=task,
            user=user,
            amount=amount
        ).exists()
        self.assertTrue(
            reward,
            f"Expected hourly reward of {amount} for user {user.username} on task {task.id}"
        )

    # Mock utilities
    def mock_timezone_now(self, fixed_time=None):
        """Mock timezone.now() to return fixed time"""
        if fixed_time is None:
            fixed_time = timezone.now()
        return patch('django.utils.timezone.now', return_value=fixed_time)

    def mock_celery_task(self, task_function):
        """Mock a Celery task to run synchronously"""
        def sync_task(*args, **kwargs):
            return task_function(*args, **kwargs)
        return patch.object(task_function, 'delay', side_effect=sync_task)

    def mock_random_choice(self, fixed_choice):
        """Mock random.choice to return fixed value"""
        return patch('random.choice', return_value=fixed_choice)

    def mock_random_randint(self, fixed_value):
        """Mock random.randint to return fixed value"""
        return patch('random.randint', return_value=fixed_value)


class BaseCeleryTestCase(BaseBusinessLogicTestCase):
    """Base test case for Celery task testing"""

    def setUp(self):
        """Set up Celery testing environment"""
        super().setUp()
        # Mock Celery configuration for testing
        self.celery_always_eager = patch('celery.current_app.conf.task_always_eager', True)
        self.celery_eager_propagates = patch('celery.current_app.conf.task_eager_propagates', True)

        self.celery_always_eager.start()
        self.celery_eager_propagates.start()

    def tearDown(self):
        """Clean up Celery mocks"""
        super().tearDown()
        self.celery_always_eager.stop()
        self.celery_eager_propagates.stop()

    def mock_celery_retry(self, task_function, max_retries=3):
        """Mock Celery task retry behavior"""
        def mock_retry(*args, **kwargs):
            # Simulate retry logic without actual delay
            retry_count = getattr(mock_retry, '_retry_count', 0)
            if retry_count < max_retries:
                mock_retry._retry_count = retry_count + 1
                raise Exception(f"Simulated retry {retry_count + 1}")
            return task_function(*args, **kwargs)

        return patch.object(task_function, 'retry', side_effect=mock_retry)


class BaseViewTestCase(BaseBusinessLogicTestCase):
    """Base test case for view testing"""

    def setUp(self):
        """Set up view testing environment"""
        super().setUp()
        self.client = Client()

    def authenticate_user(self, user):
        """Authenticate a user for API testing"""
        self.client.force_login(user)

    def post_json(self, url, data=None, user=None):
        """Make a JSON POST request"""
        if user:
            self.authenticate_user(user)
        return self.client.post(
            url,
            data=json.dumps(data or {}),
            content_type='application/json'
        )

    def get_json(self, url, user=None):
        """Make a JSON GET request"""
        if user:
            self.authenticate_user(user)
        return self.client.get(url, HTTP_ACCEPT='application/json')

    def assert_response_success(self, response, expected_status=200):
        """Assert that response is successful"""
        self.assertEqual(
            response.status_code,
            expected_status,
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {getattr(response, 'content', '')}"
        )

    def assert_response_error(self, response, expected_status=400):
        """Assert that response contains expected error"""
        self.assertEqual(
            response.status_code,
            expected_status,
            f"Expected error status {expected_status}, got {response.status_code}"
        )

    def assert_response_contains(self, response, expected_content):
        """Assert that response contains expected content"""
        content = response.content.decode('utf-8')
        self.assertIn(
            expected_content,
            content,
            f"Expected '{expected_content}' in response content"
        )


class BaseTransactionTestCase(TransactionTestCase):
    """Base test case for testing transaction behavior"""

    def setUp(self):
        """Set up transaction testing environment"""
        super().setUp()
        # Create minimal test data for transaction tests
        self.admin_user = User.objects.create_user(
            username='admin_tx',
            email='admin@lockup.test',
            password='test_pass_123',
            is_superuser=True,
            level=5,
            coins=10000
        )

        self.test_user = User.objects.create_user(
            username='user_tx',
            email='user@lockup.test',
            password='test_pass_123',
            level=2,
            coins=200
        )


class TestDataMixin:
    """Mixin providing common test data creation utilities"""

    def create_complete_lock_task_scenario(self, user):
        """Create a complete lock task testing scenario"""
        # Create the task
        task = self.create_test_lock_task(user, status='active')

        # Create the key item
        key_item = self.create_test_item(
            owner=user,
            item_type=self.key_item_type,
            properties={'task_id': str(task.id)}
        )

        # Create some timeline events
        TaskTimelineEvent.objects.create(
            task=task,
            user=user,
            event_type='task_started',
            description='Task started by user'
        )

        return task, key_item

    def create_voting_task_scenario(self, user, voters=None):
        """Create a voting task testing scenario"""
        if voters is None:
            voters = [self.user_level2, self.user_level3]

        # Create voting task
        task = self.create_test_lock_task(
            user=user,
            status='voting',
            unlock_type='vote',
            vote_threshold=len(voters),
            vote_agreement_ratio=0.6
        )

        # Create votes
        votes = []
        for i, voter in enumerate(voters):
            vote_type = 'agree' if i % 2 == 0 else 'disagree'
            vote = TaskVote.objects.create(
                task=task,
                user=voter,
                vote_type=vote_type
            )
            votes.append(vote)

        return task, votes

    def create_multi_user_task_scenario(self, creator, participants=None):
        """Create a multi-user task testing scenario"""
        if participants is None:
            participants = [self.user_level1, self.user_level2]

        # Create board task
        task = self.create_test_board_task(
            creator=creator,
            status='active',
            max_participants=len(participants) + 1
        )

        # Add participants
        for participant in participants:
            task.participants.add(participant)

        return task, participants


class MockHelpers:
    """Helper class for mocking external dependencies"""

    @staticmethod
    def mock_notification_creation():
        """Mock notification creation to avoid dependencies"""
        return patch('users.models.Notification.objects.create')

    @staticmethod
    def mock_telegram_service():
        """Mock Telegram service for notification testing"""
        return patch('telegram_bot.services.send_notification')

    @staticmethod
    def mock_file_upload():
        """Mock file upload functionality"""
        return patch('django.core.files.storage.default_storage.save')

    @staticmethod
    def mock_geolocation_service():
        """Mock geolocation service"""
        return patch('utils.location.get_location_info')

    @staticmethod
    def create_mock_celery_result(task_id='test-task-id', status='SUCCESS', result=None):
        """Create a mock Celery task result"""
        mock_result = MagicMock()
        mock_result.id = task_id
        mock_result.status = status
        mock_result.result = result or {'status': 'success'}
        mock_result.successful.return_value = (status == 'SUCCESS')
        mock_result.failed.return_value = (status == 'FAILURE')
        return mock_result