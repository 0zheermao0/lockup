#!/usr/bin/env python3
"""
Test script to reproduce the game join error
"""

import requests
import json

# Test data
base_url = "http://127.0.0.1:8000"
game_id = "3e033cde-d511-41fa-9077-73535e95ef4c"  # The game ID from the error message

# Test payload
payload = {
    "action": {
        "choice": "rock"
    }
}

headers = {
    "Content-Type": "application/json",
    # You would need to add authentication headers here
    # "Authorization": "Bearer your_token_here"
}

try:
    # Make the join game request
    url = f"{base_url}/api/store/games/{game_id}/join/"
    print(f"Making request to: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(url, json=payload, headers=headers)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 500:
        print("Found 500 error - this might be our Notification bug!")

except Exception as e:
    print(f"Error making request: {e}")