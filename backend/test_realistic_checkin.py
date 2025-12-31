#!/usr/bin/env python
"""
More realistic test that simulates the actual post creation flow
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

def test_realistic_checkin_flow():
    """Test the actual check-in flow more realistically"""
    print("🧪 Testing realistic check-in flow...")

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

    # Clear any existing check-ins today to ensure clean test
    today = timezone.now().date()
    existing_checkins = Post.objects.filter(
        user=user,
        post_type='checkin',
        created_at__date=today
    )
    if existing_checkins.exists():
        print(f"🧹 Clearing {existing_checkins.count()} existing check-ins for clean test")
        existing_checkins.delete()

    # Get initial state
    strict_task.refresh_from_db()
    user.refresh_from_db()
    initial_code = strict_task.strict_code
    initial_coins = user.coins
    print(f"🔐 Initial code: {initial_code}")
    print(f"💰 Initial coins: {initial_coins}")

    # Test 1: First check-in should trigger update
    print(f"\n🎯 Test 1: First check-in (should trigger update)")

    # Create first post but don't call the method yet
    first_post = Post(
        user=user,
        content="First check-in post",
        post_type='checkin'
    )
    # Don't save yet - simulate the flow where the method is called during creation

    view = PostListCreateView()

    # Temporarily save the post to simulate the actual creation flow
    first_post.save()

    # Now call the method as it would be called during creation
    view._process_daily_checkin_reward(first_post)

    # Check results
    strict_task.refresh_from_db()
    user.refresh_from_db()
    code_after_first = strict_task.strict_code
    coins_after_first = user.coins

    print(f"🔐 Code after first: {initial_code} → {code_after_first}")
    print(f"💰 Coins after first: {initial_coins} → {coins_after_first}")

    first_updated = initial_code != code_after_first
    first_coins_added = coins_after_first > initial_coins
    print(f"✅ First check-in updated code: {first_updated}")
    print(f"✅ First check-in added coins: {first_coins_added}")

    # Test 2: Second check-in should NOT trigger update
    print(f"\n🎯 Test 2: Second check-in (should NOT trigger update)")

    # Create second post
    second_post = Post(
        user=user,
        content="Second check-in post",
        post_type='checkin'
    )
    second_post.save()

    # Call the method
    view._process_daily_checkin_reward(second_post)

    # Check results
    strict_task.refresh_from_db()
    user.refresh_from_db()
    code_after_second = strict_task.strict_code
    coins_after_second = user.coins

    print(f"🔐 Code after second: {code_after_first} → {code_after_second}")
    print(f"💰 Coins after second: {coins_after_first} → {coins_after_second}")

    second_updated = code_after_first != code_after_second
    second_coins_added = coins_after_second > coins_after_first
    print(f"❌ Second check-in updated code: {second_updated} (should be False)")
    print(f"❌ Second check-in added coins: {second_coins_added} (should be False)")

    # Summary
    print(f"\n📊 Test Summary:")
    if first_updated and first_coins_added and not second_updated and not second_coins_added:
        print(f"✅ ALL TESTS PASSED!")
    else:
        print(f"❌ SOME TESTS FAILED!")
        print(f"  - First check-in should update: {first_updated} ✅" if first_updated else f"  - First check-in should update: {first_updated} ❌")
        print(f"  - First check-in should add coins: {first_coins_added} ✅" if first_coins_added else f"  - First check-in should add coins: {first_coins_added} ❌")
        print(f"  - Second check-in should NOT update: {not second_updated} ✅" if not second_updated else f"  - Second check-in should NOT update: {not second_updated} ❌")
        print(f"  - Second check-in should NOT add coins: {not second_coins_added} ✅" if not second_coins_added else f"  - Second check-in should NOT add coins: {not second_coins_added} ❌")

    # Cleanup
    print(f"\n🧹 Cleaning up test posts...")
    first_post.delete()
    second_post.delete()

if __name__ == '__main__':
    test_realistic_checkin_flow()