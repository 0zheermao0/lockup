# Lockup Backend Test Suite

This directory contains the organized test suite for the Lockup backend application.

## Directory Structure

```
tests/
├── __init__.py                 # Test package initialization
├── README.md                   # This file
├── api/                        # API endpoint tests
│   ├── __init__.py
│   ├── test_api.py             # Basic API testing
│   ├── test_api_call.py        # API call functionality
│   ├── test_take_api.py        # Task taking API
│   └── test_api_submission_files.py  # File submission API
├── tasks/                      # Task functionality tests
│   ├── __init__.py
│   ├── test_celery_tasks.py    # Celery task testing (comprehensive)
│   ├── create_test_task.py     # Task creation utilities
│   ├── create_test_submission.py  # Submission creation utilities
│   ├── test_task_end_logic.py  # Task completion logic
│   ├── test_action_fix.py      # Task action fixes
│   ├── test_multi_person_task_fix.py  # Multi-person task fixes
│   ├── test_multi_task_actions.py     # Multiple task actions
│   ├── test_my_taken_filter.py        # Task filtering logic
│   └── test_specific_task.py          # Specific task testing
├── frontend/                   # Frontend integration tests
│   ├── __init__.py
│   ├── test_frontend_data.py   # Frontend data integration
│   ├── test_card_display.py    # Card display functionality
│   ├── test_display_comparison.py     # Display comparison tests
│   ├── test_file_upload_fix.py        # File upload fixes
│   └── test_submission_files_permission.py  # File permission tests
├── telegram/                   # Telegram bot tests
│   ├── __init__.py
│   ├── test_telegram_binding.py       # Telegram account binding
│   ├── test_telegram_commands.py      # Bot commands
│   └── test_telegram_webhook.py       # Webhook functionality
├── debug/                      # Debug and diagnostic tools
│   ├── __init__.py
│   ├── debug_api_response.py   # API response debugging
│   ├── debug_can_take.py       # Task taking debug
│   ├── comprehensive_diagnosis.py     # System diagnosis
│   ├── check_current_tasks.py         # Current task status
│   ├── check_file_participant_relation.py  # File-participant checks
│   ├── check_specific_task_files.py        # Task file checks
│   └── check_submission_files.py           # Submission file checks
├── utils/                      # Test utilities and maintenance
│   ├── __init__.py
│   ├── fix_comment_hierarchy.py       # Comment hierarchy fixes
│   ├── fix_comment_hierarchy_v2.py    # Updated hierarchy fixes
│   └── fix_file_participant_relation.py   # Participant relation fixes
└── integration/                # Integration and verification tests
    ├── __init__.py
    ├── verify_fix.py           # Fix verification
    ├── verify_metadata_removal.py     # Metadata cleanup verification
    ├── verify_timeline_display.py     # Timeline display verification
    ├── test_final_verification.py     # Final verification tests
    ├── final_test_submission_display.py   # Submission display tests
    └── final_verification.py          # End-to-end verification
```

## Running Tests

### Using the Test Runner (Recommended)

The project includes a unified test runner (`run_tests.py` in the backend root) that provides easy access to all tests:

```bash
# Run all tests
python run_tests.py

# Run specific categories
python run_tests.py --api           # API tests only
python run_tests.py --tasks         # Task tests only
python run_tests.py --frontend      # Frontend tests only
python run_tests.py --telegram      # Telegram tests only
python run_tests.py --debug         # Debug tools only
python run_tests.py --utils         # Utility scripts only
python run_tests.py --integration   # Integration tests only

# Other options
python run_tests.py --list          # List all available tests
python run_tests.py --verbose       # Verbose output
python run_tests.py --help          # Show help
```

### Running Individual Tests

You can also run individual test files directly:

```bash
# Run a specific test file
python tests/tasks/test_celery_tasks.py

# Run with verbose output
python tests/tasks/test_celery_tasks.py --verbose

# Run debug tools
python tests/debug/comprehensive_diagnosis.py
```

## Test Categories

### 🌐 API Tests (`tests/api/`)
Tests for REST API endpoints, authentication, and API functionality.

### 📋 Task Tests (`tests/tasks/`)
Tests for task creation, management, Celery background tasks, and task lifecycle.

### 🎨 Frontend Tests (`tests/frontend/`)
Tests for frontend integration, UI components, and user interface functionality.

### 📱 Telegram Tests (`tests/telegram/`)
Tests for Telegram bot integration, commands, and webhook functionality.

### 🔍 Debug Tools (`tests/debug/`)
Diagnostic and debugging scripts for troubleshooting issues.

### 🛠️ Utilities (`tests/utils/`)
Maintenance scripts and utilities for fixing data and system states.

### 🔄 Integration Tests (`tests/integration/`)
End-to-end tests and verification scripts for complete workflows.

## Key Test Files

### `tests/tasks/test_celery_tasks.py`
Comprehensive test suite for Celery functionality including:
- Import verification
- Hourly rewards logic testing
- Database integration testing
- Task processing validation

This is the main test for the Celery + Celery Beat system.

### Debug Tools
The debug directory contains powerful diagnostic tools:
- `comprehensive_diagnosis.py`: Complete system health check
- `debug_api_response.py`: API response analysis
- `check_*` files: Various system state checks

## Adding New Tests

When adding new tests:

1. **Choose the right category** based on functionality
2. **Follow naming conventions**: `test_*.py` for test files
3. **Add proper documentation** in docstrings
4. **Include error handling** and cleanup
5. **Update this README** if adding new categories

## Django Test Integration

The organized tests work alongside Django's built-in test framework. Each app also has its own `tests.py` file for unit tests:

- `tasks/tests.py`
- `users/tests.py`
- `posts/tests.py`
- `store/tests.py`
- `telegram_bot/tests.py`

## Dependencies

Tests require the same dependencies as the main application. Make sure your virtual environment is activated:

```bash
source venv/bin/activate  # or equivalent for your system
```

## Notes

- All test files are designed to work without requiring Redis/Celery to be running
- Tests use Django's test database isolation
- Debug tools may modify real data - use with caution in production
- Integration tests verify end-to-end functionality

For more information about specific tests, check the docstrings in individual test files.