#!/usr/bin/env python3
"""
快速测试投票通过后的逻辑改进
验证投票通过后任务不立即完成，而是回到active状态等待实际时间结束
"""

import requests
import json
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"

def register_and_login(suffix):
    """注册并登录测试用户"""
    test_user = {
        "username": f"test_vote_passed_{suffix}_{int(time.time() * 1000000)}",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "email": f"test_vote_passed_{suffix}_{int(time.time() * 1000000)}@example.com"
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

def test_vote_passed_logic():
    """测试投票通过后的逻辑"""
    print("🧪 快速测试投票通过后的逻辑改进")
    print("="*50)

    # 创建用户
    print("📝 步骤1：创建用户")
    publisher_token = register_and_login("publisher")
    voter_token = register_and_login("voter")

    if not publisher_token or not voter_token:
        return False

    # 创建投票解锁任务
    print("\n📝 步骤2：创建投票解锁任务")
    headers = {'Authorization': f'Token {publisher_token}'}
    task_data = {
        "title": f"测试投票通过逻辑_{int(time.time())}",
        "description": "测试投票通过后是否立即完成",
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

    # 投同意票
    print("\n📝 步骤5：投同意票")
    voter_headers = {'Authorization': f'Token {voter_token}'}
    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/vote/",
                           json={"agree": True}, headers=voter_headers)
    if response.status_code != 201:
        print(f"❌ 投票失败: {response.status_code} - {response.text}")
        return False

    print("✅ 投同意票成功")

    # 等待投票期结束
    print("\n📝 步骤6：等待投票期结束")
    time.sleep(65)

    # 检查投票期结束后的任务状态
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}/", headers=headers)
    if response.status_code != 200:
        print(f"❌ 获取任务状态失败")
        return False

    task_before_process = response.json()
    print(f"   投票期结束后任务状态: {task_before_process.get('status')}")

    # 手动处理投票结果
    print("\n📝 步骤7：处理投票结果")
    response = requests.post(f"{BASE_URL}/api/tasks/process-voting/", headers=headers)
    if response.status_code != 200:
        print(f"❌ 处理投票结果失败: {response.status_code} - {response.text}")
        return False

    voting_results = response.json()
    print(f"✅ 投票结果处理完成")

    # 检查处理结果
    processed_tasks = voting_results.get('processed_tasks', [])
    matching_task = None
    for processed_task in processed_tasks:
        if processed_task['id'] == task_id:
            matching_task = processed_task
            break

    if not matching_task:
        print(f"❌ 未找到处理结果中的任务 {task_id}")
        return False

    print(f"   投票结果: {matching_task['result']}")
    print(f"   投票统计: {matching_task['votes']}")
    print(f"   同意率: {matching_task['ratio']}")

    if matching_task['result'] != 'passed':
        print(f"❌ 期望投票通过，但结果是: {matching_task['result']}")
        return False

    # 检查投票处理后的任务状态
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}/", headers=headers)
    if response.status_code != 200:
        print(f"❌ 获取任务状态失败")
        return False

    task_after_process = response.json()
    print(f"   投票处理后任务状态: {task_after_process.get('status')}")
    print(f"   任务是否已完成: {task_after_process.get('completed_at') is not None}")

    # 验证改进的逻辑
    if task_after_process.get('status') != 'active':
        print(f"❌ 期望投票通过后回到active状态，但状态是: {task_after_process.get('status')}")
        return False

    if task_after_process.get('completed_at') is not None:
        print(f"❌ 期望投票通过后任务未完成，但任务已有完成时间")
        return False

    if matching_task.get('status') != 'waiting_for_time_end':
        print(f"❌ 期望返回waiting_for_time_end状态，但是: {matching_task.get('status')}")
        return False

    print("✅ 测试通过：投票通过后任务正确回到active状态，等待实际时间结束")
    print("💡 改进成功：投票通过不再立即完成任务！")
    return True

if __name__ == "__main__":
    try:
        success = test_vote_passed_logic()
        if success:
            print("\n🎉 投票通过逻辑改进成功！")
            print("💡 现在投票通过后任务会回到active状态，等待实际时间结束才能完成")
        else:
            print("\n💥 投票通过逻辑改进失败")
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        exit(1)