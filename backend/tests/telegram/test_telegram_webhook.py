#!/usr/bin/env python3

import requests
import json

# 模拟 Telegram webhook 请求测试 bot 初始化
def test_telegram_webhook():
    webhook_url = "http://localhost:8005/api/telegram/webhook/"

    # 模拟一个简单的 /start 命令
    test_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": 1702500000,
            "text": "/start",
            "entities": [
                {
                    "offset": 0,
                    "length": 6,
                    "type": "bot_command"
                }
            ]
        }
    }

    print("Testing Telegram webhook...")
    print(f"Sending request to: {webhook_url}")
    print(f"Test data: {json.dumps(test_update, indent=2)}")

    try:
        response = requests.post(
            webhook_url,
            json=test_update,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")

        if response.status_code == 200:
            print("✅ Webhook request successful!")
        else:
            print("❌ Webhook request failed!")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_telegram_webhook()