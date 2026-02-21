#!/usr/bin/env python3
"""
Test script to verify frontend login works with the fixed API interceptor
"""

import requests
import json
from datetime import datetime

def test_frontend_login():
    """Test frontend login with the test user"""

    print("🧪 Testing Frontend Login Fix")
    print("=" * 50)

    # Test credentials from create_test_user.py
    test_credentials = {
        "username": "testuser",
        "password": "testpass123"
    }

    print(f"Testing login with user: {test_credentials['username']}")

    try:
        # Simulate frontend login request
        response = requests.post(
            'http://localhost:8000/api/auth/login/',
            headers={
                'Content-Type': 'application/json',
                'Origin': 'http://localhost:5176',  # Updated port
            },
            json=test_credentials,
            timeout=10
        )

        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'Not set')}")

        if response.status_code == 200:
            try:
                data = response.json()
                print("✅ Login successful!")
                print(f"✅ JSON parsing successful")
                print(f"User ID: {data.get('user', {}).get('id', 'Not found')}")
                print(f"Token: {data.get('token', 'Not found')[:20]}...")

                # Check if active_lock_task is present
                user_data = data.get('user', {})
                if 'active_lock_task' in user_data:
                    active_task = user_data['active_lock_task']
                    if active_task:
                        print(f"✅ User has active lock task: {active_task.get('title', 'Unknown')}")
                    else:
                        print("✅ User has no active lock task (null)")
                else:
                    print("⚠️  No active_lock_task field in response")

                return True

            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"Raw response: {response.text}")
                return False
        else:
            print(f"❌ Login failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_profile_endpoint():
    """Test that profile endpoints work correctly"""

    print("\n🔍 Testing Profile Endpoint")
    print("-" * 30)

    # First login to get token
    login_response = requests.post(
        'http://localhost:8000/api/auth/login/',
        headers={'Content-Type': 'application/json'},
        json={"username": "testuser", "password": "testpass123"},
        timeout=10
    )

    if login_response.status_code != 200:
        print("❌ Failed to login for profile test")
        return False

    token = login_response.json().get('token')
    if not token:
        print("❌ No token received from login")
        return False

    # Test current user profile endpoint
    try:
        response = requests.get(
            'http://localhost:8000/api/auth/profile/',
            headers={
                'Authorization': f'Token {token}',
                'Content-Type': 'application/json'
            },
            timeout=10
        )

        print(f"Profile endpoint status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Profile endpoint working")
            print(f"User ID: {data.get('id', 'Not found')}")
            return True
        else:
            print(f"❌ Profile endpoint failed: {response.text}")
            return False

    except requests.RequestException as e:
        print(f"❌ Profile endpoint request failed: {e}")
        return False

if __name__ == "__main__":
    print(f"🚀 Starting frontend login test at {datetime.now()}")
    print(f"Frontend URL: http://localhost:5176")
    print(f"Backend URL: http://localhost:8000")
    print()

    login_ok = test_frontend_login()
    profile_ok = test_profile_endpoint()

    print("\n" + "🏁 Test Summary:")
    print(f"Login test: {'✅ PASSED' if login_ok else '❌ FAILED'}")
    print(f"Profile test: {'✅ PASSED' if profile_ok else '❌ FAILED'}")

    if login_ok and profile_ok:
        print("\n🎉 All tests passed!")
        print("✅ The login fix is working correctly")
        print("✅ API interceptor should now handle login responses properly")
        print("\n📝 You can now test in the browser:")
        print("1. Go to http://localhost:5176")
        print("2. Login with username: testuser, password: testpass123")
        print("3. Verify that login works without JSON parsing errors")
        print("4. Test viewing other user profiles and returning to home page")
        print("5. Verify that lock status remains correct throughout navigation")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")