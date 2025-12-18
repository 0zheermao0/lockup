#!/usr/bin/env python3

import requests
import json

# 模拟 Telegram webhook 请求测试多个命令
def test_telegram_commands():
    webhook_url = "http://localhost:8005/api/telegram/webhook/"

    # 测试命令列表
    commands_to_test = [
        "/start",
        "/help",
        "/bind",
        "/status",
        "/task",
        "/share_item"
    ]

    base_update = {
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
            "entities": [
                {
                    "offset": 0,
                    "length": 6,
                    "type": "bot_command"
                }
            ]
        }
    }

    print("Testing multiple Telegram commands...")

    for i, command in enumerate(commands_to_test):
        print(f"\n{'='*50}")
        print(f"Testing command: {command}")
        print(f"{'='*50}")

        # 创建测试数据
        test_update = base_update.copy()
        test_update["update_id"] = 123456789 + i
        test_update["message"] = base_update["message"].copy()
        test_update["message"]["message_id"] = i + 1
        test_update["message"]["text"] = command
        test_update["message"]["entities"][0]["length"] = len(command)

        print(f"Sending request for: {command}")

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
                print(f"✅ {command} command processed successfully!")
            else:
                print(f"❌ {command} command failed!")

        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for {command}: {e}")
        except Exception as e:
            print(f"❌ Unexpected error for {command}: {e}")

if __name__ == "__main__":
    test_telegram_commands()