#!/usr/bin/env python3
"""
调试版本的投票失败惩罚测试
添加更多调试信息来理解投票处理过程
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
        "username": f"test_penalty_debug_{int(time.time() * 1000000)}",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "email": f"test_penalty_debug_{int(time.time() * 1000000)}@example.com"
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

def create_vote_unlock_task(token, difficulty='normal'):
    """创建投票解锁的带锁任务"""
    headers = {'Authorization': f'Token {token}'}
    task_data = {
        "title": f"调试惩罚计算_{difficulty}_{int(time.time())}",
        "description": f"调试{difficulty}难度的惩罚计算",
        "task_type": "lock",
        "difficulty": difficulty,
        "duration_type": "fixed",
        "duration_value": 1,  # 1分钟任务
        "unlock_type": "vote",
        "vote_threshold": 1,
        "vote_agreement_ratio": 0.8,
        "voting_duration": 1
    }

    response = requests.post(f"{BASE_URL}/api/tasks/", json=task_data, headers=headers)
    if response.status_code == 201:
        task = response.json()
        print(f"✅ 创建{difficulty}难度任务成功")
        print(f"   任务ID: {task['id']}")
        print(f"   任务状态: {task.get('status')}")
        print(f"   投票期长度: {task.get('voting_duration')}分钟")
        return task
    else:
        print(f"❌ 创建任务失败: {response.status_code} - {response.text}")
        return None

def get_task_status(token, task_id):
    """获取任务状态"""
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}/", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ 获取任务状态失败: {response.status_code}")
        return None

def debug_vote_penalty():
    """调试投票失败惩罚"""
    print("🧪 调试带锁任务投票失败时的惩罚加时功能")
    print("="*60)

    # 注册用户
    token = register_and_login()
    if not token:
        return False

    # 创建任务
    task = create_vote_unlock_task(token, 'normal')
    if not task:
        return False

    task_id = task['id']
    headers = {'Authorization': f'Token {token}'}

    # 等待任务时间结束
    print("\n📝 步骤1：等待任务时间结束")
    time.sleep(65)

    # 检查任务状态
    task_status = get_task_status(token, task_id)
    print(f"   任务时间结束后状态: {task_status.get('status') if task_status else 'unknown'}")

    # 开始投票
    print("\n📝 步骤2：开始投票")
    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/start-voting/", headers=headers)
    if response.status_code != 200:
        print(f"❌ 开始投票失败: {response.status_code} - {response.text}")
        return False
    print("✅ 投票开始成功")

    # 检查投票后的任务状态
    task_status = get_task_status(token, task_id)
    if task_status:
        print(f"   投票开始后状态: {task_status.get('status')}")
        print(f"   投票开始时间: {task_status.get('voting_start_time')}")
        print(f"   投票结束时间: {task_status.get('voting_end_time')}")

    # 创建投票者
    print("\n📝 步骤3：创建投票者并投反对票")
    voter_user = {
        "username": f"voter_debug_{int(time.time() * 1000000)}",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "email": f"voter_debug_{int(time.time() * 1000000)}@example.com"
    }

    voter_response = requests.post(f"{BASE_URL}/api/auth/register/", json=voter_user)
    if voter_response.status_code != 201:
        print(f"❌ 投票者注册失败: {voter_response.status_code}")
        return False

    voter_login = requests.post(f"{BASE_URL}/api/auth/login/", json={
        "username": voter_user["username"],
        "password": voter_user["password"]
    })
    if voter_login.status_code != 200:
        print(f"❌ 投票者登录失败: {voter_login.status_code}")
        return False

    voter_token = voter_login.json()['token']
    voter_headers = {'Authorization': f'Token {voter_token}'}

    # 投反对票
    vote_response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/vote/",
                                json={"agree": False}, headers=voter_headers)
    if vote_response.status_code != 201:
        print(f"❌ 投票失败: {vote_response.status_code} - {vote_response.text}")
        return False
    print("✅ 投票成功（反对）")

    # 检查投票后的任务状态
    task_status = get_task_status(token, task_id)
    if task_status:
        print(f"   投票后任务状态: {task_status.get('status')}")
        print(f"   当前投票数: {task_status.get('vote_count', 0)}")
        print(f"   同意票数: {task_status.get('vote_agreement_count', 0)}")

    # 等待投票期结束
    print("\n📝 步骤4：等待投票期结束")
    time.sleep(65)

    # 再次检查任务状态
    task_status = get_task_status(token, task_id)
    if task_status:
        print(f"   投票期结束后状态: {task_status.get('status')}")
        print(f"   投票结束时间: {task_status.get('voting_end_time')}")
        print(f"   当前时间: {datetime.now().isoformat()}")

    # 处理投票结果
    print("\n📝 步骤5：处理投票结果")
    voting_results = requests.post(f"{BASE_URL}/api/tasks/process-voting/", headers=headers)
    print(f"   处理投票结果响应码: {voting_results.status_code}")

    if voting_results.status_code == 200:
        results_data = voting_results.json()
        print(f"   处理结果: {json.dumps(results_data, indent=2)}")

        # 检查处理后的任务状态
        task_status_after = get_task_status(token, task_id)
        if task_status_after:
            print(f"   处理后任务状态: {task_status_after.get('status')}")
            print(f"   任务结束时间: {task_status_after.get('end_time')}")
            print(f"   投票失败惩罚分钟: {task_status_after.get('vote_failed_penalty_minutes')}")

        return True
    else:
        print(f"❌ 投票结果处理失败: {voting_results.status_code} - {voting_results.text}")
        return False

if __name__ == "__main__":
    try:
        debug_vote_penalty()
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()