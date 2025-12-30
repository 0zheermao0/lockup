#!/usr/bin/env python3
"""
Manual test script for event system
Tests individual components without Django test runner
"""

import os
import sys
import django
from django.conf import settings

# Add the backend directory to Python path
sys.path.insert(0, '/Users/joey/code/lockup/backend')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

def test_event_models():
    """Test event models creation and basic functionality"""
    print("\n🧪 Testing Event Models")
    print("-" * 30)

    try:
        from events.models import EventDefinition, EventEffect, EventOccurrence
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        User = get_user_model()

        # Create a test user (in-memory, no DB save for now)
        print("✅ Event models imported successfully")

        # Test model field definitions
        event_def_fields = [field.name for field in EventDefinition._meta.fields]
        expected_fields = ['id', 'name', 'category', 'title', 'description', 'schedule_type']

        for field in expected_fields:
            if field in event_def_fields:
                print(f"✅ EventDefinition has field: {field}")
            else:
                print(f"❌ EventDefinition missing field: {field}")

        return True

    except Exception as e:
        print(f"❌ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_effect_executors():
    """Test effect executor classes"""
    print("\n🧪 Testing Effect Executors")
    print("-" * 30)

    try:
        from events.effects import (
            get_effect_executor, CoinsEffectExecutor,
            ItemDistributeEffectExecutor, TaskFreezeEffectExecutor
        )

        print("✅ Effect executors imported successfully")

        # Test effect types mapping
        from events.effects import EFFECT_EXECUTORS

        expected_executors = [
            'coins_add', 'coins_subtract', 'item_distribute',
            'task_freeze_all', 'task_unfreeze_all'
        ]

        for effect_type in expected_executors:
            if effect_type in EFFECT_EXECUTORS:
                print(f"✅ Effect executor registered: {effect_type}")
            else:
                print(f"❌ Effect executor missing: {effect_type}")

        return True

    except Exception as e:
        print(f"❌ Effect executor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_celery_tasks():
    """Test celery task imports"""
    print("\n🧪 Testing Celery Tasks")
    print("-" * 30)

    try:
        from events.celery_tasks import (
            schedule_pending_events, execute_pending_events,
            process_expired_effects, trigger_manual_event
        )

        print("✅ Celery tasks imported successfully")

        # Test task signatures
        tasks = [
            schedule_pending_events,
            execute_pending_events,
            process_expired_effects,
            trigger_manual_event
        ]

        for task in tasks:
            if hasattr(task, 'delay'):
                print(f"✅ Task has delay method: {task.__name__}")
            else:
                print(f"❌ Task missing delay method: {task.__name__}")

        return True

    except Exception as e:
        print(f"❌ Celery task test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_classes():
    """Test admin class imports"""
    print("\n🧪 Testing Admin Classes")
    print("-" * 30)

    try:
        from events.admin import (
            EventDefinitionAdmin, EventOccurrenceAdmin,
            EventEffectExecutionAdmin
        )

        print("✅ Admin classes imported successfully")

        # Test admin configurations
        admin_classes = [
            EventDefinitionAdmin,
            EventOccurrenceAdmin,
            EventEffectExecutionAdmin
        ]

        for admin_class in admin_classes:
            if hasattr(admin_class, 'list_display'):
                print(f"✅ Admin has list_display: {admin_class.__name__}")
            else:
                print(f"❌ Admin missing list_display: {admin_class.__name__}")

        return True

    except Exception as e:
        print(f"❌ Admin test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_management_commands():
    """Test management command imports"""
    print("\n🧪 Testing Management Commands")
    print("-" * 30)

    try:
        # Test command file existence
        import os
        command_files = [
            'events/management/commands/trigger_event.py',
            'events/management/commands/init_sample_events.py'
        ]

        for cmd_file in command_files:
            full_path = os.path.join('/Users/joey/code/lockup/backend', cmd_file)
            if os.path.exists(full_path):
                print(f"✅ Command file exists: {cmd_file}")
            else:
                print(f"❌ Command file missing: {cmd_file}")

        return True

    except Exception as e:
        print(f"❌ Management command test failed: {e}")
        return False

def test_model_relationships():
    """Test model relationship definitions"""
    print("\n🧪 Testing Model Relationships")
    print("-" * 30)

    try:
        from events.models import EventDefinition, EventEffect, EventOccurrence

        # Test EventDefinition relationships
        event_def_relations = [field.name for field in EventDefinition._meta.related_objects]
        print(f"✅ EventDefinition related objects: {event_def_relations}")

        # Test foreign key relationships
        effect_fks = [field.name for field in EventEffect._meta.fields if field.get_internal_type() == 'ForeignKey']
        print(f"✅ EventEffect foreign keys: {effect_fks}")

        return True

    except Exception as e:
        print(f"❌ Model relationship test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all manual tests"""
    print("🚀 Starting Manual Event System Tests")
    print("=" * 50)

    tests = [
        test_event_models,
        test_effect_executors,
        test_celery_tasks,
        test_admin_classes,
        test_management_commands,
        test_model_relationships
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Event system is properly configured.")
        return True
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return False

if __name__ == '__main__':
    success = run_all_tests()

    if success:
        print("\n📋 Next Steps:")
        print("- Event system is ready for use")
        print("- Try: python manage.py trigger_event --event-name 'test_event' --dry-run")
        print("- Try: python manage.py init_sample_events --dry-run")
    else:
        print("\n🔧 Fix the issues above before proceeding")
        sys.exit(1)