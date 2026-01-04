#!/usr/bin/env python3
"""
Test Data Factories for Lockup Backend Unit Tests

This module provides factory classes for creating test data with realistic
relationships and constraints. Factories use the Factory Boy pattern but
are implemented as simple classes to avoid external dependencies.

Author: Claude Code
Created: 2026-01-04
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random
import string

from tasks.models import LockTask, TaskVote, TaskTimelineEvent, HourlyReward
from posts.models import Post, Comment, PostLike, CheckinVote
from store.models import Item, ItemType, Game, GameParticipant, GameSession
from users.models import User

User = get_user_model()


class BaseFactory:
    """Base factory class with common utilities"""

    @staticmethod
    def generate_random_string(length=8):
        """Generate a random string of specified length"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    @staticmethod
    def generate_email(username=None):
        """Generate a test email address"""
        if username is None:
            username = BaseFactory.generate_random_string()
        return f"{username}@lockup.test"

    @staticmethod
    def generate_past_time(hours_ago=1):
        """Generate a past timestamp"""
        return timezone.now() - timedelta(hours=hours_ago)

    @staticmethod
    def generate_future_time(hours_ahead=1):
        """Generate a future timestamp"""
        return timezone.now() + timedelta(hours=hours_ahead)


class UserFactory(BaseFactory):
    """Factory for creating test users"""

    @classmethod
    def create_user(cls, **kwargs):
        """Create a test user with realistic defaults"""
        defaults = {
            'username': f'user_{cls.generate_random_string()}',
            'password': 'test_password_123',
            'level': random.randint(1, 5),
            'coins': random.randint(50, 500),
            'activity_score': random.randint(10, 1000),
            'is_active': True
        }
        defaults.update(kwargs)

        # Generate email if not provided
        if 'email' not in defaults:
            defaults['email'] = cls.generate_email(defaults['username'])

        return User.objects.create_user(**defaults)

    @classmethod
    def create_admin_user(cls, **kwargs):
        """Create an admin test user"""
        defaults = {
            'username': f'admin_{cls.generate_random_string()}',
            'is_superuser': True,
            'is_staff': True,
            'level': 5,
            'coins': 10000,
            'activity_score': 1000
        }
        defaults.update(kwargs)
        return cls.create_user(**defaults)

    @classmethod
    def create_users_by_level(cls, count_per_level=2):
        """Create users for each level (1-5)"""
        users = {}
        for level in range(1, 6):
            users[level] = []
            for i in range(count_per_level):
                user = cls.create_user(
                    level=level,
                    coins=level * 100,
                    activity_score=level * 50
                )
                users[level].append(user)
        return users

    @classmethod
    def create_user_with_items(cls, item_types=None, **user_kwargs):
        """Create a user with specific items"""
        user = cls.create_user(**user_kwargs)

        if item_types:
            for item_type_name, quantity in item_types.items():
                try:
                    item_type = ItemType.objects.get(name=item_type_name)
                    for _ in range(quantity):
                        ItemFactory.create_item(owner=user, item_type=item_type)
                except ItemType.DoesNotExist:
                    # Skip if item type doesn't exist in test
                    pass

        return user


class ItemTypeFactory(BaseFactory):
    """Factory for creating test item types"""

    @classmethod
    def create_item_type(cls, **kwargs):
        """Create a test item type"""
        defaults = {
            'name': f'item_{cls.generate_random_string()}',
            'display_name': f'Test Item {cls.generate_random_string().upper()}',
            'description': 'A test item for unit testing',
            'price': random.randint(10, 100),
            'max_quantity': random.randint(1, 10),
            'is_consumable': random.choice([True, False])
        }
        defaults.update(kwargs)
        return ItemType.objects.create(**defaults)

    @classmethod
    def create_standard_item_types(cls):
        """Create standard item types used in testing"""
        item_types = {}

        # Key item type
        item_types['key'] = ItemType.objects.create(
            name='key',
            display_name='钥匙',
            description='用于完成带锁任务的钥匙',
            price=0,
            max_quantity=1,
            is_consumable=True
        )

        # Universal key
        item_types['universal_key'] = ItemType.objects.create(
            name='universal_key',
            display_name='万能钥匙',
            description='可以完成任何带锁任务的万能钥匙',
            price=100,
            max_quantity=5,
            is_consumable=True
        )

        # Time wheel
        item_types['time_wheel'] = ItemType.objects.create(
            name='time_wheel',
            display_name='时间轮盘',
            description='可以修改任务时间的神奇轮盘',
            price=50,
            max_quantity=3,
            is_consumable=True
        )

        # Photo paper
        item_types['photo_paper'] = ItemType.objects.create(
            name='photo_paper',
            display_name='照片纸',
            description='用于拍摄照片的特殊纸张',
            price=10,
            max_quantity=10,
            is_consumable=True
        )

        # Detection radar
        item_types['detection_radar'] = ItemType.objects.create(
            name='detection_radar',
            display_name='探测雷达',
            description='探测周围物品的神奇雷达',
            price=30,
            max_quantity=5,
            is_consumable=True
        )

        return item_types


