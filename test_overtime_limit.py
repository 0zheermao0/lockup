#!/usr/bin/env python3
"""
测试带锁任务随机加时操作的时间限制
验证两小时内只能对同一个任务人操作一次的限制是否正确工作
"""

import requests
import json
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"

def register_and_login(username_suffix):
    """注册并登录测试用户"""
    test_user = {
        "username": f"test_overtime_{username_suffix}_{int(time.time() * 1000000)}",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "email": f"test_overtime_{username_suffix}_{int(time.time() * 1000000)}@example.com"
    }

    # 注册
    response = requests.post(f"{BASE_URL}/api/auth/register/", json=test_user)
    if response.status_code != 201:
        print(f"❌ 用户{username_suffix}注册失败: {response.status_code} - {response.text}")
        return None, None

    # 登录
    login_response = requests.post(f"{BASE_URL}/api/auth/login/", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })

    if login_response.status_code != 200:
        print(f"❌ 用户{username_suffix}登录失败: {login_response.status_code} - {login_response.text}")
        return None, None

    data = login_response.json()
    print(f"✅ 用户{username_suffix} ({test_user['username']}) 注册并登录成功")

    return data['token'], test_user['username']

def create_lock_task(token, difficulty='normal'):
    """创建带锁任务"""
    headers = {'Authorization': f'Token {token}'}
    task_data = {
        "title": f"测试加时限制任务_{difficulty}_{int(time.time())}",
        "description": f"测试{difficulty}难度的加时限制",
        "task_type": "lock",
        "difficulty": difficulty,
        "duration_type": "fixed",
        "duration_value": 60,  # 60分钟任务
        "unlock_type": "time"
    }

    response = requests.post(f"{BASE_URL}/api/tasks/", json=task_data, headers=headers)
    if response.status_code == 201:
        task = response.json()
        print(f"✅ 创建{difficulty}难度任务成功: {task['id']}")
        return task
    else:
        print(f"❌ 创建任务失败: {response.status_code} - {response.text}")
        return None

def add_overtime_to_task(token, task_id):
    """为任务添加随机加时"""
    headers = {'Authorization': f'Token {token}'}
    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/overtime/", headers=headers)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 加时成功: {data.get('message', '未知')}")
        return True
    else:
        error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {'error': response.text}
        print(f"❌ 加时失败: {error_data.get('error', '未知错误')}")
        return False

def test_overtime_time_limit():
    """测试加时操作的时间限制"""
    print("🧪 测试带锁任务随机加时操作的时间限制")
    print("="*60)
    print("测试规则：两小时内只能对同一个任务人操作一次")
    print()

    # 创建两个用户：任务发布者和加时操作者
    print("📝 步骤1：创建测试用户")
    publisher_token, publisher_username = register_and_login("publisher")
    overtime_user_token, overtime_user_username = register_and_login("overtime_user")

    if not publisher_token or not overtime_user_token:
        return False

    print()
    print("📝 步骤2：发布者创建带锁任务")
    task = create_lock_task(publisher_token, 'normal')
    if not task:
        return False

    task_id = task['id']
    print(f"   任务ID: {task_id}")

    print()
    print("📝 步骤3：第一次加时操作（应该成功）")
    first_overtime = add_overtime_to_task(overtime_user_token, task_id)

    if not first_overtime:
        print("❌ 第一次加时操作失败，测试无法继续")
        return False

    print()
    print("📝 步骤4：立即进行第二次加时操作（应该失败）")
    second_overtime = add_overtime_to_task(overtime_user_token, task_id)

    if second_overtime:
        print("❌ 第二次加时操作成功了，但应该失败（两小时内限制）")
        return False
    else:
        print("✅ 正确：第二次加时操作被正确阻止")

    print()
    print("📝 步骤5：创建第二个任务，测试对同一发布者的限制")
    task2 = create_lock_task(publisher_token, 'hard')
    if not task2:
        print("⚠️  无法创建第二个任务，跳过此测试")
    else:
        task2_id = task2['id']
        print(f"   第二个任务ID: {task2_id}")

        third_overtime = add_overtime_to_task(overtime_user_token, task2_id)
        if third_overtime:
            print("❌ 对同一发布者的第二个任务加时成功了，但应该失败（两小时内限制）")
            return False
        else:
            print("✅ 正确：对同一发布者的第二个任务加时也被正确阻止")

    print()
    print("🎉 所有测试通过！两小时内加时限制正确工作")
    print("💡 说明：")
    print("   - 用户在两小时内只能对同一个任务发布者的任务进行一次加时操作")
    print("   - 无论是同一个任务还是该发布者的其他任务，都受此限制")

    return True

if __name__ == "__main__":
    try:
        success = test_overtime_time_limit()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        exit(1)