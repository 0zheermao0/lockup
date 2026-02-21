#!/usr/bin/env python3
"""
Test script to verify login fix works correctly
"""

import requests
import json

def test_login_endpoint():
    """Test the login endpoint to see what's happening"""

    print("🧪 Testing Login Endpoint Fix...")

    # Test with invalid credentials first (should return 400 with JSON)
    try:
        response = requests.post(
            'http://localhost:8000/api/auth/login/',
            headers={'Content-Type': 'application/json'},
            json={'username': 'invalid', 'password': 'invalid'},
            timeout=10
        )

        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'Not set')}")
        print(f"Response Text: {response.text}")

        # Try to parse as JSON
        try:
            json_data = response.json()
            print(f"✅ JSON parsing successful: {json_data}")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"Raw response: {repr(response.text)}")
            return False

    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_frontend_integration():
    """Test if frontend can access the login endpoint"""

    print("\n🔍 Testing Frontend Integration...")

    try:
        # Test CORS and basic connectivity
        response = requests.options(
            'http://localhost:8000/api/auth/login/',
            headers={
                'Origin': 'http://localhost:5174',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            },
            timeout=10
        )

        print(f"OPTIONS Status: {response.status_code}")
        print(f"CORS Headers: {dict(response.headers)}")

        return response.status_code == 200

    except requests.RequestException as e:
        print(f"❌ OPTIONS request failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Login Fix...")

    login_ok = test_login_endpoint()
    cors_ok = test_frontend_integration()

    print(f"\n🏁 Test Results:")
    print(f"Login endpoint: {'✅' if login_ok else '❌'}")
    print(f"CORS/Frontend: {'✅' if cors_ok else '❌'}")

    if login_ok and cors_ok:
        print("\n✅ Login endpoint is working correctly!")
        print("The issue might be in the frontend API interceptor logic.")
        print("Please check the browser console for more details.")
    else:
        print("\n❌ There are issues with the login endpoint.")