class ItemFactory(BaseFactory):
    """Factory for creating test items"""

    @classmethod
    def create_item(cls, **kwargs):
        """Create a test item"""
        defaults = {
            'status': 'available',
            'properties': {}
        }
        defaults.update(kwargs)

        # Ensure owner and original_owner are set
        if 'owner' in defaults and 'original_owner' not in defaults:
            defaults['original_owner'] = defaults['owner']

        return Item.objects.create(**defaults)

    @classmethod
    def create_task_key(cls, task, owner=None):
        """Create a key item for a specific task"""
        if owner is None:
            owner = task.user

        key_type, _ = ItemType.objects.get_or_create(
            name='key',
            defaults={
                'display_name': '钥匙',
                'description': '用于完成带锁任务的钥匙',
                'price': 0,
                'max_quantity': 1,
                'is_consumable': True
            }
        )

        return cls.create_item(
            owner=owner,
            original_owner=owner,
            item_type=key_type,
            properties={'task_id': str(task.id)}
        )

    @classmethod
    def create_universal_key(cls, owner):
        """Create a universal key item"""
        universal_key_type, _ = ItemType.objects.get_or_create(
            name='universal_key',
            defaults={
                'display_name': '万能钥匙',
                'description': '可以完成任何带锁任务的万能钥匙',
                'price': 100,
                'max_quantity': 5,
                'is_consumable': True
            }
        )

        return cls.create_item(
            owner=owner,
            original_owner=owner,
            item_type=universal_key_type
        )


class LockTaskFactory(BaseFactory):
    """Factory for creating test lock tasks"""

    @classmethod
    def create_lock_task(cls, **kwargs):
        """Create a test lock task"""
        defaults = {
            'task_type': 'lock',
            'status': 'pending',
            'difficulty': random.choice(['easy', 'medium', 'hard', 'extreme']),
            'start_time': timezone.now(),
            'end_time': cls.generate_future_time(hours_ahead=2),
            'is_frozen': False,
            'unlock_type': 'time',
            'vote_threshold': 1,
            'vote_agreement_ratio': 0.5
        }
        defaults.update(kwargs)
        return LockTask.objects.create(**defaults)

    @classmethod
    def create_active_task(cls, user, **kwargs):
        """Create an active lock task"""
        defaults = {
            'user': user,
            'status': 'active',
            'start_time': cls.generate_past_time(hours_ago=1),
            'end_time': cls.generate_future_time(hours_ahead=1)
        }
        defaults.update(kwargs)
        return cls.create_lock_task(**defaults)

    @classmethod
    def create_voting_task(cls, user, **kwargs):
        """Create a voting lock task"""
        defaults = {
            'user': user,
            'status': 'voting',
            'unlock_type': 'vote',
            'start_time': cls.generate_past_time(hours_ago=2),
            'end_time': cls.generate_past_time(hours_ago=0.5),
            'vote_threshold': 3,
            'vote_agreement_ratio': 0.6
        }
        defaults.update(kwargs)
        return cls.create_lock_task(**defaults)

    @classmethod
    def create_completed_task(cls, user, **kwargs):
        """Create a completed lock task"""
        defaults = {
            'user': user,
            'status': 'completed',
            'start_time': cls.generate_past_time(hours_ago=4),
            'end_time': cls.generate_past_time(hours_ago=2),
            'completed_at': cls.generate_past_time(hours_ago=2)
        }
        defaults.update(kwargs)
        return cls.create_lock_task(**defaults)

    @classmethod
    def create_task_with_key(cls, user, **kwargs):
        """Create a lock task with corresponding key item"""
        task = cls.create_lock_task(user=user, **kwargs)
        key = ItemFactory.create_task_key(task, user)
        return task, key

    @classmethod
    def create_board_task(cls, **kwargs):
        """Create a board task"""
        defaults = {
            'task_type': 'board',
            'status': 'pending',
            'reward_amount': random.randint(50, 500),
            'max_participants': random.randint(1, 10),
            'deadline': cls.generate_future_time(hours_ahead=24 * 7)  # 1 week
        }
        defaults.update(kwargs)
        return LockTask.objects.create(**defaults)


