#!/usr/bin/env python
"""
Test script to verify the new verification code update mechanism
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
from users.models import User

def test_verification_code_update():
    """Test the verification code update mechanism"""
    print("Testing verification code update mechanism...")

    # Find a user with strict mode tasks
    strict_task = LockTask.objects.filter(
        strict_mode=True,
        status='active'
    ).first()

    if not strict_task:
        print("❌ No active strict mode tasks found")
        return

    user = strict_task.user
    print(f"✅ Found user {user.username} with strict mode task: {strict_task.title}")
    print(f"📋 Current verification code: {strict_task.strict_code}")

    # Check if user has made a check-in today
    today = timezone.now().date()
    today_checkins = Post.objects.filter(
        user=user,
        post_type='checkin',
        created_at__date=today
    )

    if today_checkins.exists():
        print(f"⚠️  User already has {today_checkins.count()} check-in post(s) today")
        print("To test, we would need to create a check-in for a different user or wait until tomorrow")

        # Show what would happen
        print("\n🔍 Simulation: If this were the first check-in today:")
        print("1. User would get +1 coin reward")
        print("2. Verification codes would be updated for all strict mode tasks")
        print("3. Timeline events would be created")

        return

    print(f"✅ No check-in posts found for today - perfect for testing!")

    # Get all strict mode tasks for this user before update
    user_strict_tasks = LockTask.objects.filter(
        user=user,
        strict_mode=True,
        status='active'
    )

    print(f"\n📊 User has {user_strict_tasks.count()} active strict mode tasks:")
    for task in user_strict_tasks:
        print(f"  - {task.title}: {task.strict_code}")

    # Simulate creating a check-in post (but don't actually create it)
    print(f"\n🎯 Would trigger verification code update when user creates first check-in post today")
    print(f"💰 User current coins: {user.coins}")

    # Show timeline events before
    timeline_count_before = TaskTimelineEvent.objects.filter(
        task__in=user_strict_tasks,
        event_type='verification_code_updated'
    ).count()
    print(f"📈 Current verification update timeline events: {timeline_count_before}")

if __name__ == '__main__':
    test_verification_code_update()