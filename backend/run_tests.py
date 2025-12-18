#!/usr/bin/env python3
"""
Lockup Backend Test Runner

This script provides a unified interface to run all tests and diagnostic tools
in the Lockup backend application.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --api              # Run only API tests
    python run_tests.py --tasks            # Run only task tests
    python run_tests.py --frontend         # Run only frontend tests
    python run_tests.py --telegram         # Run only Telegram tests
    python run_tests.py --debug            # Run debug tools
    python run_tests.py --integration      # Run integration tests
    python run_tests.py --list             # List all available tests
    python run_tests.py --verbose          # Verbose output

Author: Claude Code
Created: 2024-12-19
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

# Setup Django before imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"❌ Failed to setup Django: {e}")
    sys.exit(1)


class TestRunner:
    """Unified test runner for Lockup backend"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.tests_dir = Path(__file__).parent / 'tests'
        self.test_categories = {
            'api': 'API endpoint tests',
            'tasks': 'Task functionality and Celery tests',
            'frontend': 'Frontend integration tests',
            'telegram': 'Telegram bot tests',
            'debug': 'Debug and diagnostic tools',
            'utils': 'Utility and maintenance scripts',
            'integration': 'Integration and verification tests'
        }

    def log(self, message: str, level: str = "INFO") -> None:
        """Log messages with optional verbosity control"""
        if level == "ERROR" or self.verbose or level == "RESULT":
            print(message)

    def print_header(self, title: str) -> None:
        """Print a formatted header"""
        print("=" * 60)
        print(f"{title:^60}")
        print("=" * 60)

    def discover_tests(self, category: Optional[str] = None) -> Dict[str, List[Path]]:
        """Discover test files in the specified category or all categories"""
        discovered = {}

        if category:
            categories = [category] if category in self.test_categories else []
        else:
            categories = list(self.test_categories.keys())

        for cat in categories:
            cat_dir = self.tests_dir / cat
            if cat_dir.exists():
                test_files = list(cat_dir.glob('*.py'))
                # Exclude __init__.py files
                test_files = [f for f in test_files if f.name != '__init__.py']
                if test_files:
                    discovered[cat] = test_files

        return discovered

    def list_tests(self) -> None:
        """List all available tests organized by category"""
        self.print_header("AVAILABLE TESTS")

        discovered = self.discover_tests()

        for category, description in self.test_categories.items():
            print(f"\n📁 {category.upper()}: {description}")

            if category in discovered:
                for test_file in discovered[category]:
                    print(f"  📄 {test_file.name}")
            else:
                print("  (No test files found)")

        print(f"\nTotal categories: {len(self.test_categories)}")
        total_files = sum(len(files) for files in discovered.values())
        print(f"Total test files: {total_files}")

    def run_python_file(self, file_path: Path) -> bool:
        """Run a Python test file and return success status"""
        self.log(f"Running {file_path.name}...")

        try:
            result = subprocess.run(
                [sys.executable, str(file_path)],
                cwd=self.tests_dir.parent,
                capture_output=not self.verbose,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode == 0:
                self.log(f"✅ {file_path.name} passed", "RESULT")
                return True
            else:
                self.log(f"❌ {file_path.name} failed (exit code: {result.returncode})", "ERROR")
                if not self.verbose and result.stderr:
                    self.log(f"Error output: {result.stderr}", "ERROR")
                return False

        except subprocess.TimeoutExpired:
            self.log(f"⏱️ {file_path.name} timed out", "ERROR")
            return False
        except Exception as e:
            self.log(f"💥 {file_path.name} crashed: {e}", "ERROR")
            return False

    def run_category_tests(self, category: str) -> Dict[str, bool]:
        """Run all tests in a specific category"""
        if category not in self.test_categories:
            self.log(f"❌ Unknown category: {category}", "ERROR")
            return {}

        self.print_header(f"RUNNING {category.upper()} TESTS")

        discovered = self.discover_tests(category)

        if category not in discovered:
            self.log(f"No test files found in {category} category")
            return {}

        results = {}
        for test_file in discovered[category]:
            results[test_file.name] = self.run_python_file(test_file)

        return results

    def run_all_tests(self) -> Dict[str, Dict[str, bool]]:
        """Run all tests in all categories"""
        self.print_header("RUNNING ALL TESTS")

        all_results = {}
        discovered = self.discover_tests()

        for category in self.test_categories.keys():
            if category in discovered:
                self.log(f"\n📁 Running {category} tests...")
                category_results = {}

                for test_file in discovered[category]:
                    category_results[test_file.name] = self.run_python_file(test_file)

                all_results[category] = category_results
            else:
                self.log(f"📁 Skipping {category} (no test files)")

        return all_results

    def print_summary(self, results: Dict) -> bool:
        """Print test results summary"""
        self.print_header("TEST SUMMARY")

        total_passed = 0
        total_failed = 0

        # Handle both single category and all categories results
        if isinstance(next(iter(results.values()), {}), bool):
            # Single category results
            for test_name, passed in results.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"{test_name}: {status}")
                if passed:
                    total_passed += 1
                else:
                    total_failed += 1
        else:
            # All categories results
            for category, category_results in results.items():
                print(f"\n📁 {category.upper()}:")
                for test_name, passed in category_results.items():
                    status = "✅ PASS" if passed else "❌ FAIL"
                    print(f"  {test_name}: {status}")
                    if passed:
                        total_passed += 1
                    else:
                        total_failed += 1

        total_tests = total_passed + total_failed
        print(f"\n📊 Results: {total_passed}/{total_tests} passed")

        if total_failed == 0:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️ {total_failed} tests failed")
            return False


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description='Lockup Backend Test Runner')

    # Test category options
    parser.add_argument('--api', action='store_true', help='Run API tests')
    parser.add_argument('--tasks', action='store_true', help='Run task tests')
    parser.add_argument('--frontend', action='store_true', help='Run frontend tests')
    parser.add_argument('--telegram', action='store_true', help='Run Telegram tests')
    parser.add_argument('--debug', action='store_true', help='Run debug tools')
    parser.add_argument('--utils', action='store_true', help='Run utility scripts')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')

    # Other options
    parser.add_argument('--list', action='store_true', help='List all available tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    runner = TestRunner(verbose=args.verbose)

    # Handle list option
    if args.list:
        runner.list_tests()
        return

    # Determine which tests to run
    categories_to_run = []
    if args.api:
        categories_to_run.append('api')
    if args.tasks:
        categories_to_run.append('tasks')
    if args.frontend:
        categories_to_run.append('frontend')
    if args.telegram:
        categories_to_run.append('telegram')
    if args.debug:
        categories_to_run.append('debug')
    if args.utils:
        categories_to_run.append('utils')
    if args.integration:
        categories_to_run.append('integration')

    # Run tests
    if categories_to_run:
        # Run specific categories
        all_results = {}
        for category in categories_to_run:
            results = runner.run_category_tests(category)
            if results:
                all_results[category] = results

        if all_results:
            success = runner.print_summary(all_results)
        else:
            print("No tests found in specified categories")
            success = False
    else:
        # Run all tests
        all_results = runner.run_all_tests()
        success = runner.print_summary(all_results)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()