class TaskVoteFactory(BaseFactory):
    """Factory for creating task votes"""

    @classmethod
    def create_vote(cls, task, user, **kwargs):
        """Create a task vote"""
        defaults = {
            'vote_type': random.choice(['agree', 'disagree']),
            'created_at': timezone.now()
        }
        defaults.update(kwargs)
        return TaskVote.objects.create(task=task, user=user, **defaults)

    @classmethod
    def create_votes_for_task(cls, task, voters, agree_ratio=0.5):
        """Create multiple votes for a task"""
        votes = []
        agree_count = int(len(voters) * agree_ratio)

        for i, voter in enumerate(voters):
            vote_type = 'agree' if i < agree_count else 'disagree'
            vote = cls.create_vote(task, voter, vote_type=vote_type)
            votes.append(vote)

        return votes


class TaskTimelineEventFactory(BaseFactory):
    """Factory for creating task timeline events"""

    @classmethod
    def create_event(cls, task, **kwargs):
        """Create a task timeline event"""
        defaults = {
            'event_type': random.choice([
                'task_created', 'task_started', 'task_completed',
                'vote_cast', 'time_added', 'hourly_reward_distributed'
            ]),
            'description': f'Test timeline event: {cls.generate_random_string()}',
            'created_at': timezone.now()
        }
        defaults.update(kwargs)
        return TaskTimelineEvent.objects.create(task=task, **defaults)

    @classmethod
    def create_task_lifecycle_events(cls, task, user):
        """Create a complete set of lifecycle events for a task"""
        events = []

        # Task created
        events.append(cls.create_event(
            task=task,
            user=user,
            event_type='task_created',
            description=f'Task created by {user.username}'
        ))

        # Task started
        events.append(cls.create_event(
            task=task,
            user=user,
            event_type='task_started',
            description=f'Task started by {user.username}'
        ))

        # Add some hourly rewards if task is active
        if task.status == 'active':
            for hour in range(1, 3):
                events.append(cls.create_event(
                    task=task,
                    user=user,
                    event_type='hourly_reward_distributed',
                    description=f'Hourly reward distributed (hour {hour})'
                ))

        return events


class PostFactory(BaseFactory):
    """Factory for creating test posts"""

    @classmethod
    def create_post(cls, **kwargs):
        """Create a test post"""
        defaults = {
            'content': f'Test post content {cls.generate_random_string()}',
            'post_type': 'normal',
            'is_public': True,
            'created_at': timezone.now()
        }
        defaults.update(kwargs)
        return Post.objects.create(**defaults)

    @classmethod
    def create_checkin_post(cls, author, **kwargs):
        """Create a checkin post with location"""
        defaults = {
            'author': author,
            'post_type': 'checkin',
            'latitude': 39.9042 + random.uniform(-0.1, 0.1),  # Beijing area
            'longitude': 116.4074 + random.uniform(-0.1, 0.1),
            'location_name': f'Test Location {cls.generate_random_string()}'
        }
        defaults.update(kwargs)
        return cls.create_post(**defaults)

    @classmethod
    def create_task_share_post(cls, author, task, **kwargs):
        """Create a task sharing post"""
        defaults = {
            'author': author,
            'post_type': 'task_share',
            'content': f'Sharing my task: {task.id}',
            'related_task': task
        }
        defaults.update(kwargs)
        return cls.create_post(**defaults)


class CommentFactory(BaseFactory):
    """Factory for creating test comments"""

    @classmethod
    def create_comment(cls, post, author, **kwargs):
        """Create a test comment"""
        defaults = {
            'content': f'Test comment {cls.generate_random_string()}',
            'created_at': timezone.now()
        }
        defaults.update(kwargs)
        return Comment.objects.create(post=post, author=author, **defaults)

    @classmethod
    def create_comment_thread(cls, post, authors, depth=2):
        """Create a comment thread with nested replies"""
        comments = []

        # Create root comment
        root_comment = cls.create_comment(
            post=post,
            author=authors[0],
            content='Root comment'
        )
        comments.append(root_comment)

        # Create replies if depth > 1
        if depth > 1 and len(authors) > 1:
            for i in range(1, min(len(authors), depth)):
                reply = cls.create_comment(
                    post=post,
                    author=authors[i],
                    content=f'Reply level {i}',
                    parent=root_comment
                )
                comments.append(reply)

        return comments


