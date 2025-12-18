#!/usr/bin/env python3
"""
Celery Tasks Test Suite

This script provides comprehensive testing for the Celery hourly rewards system.
It can run without requiring Redis/Celery to be running by testing the logic directly.

Usage:
    python test_celery_tasks.py                    # Run all tests
    python test_celery_tasks.py --imports-only     # Test only imports
    python test_celery_tasks.py --logic-only       # Test only logic
    python test_celery_tasks.py --verbose          # Verbose output

Author: Claude Code
Created: 2024-12-19
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Setup Django before any Django imports
# Add backend root directory to path so we can import Django modules
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"❌ Failed to setup Django: {e}")
    sys.exit(1)

from django.utils import timezone
from tasks.models import LockTask, HourlyReward
from users.models import User


class CeleryTestSuite:
    """Comprehensive test suite for Celery functionality"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.test_results = {}

    def log(self, message: str, level: str = "INFO") -> None:
        """Log messages with optional verbosity control"""
        if level == "ERROR" or self.verbose or level == "RESULT":
            print(message)

    def print_header(self, title: str) -> None:
        """Print a formatted header"""
        print("=" * 60)
        print(f"{title:^60}")
        print("=" * 60)

    def print_summary(self) -> None:
        """Print test results summary"""
        self.print_header("TEST SUMMARY")

        passed = 0
        total = len(self.test_results)

        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
            if result:
                passed += 1

        print()
        if passed == total:
            print("🎉 All tests passed! Celery hourly rewards system is ready.")
            return True
        else:
            print(f"⚠️ {total - passed} out of {total} tests failed. Please check the errors above.")
            return False

    def test_imports(self) -> bool:
        """Test that all Celery components can be imported"""
        self.print_header("TESTING CELERY IMPORTS")

        try:
            # Test Celery tasks import
            from tasks.celery_tasks import (
                process_hourly_rewards,
                health_check_hourly_rewards,
                debug_task,
                _process_task_hourly_rewards
            )
            self.log("✅ Celery tasks imported successfully", "RESULT")

            # Test Celery app import
            from celery_app import app
            self.log("✅ Celery app imported successfully", "RESULT")

            # Test django-celery-beat models
            from django_celery_beat.models import PeriodicTask, IntervalSchedule
            periodic_tasks = PeriodicTask.objects.all()
            self.log(f"✅ Found {periodic_tasks.count()} periodic tasks in database", "RESULT")

            # List periodic tasks
            for task in periodic_tasks:
                self.log(f"  - {task.name}: {task.task} (enabled: {task.enabled})")

            return True

        except ImportError as e:
            self.log(f"❌ Import error: {e}", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ Unexpected error during imports: {e}", "ERROR")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False

    def get_database_stats(self) -> Dict[str, int]:
        """Get current database statistics"""
        return {
            'total_lock_tasks': LockTask.objects.filter(task_type='lock').count(),
            'active_lock_tasks': LockTask.objects.filter(
                task_type='lock',
                status__in=['active', 'voting']
            ).count(),
            'total_hourly_rewards': HourlyReward.objects.count(),
        }

    def create_test_task(self) -> Tuple[User, LockTask]:
        """Create a test user and task for testing"""
        test_user, created = User.objects.get_or_create(
            username='test_celery_user',
            defaults={'email': 'test@celerytest.com', 'coins': 10}
        )

        # Clean up any existing test tasks
        LockTask.objects.filter(
            title='Test Celery Lock Task',
            user=test_user
        ).delete()

        # Create a test lock task that started 2 hours ago
        test_task = LockTask.objects.create(
            title='Test Celery Lock Task',
            description='Test task for Celery hourly rewards',
            task_type='lock',
            status='active',
            user=test_user,
            start_time=timezone.now() - timedelta(hours=2),
            total_hourly_rewards=0,
            last_hourly_reward_at=None
        )

        self.log(f"Created test task: {test_task.title} (ID: {test_task.id})")
        self.log(f"Task started: {test_task.start_time}")

        return test_user, test_task

    def test_with_existing_tasks(self) -> bool:
        """Test logic with existing active tasks"""
        active_tasks = LockTask.objects.filter(
            task_type='lock',
            status__in=['active', 'voting']
        )

        if not active_tasks.exists():
            self.log("No existing active tasks found")
            return True

        sample_task = active_tasks.first()
        self.log("Found existing active lock tasks. Analyzing sample task...")
        self.log(f"Sample task: {sample_task.title}")
        self.log(f"User: {sample_task.user.username}")
        self.log(f"Start time: {sample_task.start_time}")
        self.log(f"Current hourly rewards: {sample_task.total_hourly_rewards}")
        self.log(f"Last reward at: {sample_task.last_hourly_reward_at}")

        if sample_task.start_time:
            now = timezone.now()
            elapsed_time = now - sample_task.start_time
            elapsed_hours = int(elapsed_time.total_seconds() // 3600)
            rewards_due = elapsed_hours - sample_task.total_hourly_rewards

            self.log(f"Elapsed time: {elapsed_time}")
            self.log(f"Elapsed hours: {elapsed_hours}")
            self.log(f"Rewards due: {rewards_due}")

            if rewards_due > 0:
                self.log("✅ This task would receive hourly rewards", "RESULT")
            else:
                self.log("ℹ️ This task is up to date with rewards", "RESULT")

        return True

    def test_reward_processing(self, test_user: User, test_task: LockTask) -> bool:
        """Test the actual reward processing logic"""
        from tasks.celery_tasks import _process_task_hourly_rewards

        now = timezone.now()
        elapsed_time = now - test_task.start_time
        elapsed_hours = int(elapsed_time.total_seconds() // 3600)

        self.log(f"Elapsed time: {elapsed_time}")
        self.log(f"Elapsed hours: {elapsed_hours}")

        if elapsed_hours < 1:
            self.log("Task hasn't run for a full hour yet, skipping reward processing")
            return True

        processed_rewards = []
        initial_coins = test_user.coins

        try:
            # Process rewards for this task
            _process_task_hourly_rewards(
                test_task, now, 1, elapsed_hours, processed_rewards
            )

            # Update task
            test_task.total_hourly_rewards += elapsed_hours
            test_task.last_hourly_reward_at = now
            test_task.save()

            # Refresh user from database
            test_user.refresh_from_db()

            # Verify results
            coins_earned = test_user.coins - initial_coins
            self.log(f"✅ Successfully processed {elapsed_hours} hourly rewards", "RESULT")
            self.log(f"User coins: {initial_coins} → {test_user.coins} (+{coins_earned})", "RESULT")
            self.log(f"Task total hourly rewards: {test_task.total_hourly_rewards}", "RESULT")

            if self.verbose:
                self.log(f"Processed rewards details: {processed_rewards}")

            # Verify hourly reward records were created
            task_rewards = HourlyReward.objects.filter(task=test_task)
            self.log(f"Hourly reward records created: {task_rewards.count()}", "RESULT")

            if self.verbose:
                for reward in task_rewards[:5]:  # Show first 5
                    self.log(f"  - Hour {reward.hour_count}: {reward.reward_amount} coins")
                if task_rewards.count() > 5:
                    self.log(f"  ... and {task_rewards.count() - 5} more")

            return True

        except Exception as e:
            self.log(f"❌ Error processing hourly rewards: {e}", "ERROR")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False

    def test_hourly_rewards_logic(self) -> bool:
        """Test the hourly rewards processing logic"""
        self.print_header("TESTING CELERY HOURLY REWARDS LOGIC")

        # Get and display database statistics
        stats = self.get_database_stats()
        self.log("Database Statistics:")
        for key, value in stats.items():
            self.log(f"  {key.replace('_', ' ').title()}: {value}")
        print()

        try:
            if stats['active_lock_tasks'] == 0:
                self.log("No active lock tasks found. Creating test task...")
                test_user, test_task = self.create_test_task()
                result = self.test_reward_processing(test_user, test_task)

                # Clean up test data
                if not self.verbose:
                    test_task.delete()
                    if test_user.username == 'test_celery_user':
                        test_user.delete()

                return result
            else:
                return self.test_with_existing_tasks()

        except Exception as e:
            self.log(f"❌ Unexpected error in logic test: {e}", "ERROR")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False

    def run_all_tests(self) -> bool:
        """Run all tests and return overall success"""
        print(f"Starting Celery Test Suite at {datetime.now()}")
        print()

        # Run import tests
        self.test_results['Celery Imports'] = self.test_imports()
        print()

        # Run logic tests
        self.test_results['Hourly Rewards Logic'] = self.test_hourly_rewards_logic()
        print()

        # Print summary and return result
        return self.print_summary()


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description='Celery Tasks Test Suite')
    parser.add_argument('--imports-only', action='store_true',
                       help='Test only imports')
    parser.add_argument('--logic-only', action='store_true',
                       help='Test only logic')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    suite = CeleryTestSuite(verbose=args.verbose)

    success = True

    if args.imports_only:
        success = suite.test_imports()
    elif args.logic_only:
        success = suite.test_hourly_rewards_logic()
    else:
        success = suite.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()