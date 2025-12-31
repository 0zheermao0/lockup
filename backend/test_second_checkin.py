#!/usr/bin/env python
"""
Test that verification codes are NOT updated on second check-in of the day
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

def test_no_update_on_second_checkin():
    """Test that verification codes are NOT updated on second check-in"""
    print("🧪 Testing that second check-in doesn't update verification codes...")

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

    # Create first check-in post
    first_post = Post.objects.create(
        user=user,
        content="First check-in post",
        post_type='checkin'
    )
    print(f"📝 Created first check-in post: {first_post.id}")

    # Get current verification code
    strict_task.refresh_from_db()
    code_after_first = strict_task.strict_code
    print(f"🔐 Code after first check-in: {code_after_first}")

    # Get current coins
    user.refresh_from_db()
    coins_after_first = user.coins
    print(f"💰 Coins after first check-in: {coins_after_first}")

    # Create second check-in post
    print(f"\n🎯 Creating second check-in post...")
    second_post = Post.objects.create(
        user=user,
        content="Second check-in post",
        post_type='checkin'
    )
    print(f"📝 Created second check-in post: {second_post.id}")

    # Process second check-in
    view = PostListCreateView()
    print(f"🔄 Calling _process_daily_checkin_reward for second check-in...")
    view._process_daily_checkin_reward(second_post)

    # Check results
    strict_task.refresh_from_db()
    user.refresh_from_db()

    code_after_second = strict_task.strict_code
    coins_after_second = user.coins

    print(f"\n📊 Results:")
    print(f"🔐 Code after second check-in: {code_after_second}")
    print(f"💰 Coins after second check-in: {coins_after_second}")

    # Verify no changes
    if code_after_first == code_after_second:
        print(f"✅ PASS: Verification code unchanged (as expected)")
    else:
        print(f"❌ FAIL: Verification code changed unexpectedly!")

    if coins_after_first == coins_after_second:
        print(f"✅ PASS: Coins unchanged (as expected)")
    else:
        print(f"❌ FAIL: Coins changed unexpectedly!")

    # Cleanup
    print(f"\n🧹 Cleaning up test posts...")
    first_post.delete()
    second_post.delete()

    print(f"✅ Second check-in test completed!")

if __name__ == '__main__':
    test_no_update_on_second_checkin()