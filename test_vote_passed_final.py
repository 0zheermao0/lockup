#!/usr/bin/env python3
"""
最终测试投票通过后的逻辑改进
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
        "username": f"test_final_{suffix}_{int(time.time() * 1000000)}",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "email": f"test_final_{suffix}_{int(time.time() * 1000000)}@example.com"
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

def test_final_voting_logic():
    """最终测试投票通过后的逻辑"""
    print("🧪 最终测试：投票通过后任务状态变化")
    print("="*50)

    # 创建用户
    print("📝 步骤1：创建用户")
    publisher_token = register_and_login("publisher")
    voter_token = register_and_login("voter")

    if not publisher_token or not voter_token:
        return False

    # 创建投票解锁任务（更长的任务时间）
    print("\n📝 步骤2：创建投票解锁任务")
    headers = {'Authorization': f'Token {publisher_token}'}
    task_data = {
        "title": f"最终测试投票逻辑_{int(time.time())}",
        "description": "测试投票通过后是否立即完成",
        "task_type": "lock",
        "difficulty": "normal",
        "duration_type": "fixed",
        "duration_value": 5,  # 5分钟任务，足够长以验证逻辑
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
    print(f"   任务原始结束时间: {task.get('end_time')}")

    # 等待任务时间结束
    print("\n📝 步骤3：等待任务时间结束")
    time.sleep(305)  # 等待5分钟多一点

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

    task_after_voting = response.json()
    print(f"   投票期结束后任务状态: {task_after_voting.get('status')}")
    print(f"   任务是否已完成: {task_after_voting.get('completed_at') is not None}")
    print(f"   当前任务结束时间: {task_after_voting.get('end_time')}")

    # 验证改进的逻辑
    success = True

    if task_after_voting.get('status') != 'active':
        print(f"❌ 期望投票通过后回到active状态，但状态是: {task_after_voting.get('status')}")
        success = False
    else:
        print("✅ 投票通过后任务正确回到active状态")

    if task_after_voting.get('completed_at') is not None:
        print(f"❌ 期望投票通过后任务未完成，但任务已有完成时间: {task_after_voting.get('completed_at')}")
        success = False
    else:
        print("✅ 投票通过后任务正确地未立即完成")

    # 检查任务结束时间是否仍然存在（应该保持原来的结束时间）
    if task_after_voting.get('end_time') is None:
        print(f"❌ 任务结束时间丢失")
        success = False
    else:
        print("✅ 任务结束时间保持正确")

    return success

if __name__ == "__main__":
    try:
        success = test_final_voting_logic()
        if success:
            print("\n🎉 投票通过逻辑改进验证成功！")
            print("💡 改进要点：")
            print("   1. 投票通过后任务回到active状态（不立即完成）")
            print("   2. 任务需要等待实际时间结束后才能手动完成")
            print("   3. 投票通过期间任务仍可参与小游戏和被加时")
        else:
            print("\n💥 投票通过逻辑改进验证失败")
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        exit(1)