class GameFactory(BaseFactory):
    """Factory for creating test games and game sessions"""

    @classmethod
    def create_game_session(cls, **kwargs):
        """Create a test game session"""
        defaults = {
            'game_type': random.choice(['time_wheel', 'dice', 'rock_paper_scissors']),
            'status': 'pending',
            'max_participants': random.randint(1, 4),
            'entry_fee': random.randint(10, 50),
            'created_at': timezone.now()
        }
        defaults.update(kwargs)
        return GameSession.objects.create(**defaults)

    @classmethod
    def create_time_wheel_session(cls, **kwargs):
        """Create a time wheel game session"""
        defaults = {
            'game_type': 'time_wheel',
            'max_participants': 1,
            'entry_fee': 20
        }
        defaults.update(kwargs)
        return cls.create_game_session(**defaults)

    @classmethod
    def create_dice_session(cls, **kwargs):
        """Create a dice game session"""
        defaults = {
            'game_type': 'dice',
            'max_participants': 4,
            'entry_fee': 10
        }
        defaults.update(kwargs)
        return cls.create_game_session(**defaults)

    @classmethod
    def create_game_with_participants(cls, participants, **kwargs):
        """Create a game session with participants"""
        game_session = cls.create_game_session(**kwargs)

        for participant in participants:
            GameParticipant.objects.create(
                game_session=game_session,
                user=participant,
                action='',  # Will be set when game starts
                joined_at=timezone.now()
            )

        return game_session


class HourlyRewardFactory(BaseFactory):
    """Factory for creating hourly rewards"""

    @classmethod
    def create_reward(cls, task, user, **kwargs):
        """Create an hourly reward"""
        defaults = {
            'amount': random.randint(5, 25),
            'hour': random.randint(1, 24),
            'created_at': timezone.now()
        }
        defaults.update(kwargs)
        return HourlyReward.objects.create(task=task, user=user, **defaults)

    @classmethod
    def create_rewards_for_task(cls, task, hours_count=3):
        """Create multiple hourly rewards for a task"""
        rewards = []
        for hour in range(1, hours_count + 1):
            reward = cls.create_reward(
                task=task,
                user=task.user,
                hour=hour,
                amount=10 + (hour * 2)  # Increasing reward
            )
            rewards.append(reward)
        return rewards


class ScenarioFactory(BaseFactory):
    """Factory for creating complex test scenarios"""

    @classmethod
    def create_complete_task_scenario(cls, user):
        """Create a complete task scenario with all related objects"""
        # Create the task
        task = LockTaskFactory.create_active_task(user)

        # Create the key
        key = ItemFactory.create_task_key(task, user)

        # Create timeline events
        events = TaskTimelineEventFactory.create_task_lifecycle_events(task, user)

        # Create hourly rewards
        rewards = HourlyRewardFactory.create_rewards_for_task(task)

        return {
            'task': task,
            'key': key,
            'events': events,
            'rewards': rewards
        }

    @classmethod
    def create_voting_scenario(cls, task_user, voters):
        """Create a voting scenario with task and votes"""
        # Create voting task
        task = LockTaskFactory.create_voting_task(task_user)

        # Create votes
        votes = TaskVoteFactory.create_votes_for_task(task, voters, agree_ratio=0.7)

        return {
            'task': task,
            'votes': votes,
            'voters': voters
        }

    @classmethod
    def create_social_scenario(cls, users):
        """Create a social scenario with posts, comments, and interactions"""
        if len(users) < 2:
            raise ValueError("Need at least 2 users for social scenario")

        author = users[0]
        commenters = users[1:]

        # Create a post
        post = PostFactory.create_checkin_post(author)

        # Create comments
        comments = CommentFactory.create_comment_thread(post, commenters)

        # Create likes
        likes = []
        for user in commenters:
            like, created = PostLike.objects.get_or_create(
                post=post,
                user=user
            )
            if created:
                likes.append(like)

        return {
            'post': post,
            'comments': comments,
            'likes': likes,
            'author': author,
            'commenters': commenters
        }