#!/usr/bin/env python
"""
Debug the check-in logic to understand why it's not detecting existing check-ins
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

from tasks.models import LockTask
from posts.models import Post
from users.models import User

def debug_checkin_logic():
    """Debug the check-in detection logic"""
    print("🔍 Debugging check-in detection logic...")

    # Find a user with strict mode tasks
    strict_task = LockTask.objects.filter(
        strict_mode=True,
        status='active'
    ).first()

    if not strict_task:
        print("❌ No active strict mode tasks found")
        return

    user = strict_task.user
    today = timezone.now().date()
    print(f"👤 User: {user.username}")
    print(f"📅 Today: {today}")

    # Clear existing check-ins
    existing = Post.objects.filter(
        user=user,
        post_type='checkin',
        created_at__date=today
    )
    print(f"🧹 Clearing {existing.count()} existing check-ins")
    existing.delete()

    # Create first post
    first_post = Post.objects.create(
        user=user,
        content="First test post",
        post_type='checkin'
    )
    print(f"📝 Created first post: {first_post.id}")
    print(f"📅 First post date: {first_post.created_at.date()}")

    # Test the logic that would be used in the second post
    print(f"\n🔍 Testing logic for second post...")

    # This simulates what happens when processing the second post
    today_checkins = Post.objects.filter(
        user=user,
        post_type='checkin',
        created_at__date=today
    )
    print(f"📊 Found {today_checkins.count()} check-ins today (before exclusion)")

    for post in today_checkins:
        print(f"  - Post {post.id}: {post.created_at}")

    # Now create second post and test exclusion
    second_post = Post.objects.create(
        user=user,
        content="Second test post",
        post_type='checkin'
    )
    print(f"📝 Created second post: {second_post.id}")
    print(f"📅 Second post date: {second_post.created_at.date()}")

    # Test exclusion logic (what happens in _process_daily_checkin_reward)
    today_checkins_excluding_current = Post.objects.filter(
        user=user,
        post_type='checkin',
        created_at__date=today
    ).exclude(id=second_post.id)

    print(f"\n📊 Check-ins today excluding current post: {today_checkins_excluding_current.count()}")
    for post in today_checkins_excluding_current:
        print(f"  - Post {post.id}: {post.created_at}")

    should_skip = today_checkins_excluding_current.exists()
    print(f"\n🎯 Should skip reward/update: {should_skip}")

    if should_skip:
        print("✅ Logic working correctly - would skip on second check-in")
    else:
        print("❌ Logic not working - would NOT skip on second check-in")

    # Cleanup
    first_post.delete()
    second_post.delete()

if __name__ == '__main__':
    debug_checkin_logic()