#!/usr/bin/env python3
"""
快速测试投票失败惩罚计算逻辑
直接测试 get_vote_penalty_minutes() 方法是否正确返回基于难度的惩罚时间
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
        "username": f"test_penalty_quick_{int(time.time() * 1000000)}",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "email": f"test_penalty_quick_{int(time.time() * 1000000)}@example.com"
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
        "title": f"测试惩罚计算_{difficulty}_{int(time.time())}",
        "description": f"测试{difficulty}难度的惩罚计算",
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
        print(f"✅ 创建{difficulty}难度任务成功: {task['id']}")
        return task
    else:
        print(f"❌ 创建任务失败: {response.status_code} - {response.text}")
        return None

def simulate_vote_failure_and_check_penalty(token, difficulty, expected_penalty):
    """模拟投票失败并检查惩罚时间"""
    print(f"\n📝 测试{difficulty}难度的投票失败惩罚计算")
    print("-" * 40)

    # 创建任务
    task = create_vote_unlock_task(token, difficulty)
    if not task:
        return False

    task_id = task['id']

    # 等待任务时间结束
    print("⏳ 等待任务时间结束...")
    time.sleep(65)  # 等待1分钟多一点

    # 开始投票
    headers = {'Authorization': f'Token {token}'}
    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/start-voting/", headers=headers)
    if response.status_code != 200:
        print(f"❌ 开始投票失败: {response.status_code} - {response.text}")
        return False
    print("✅ 投票开始成功")

    # 创建第二个用户来投反对票
    voter_user = {
        "username": f"voter_{difficulty}_{int(time.time() * 1000000)}",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "email": f"voter_{difficulty}_{int(time.time() * 1000000)}@example.com"
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

    # 等待投票期结束
    print("⏳ 等待投票期结束...")
    time.sleep(65)

    # 获取投票前的任务状态
    task_before = requests.get(f"{BASE_URL}/api/tasks/{task_id}/", headers=headers)
    if task_before.status_code != 200:
        print(f"❌ 获取任务状态失败: {task_before.status_code}")
        return False

    print(f"   投票前任务状态: {task_before.json().get('status')}")

    # 处理投票结果
    voting_results = requests.post(f"{BASE_URL}/api/tasks/process-voting/", headers=headers)
    if voting_results.status_code != 200:
        print(f"❌ 投票结果处理失败: {voting_results.status_code} - {voting_results.text}")
        return False

    results_data = voting_results.json()
    print(f"✅ 投票结果处理完成")

    # 检查处理结果中的惩罚时间
    processed_tasks = results_data.get('processed_tasks', [])
    matching_task = None
    for processed_task in processed_tasks:
        if processed_task['id'] == str(task_id):
            matching_task = processed_task
            break

    if not matching_task:
        print(f"❌ 未找到处理结果中的任务 {task_id}")
        return False

    if matching_task['result'] != 'failed':
        print(f"❌ 期望投票失败，但结果是: {matching_task['result']}")
        return False

    penalty_minutes = matching_task.get('penalty_minutes')
    if penalty_minutes != expected_penalty:
        print(f"❌ 惩罚时间不正确！期望: {expected_penalty}分钟，实际: {penalty_minutes}分钟")
        return False

    print(f"✅ 投票失败惩罚正确: {penalty_minutes}分钟（{difficulty}难度）")
    return True

def test_vote_penalty_calculation():
    """测试投票失败惩罚计算"""
    print("🧪 快速测试带锁任务投票失败时的惩罚加时功能")
    print("="*60)
    print("测试规则：")
    print("- easy难度：10分钟惩罚")
    print("- normal难度：20分钟惩罚")
    print("- hard难度：30分钟惩罚")
    print("- hell难度：60分钟惩罚")
    print()

    # 注册用户
    token = register_and_login()
    if not token:
        return False

    # 测试一个难度级别来验证修复
    result = simulate_vote_failure_and_check_penalty(token, 'normal', 20)

    if result:
        print("\n🎉 投票失败惩罚计算测试通过！")
        print("💡 修复成功：现在使用基于难度的惩罚时间，而不是硬编码的15分钟")
    else:
        print("\n💥 测试失败，投票失败惩罚计算仍有问题")

    return result

if __name__ == "__main__":
    try:
        success = test_vote_penalty_calculation()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        exit(1)