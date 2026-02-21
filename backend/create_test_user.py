#!/usr/bin/env python3
"""
Create a test user for testing the login fix
"""

import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append('/Users/joey/code/lockup/backend')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import User

def create_test_user():
    """Create a test user for login testing"""

    try:
        # Check if test user already exists
        test_user = User.objects.filter(username='testuser').first()

        if test_user:
            print(f"✅ Test user 'testuser' already exists (ID: {test_user.id})")
            return test_user

        # Create new test user
        test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        print(f"✅ Created test user 'testuser' (ID: {test_user.id})")
        return test_user

    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        return None

def test_user_login():
    """Test user login with requests"""
    import requests

    try:
        response = requests.post(
            'http://localhost:8000/api/auth/login/',
            headers={'Content-Type': 'application/json'},
            json={'username': 'testuser', 'password': 'testpass123'},
            timeout=10
        )

        print(f"\n🔍 Login Test Results:")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful!")
            print(f"Token: {data.get('token', 'Not found')[:20]}...")
            print(f"User ID: {data.get('user', {}).get('id', 'Not found')}")
            return True
        else:
            print(f"❌ Login failed")
            return False

    except Exception as e:
        print(f"❌ Login test error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Creating test user for login testing...")

    user = create_test_user()
    if user:
        print(f"\n📝 Test credentials:")
        print(f"Username: testuser")
        print(f"Password: testpass123")

        # Test login
        login_success = test_user_login()

        if login_success:
            print(f"\n✅ Test user setup complete! You can now test login in the frontend.")
        else:
            print(f"\n❌ Login test failed. Please check the backend logs.")
    else:
        print(f"\n❌ Failed to create test user.")