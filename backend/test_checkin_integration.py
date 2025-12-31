#!/usr/bin/env python
"""
Integration test for the verification code update mechanism
This test simulates creating a check-in post and verifies the verification code update
"""

import os
import sys
import django
from django.utils import timezone

# Add the backend directory to the Python path
sys.path.append('/Users/joey/code/lockup/backend')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from tasks.models import LockTask, TaskTimelineEvent
from posts.models import Post
from posts.views import PostListCreateView
from users.models import User
from django.test import RequestFactory
from unittest.mock import Mock

def test_verification_code_update_integration():
    """Integration test for verification code update on first daily check-in"""
    print("🧪 Testing verification code update integration...")

    # Find a user with strict mode tasks
    strict_task = LockTask.objects.filter(
        strict_mode=True,
        status='active'
    ).first()

    if not strict_task:
        print("❌ No active strict mode tasks found")
        return

    user = strict_task.user
    print(f"✅ Testing with user: {user.username}")
    print(f"📋 Task: {strict_task.title}")
    print(f"🔐 Current verification code: {strict_task.strict_code}")

    # Check if user has made a check-in today
    today = timezone.now().date()
    today_checkins = Post.objects.filter(
        user=user,
        post_type='checkin',
        created_at__date=today
    )

    if today_checkins.exists():
        print(f"⚠️  User already has check-in posts today. Deleting them for test...")
        today_checkins.delete()

    # Get all strict mode tasks for this user before update
    user_strict_tasks = LockTask.objects.filter(
        user=user,
        strict_mode=True,
        status='active'
    )

    print(f"\n📊 User has {user_strict_tasks.count()} active strict mode tasks")

    # Capture current state
    initial_codes = {}
    for task in user_strict_tasks:
        initial_codes[task.id] = task.strict_code
        print(f"  - {task.title}: {task.strict_code}")

    initial_coins = user.coins
    print(f"💰 Initial coins: {initial_coins}")

    # Count initial timeline events
    initial_timeline_events = TaskTimelineEvent.objects.filter(
        task__in=user_strict_tasks,
        event_type='verification_code_updated'
    ).count()
    print(f"📈 Initial verification update events: {initial_timeline_events}")

    # Create a mock post to test the verification code update logic
    print(f"\n🎯 Creating test check-in post...")

    # Create a test post
    post = Post.objects.create(
        user=user,
        content="Test check-in post for verification code update",
        post_type='checkin'
    )
    print(f"✅ Created post: {post.id}")

    # Manually call the verification code update method
    # Create a view instance to test the method
    view = PostListCreateView()

    print(f"🔄 Calling _process_daily_checkin_reward...")
    view._process_daily_checkin_reward(post)

    # Check results
    print(f"\n📊 Results:")

    # Refresh user from database
    user.refresh_from_db()
    print(f"💰 Coins after: {user.coins} (change: +{user.coins - initial_coins})")

    # Check verification codes
    updated_codes = {}
    for task in user_strict_tasks:
        task.refresh_from_db()
        updated_codes[task.id] = task.strict_code
        changed = "✅ CHANGED" if initial_codes[task.id] != task.strict_code else "❌ NO CHANGE"
        print(f"🔐 {task.title}: {initial_codes[task.id]} → {task.strict_code} {changed}")

    # Check timeline events
    final_timeline_events = TaskTimelineEvent.objects.filter(
        task__in=user_strict_tasks,
        event_type='verification_code_updated'
    ).count()
    new_events = final_timeline_events - initial_timeline_events
    print(f"📈 New verification update events: {new_events}")

    if new_events > 0:
        print(f"📋 Latest timeline events:")
        latest_events = TaskTimelineEvent.objects.filter(
            task__in=user_strict_tasks,
            event_type='verification_code_updated'
        ).order_by('-created_at')[:new_events]

        for event in latest_events:
            print(f"  - {event.description}")
            print(f"    Metadata: {event.metadata}")

    # Cleanup
    print(f"\n🧹 Cleaning up test post...")
    post.delete()

    print(f"\n✅ Integration test completed!")

if __name__ == '__main__':
    test_verification_code_update_integration()