#!/usr/bin/env python3
"""
快速测试改进后的投票状态逻辑
主要验证API端点是否接受投票状态的任务进行加时操作
"""

import requests
import json
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"

def register_and_login():
    """注册并登录测试用户"""
    test_user = {
        "username": f"test_voting_quick_{int(time.time() * 1000000)}",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "email": f"test_voting_quick_{int(time.time() * 1000000)}@example.com"
    }

    # 注册
    response = requests.post(f"{BASE_URL}/api/auth/register/", json=test_user)
    if response.status_code != 201:
        print(f"❌ 注册失败: {response.status_code} - {response.text}")
        return None

    # 登录
    login_response = requests.post(f"{BASE_URL}/api/auth/login/", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })

    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.status_code} - {login_response.text}")
        return None

    data = login_response.json()
    print(f"✅ 用户 {test_user['username']} 注册并登录成功")

    return data['token']

def test_voting_overtime_api():
    """测试投票期任务加时API"""
    print("🧪 快速测试改进后的投票状态逻辑")
    print("="*50)

    # 创建两个用户
    print("📝 步骤1：创建用户")
    publisher_token = register_and_login()
    overtime_user_token = register_and_login()

    if not publisher_token or not overtime_user_token:
        return False

    # 创建投票解锁任务
    print("\n📝 步骤2：创建投票解锁任务")
    headers = {'Authorization': f'Token {publisher_token}'}
    task_data = {
        "title": f"测试投票期加时_{int(time.time())}",
        "description": "测试投票期是否可以被加时",
        "task_type": "lock",
        "difficulty": "normal",
        "duration_type": "fixed",
        "duration_value": 1,  # 1分钟任务
        "unlock_type": "vote",
        "vote_threshold": 1,
        "vote_agreement_ratio": 0.8,
        "voting_duration": 1
    }

    response = requests.post(f"{BASE_URL}/api/tasks/", json=task_data, headers=headers)
    if response.status_code != 201:
        print(f"❌ 创建任务失败: {response.status_code} - {response.text}")
        return False

    task = response.json()
    task_id = task['id']
    print(f"✅ 任务创建成功: {task_id}")

    # 等待任务时间结束
    print("\n📝 步骤3：等待任务时间结束")
    time.sleep(65)

    # 开始投票
    print("📝 步骤4：开始投票")
    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/start-voting/", headers=headers)
    if response.status_code != 200:
        print(f"❌ 开始投票失败: {response.status_code} - {response.text}")
        return False

    print("✅ 投票开始成功")

    # 检查任务状态
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}/", headers=headers)
    if response.status_code == 200:
        task_status = response.json()
        print(f"   当前任务状态: {task_status.get('status')}")
        if task_status.get('status') != 'voting':
            print(f"❌ 任务未进入投票状态")
            return False
    else:
        print(f"❌ 获取任务状态失败")
        return False

    # 尝试对投票期任务进行随机加时
    print("\n📝 步骤5：尝试对投票期任务进行随机加时")
    overtime_headers = {'Authorization': f'Token {overtime_user_token}'}
    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/overtime/", headers=overtime_headers)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 投票期加时成功: {data.get('message', '未知')}")
        print(f"   加时分钟: {data.get('overtime_minutes', 'unknown')}")
        print("✅ 测试通过：投票期任务现在可以被随机加时！")
        return True
    else:
        error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {'error': response.text}
        print(f"❌ 投票期加时失败: {error_data.get('error', '未知错误')}")
        print("❌ 测试失败：投票期任务仍然无法被随机加时")
        return False

if __name__ == "__main__":
    try:
        success = test_voting_overtime_api()
        if success:
            print("\n🎉 改进成功！投票状态现在真正成为了一种特殊的带锁状态")
        else:
            print("\n💥 改进失败，需要检查代码")
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        exit(1)