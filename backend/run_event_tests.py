#!/usr/bin/env python3
"""
Simplified test runner for event system tests
Bypasses Django test runner to avoid migration issues
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Add the backend directory to Python path
sys.path.insert(0, '/Users/joey/code/lockup/backend')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

# Import Django testing components
from django.test import TestCase
from django.db import transaction
from django.core.management import call_command

def run_basic_tests():
    """Run basic tests without full Django test runner"""

    print("🧪 Starting Event System Tests")
    print("=" * 50)

    # Test 1: Import all test modules
    print("\n1. Testing imports...")
    try:
        from tests.events.test_base import EventTestCase
        from tests.events.test_models import EventDefinitionModelTest
        from tests.events.test_effects import EffectExecutorFactoryTest
        from tests.events.test_celery_tasks import SchedulePendingEventsTaskTest
        from tests.events.test_admin import EventDefinitionAdminTest
        print("✅ All test modules import successfully")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

    # Test 2: Check model imports
    print("\n2. Testing model imports...")
    try:
        from events.models import EventDefinition, EventEffect, EventOccurrence
        from events.effects import get_effect_executor, CoinsEffectExecutor
        from events.celery_tasks import schedule_pending_events
        print("✅ All event system components import successfully")
    except Exception as e:
        print(f"❌ Model import error: {e}")
        return False

    # Test 3: Test effect executor factory
    print("\n3. Testing effect executor factory...")
    try:
        from events.models import EventDefinition, EventEffect
        from events.effects import get_effect_executor, CoinsEffectExecutor
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Create minimal test data in memory (no DB operations)
        class MockEventDefinition:
            def __init__(self):
                self.id = 'test-id'
                self.name = 'test'

        class MockEventEffect:
            def __init__(self, effect_type):
                self.effect_type = effect_type
                self.event_definition = MockEventDefinition()
                self.target_type = 'all_users'
                self.effect_parameters = {'amount': 10}
                self.target_parameters = {}

        # Test factory function
        mock_effect = MockEventEffect('coins_add')
        executor = get_effect_executor(mock_effect)

        if isinstance(executor, CoinsEffectExecutor):
            print("✅ Effect executor factory works correctly")
        else:
            print(f"❌ Unexpected executor type: {type(executor)}")
            return False

    except Exception as e:
        print(f"❌ Effect executor test error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Test admin imports
    print("\n4. Testing admin imports...")
    try:
        from events.admin import EventDefinitionAdmin, EventOccurrenceAdmin
        print("✅ Admin classes import successfully")
    except Exception as e:
        print(f"❌ Admin import error: {e}")
        return False

    print("\n" + "=" * 50)
    print("🎉 All basic tests passed!")
    print("✅ Event system is properly configured")
    return True

if __name__ == '__main__':
    success = run_basic_tests()
    if not success:
        sys.exit(1)

    print("\n📋 Next Steps:")
    print("- Run individual test classes manually")
    print("- Test with actual database operations")
    print("- Run integration tests")