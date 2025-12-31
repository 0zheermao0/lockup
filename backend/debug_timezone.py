#!/usr/bin/env python
"""
Debug timezone issues with check-in detection
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

def debug_timezone():
    """Debug timezone handling"""
    print("🌍 Debugging timezone handling...")

    now = timezone.now()
    today = now.date()

    print(f"🕐 Current timezone.now(): {now}")
    print(f"📅 Today (from timezone.now().date()): {today}")
    print(f"🌍 Timezone: {now.tzinfo}")

    # Find a user with strict mode tasks
    strict_task = LockTask.objects.filter(
        strict_mode=True,
        status='active'
    ).first()

    user = strict_task.user
    print(f"👤 User: {user.username}")

    # Clear existing
    Post.objects.filter(user=user, post_type='checkin').delete()

    # Create a test post
    post = Post.objects.create(
        user=user,
        content="Test post",
        post_type='checkin'
    )

    print(f"\n📝 Created post: {post.id}")
    print(f"🕐 Post created_at: {post.created_at}")
    print(f"📅 Post date: {post.created_at.date()}")
    print(f"🌍 Post timezone: {post.created_at.tzinfo}")

    # Test different ways of querying
    print(f"\n🔍 Testing different query methods:")

    # Method 1: Using created_at__date
    method1 = Post.objects.filter(
        user=user,
        post_type='checkin',
        created_at__date=today
    )
    print(f"Method 1 (created_at__date=today): {method1.count()} posts")

    # Method 2: Using created_at__date with post's date
    method2 = Post.objects.filter(
        user=user,
        post_type='checkin',
        created_at__date=post.created_at.date()
    )
    print(f"Method 2 (created_at__date=post.date): {method2.count()} posts")

    # Method 3: Range query
    start_of_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timezone.timedelta(days=1)
    method3 = Post.objects.filter(
        user=user,
        post_type='checkin',
        created_at__gte=start_of_day,
        created_at__lt=end_of_day
    )
    print(f"Method 3 (range query): {method3.count()} posts")
    print(f"  Range: {start_of_day} to {end_of_day}")

    # Check all posts for this user
    all_posts = Post.objects.filter(user=user, post_type='checkin')
    print(f"\n📊 All check-in posts for user:")
    for p in all_posts:
        print(f"  - {p.id}: {p.created_at} (date: {p.created_at.date()})")

    # Cleanup
    post.delete()

if __name__ == '__main__':
    debug_timezone()