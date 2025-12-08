#!/usr/bin/env python3
"""
测试带锁任务投票失败时的惩罚加时功能
验证不同难度级别的任务投票失败时是否应用了正确的惩罚时间
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
        "username": f"test_vote_penalty_{username_suffix}_{int(time.time() * 1000000)}",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "email": f"test_vote_penalty_{username_suffix}_{int(time.time() * 1000000)}@example.com"
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

def create_vote_unlock_task(token, difficulty='normal'):
    """创建投票解锁的带锁任务"""
    headers = {'Authorization': f'Token {token}'}
    task_data = {
        "title": f"测试投票惩罚_{difficulty}_{int(time.time())}",
        "description": f"测试{difficulty}难度的投票失败惩罚",
        "task_type": "lock",
        "difficulty": difficulty,
        "duration_type": "fixed",
        "duration_value": 1,  # 1分钟任务，便于快速测试
        "unlock_type": "vote",
        "vote_threshold": 1,  # 至少需要1票
        "vote_agreement_ratio": 0.8,  # 需要80%同意率
        "voting_duration": 1  # 1分钟投票期
    }

    response = requests.post(f"{BASE_URL}/api/tasks/", json=task_data, headers=headers)
    if response.status_code == 201:
        task = response.json()
        print(f"✅ 创建{difficulty}难度投票任务成功: {task['id']}")
        return task
    else:
        print(f"❌ 创建任务失败: {response.status_code} - {response.text}")
        return None

def start_voting(token, task_id):
    """开始投票"""
    headers = {'Authorization': f'Token {token}'}
    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/start-voting/", headers=headers)

    if response.status_code == 200:
        print(f"✅ 投票开始成功")
        return True
    else:
        print(f"❌ 开始投票失败: {response.status_code} - {response.text}")
        return False

def vote_against_task(token, task_id):
    """对任务投反对票"""
    headers = {'Authorization': f'Token {token}'}
    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/vote/",
                           json={"agree": False}, headers=headers)

    if response.status_code == 201:
        print(f"✅ 投票成功（反对）")
        return True
    else:
        print(f"❌ 投票失败: {response.status_code} - {response.text}")
        return False

def get_task_details(token, task_id):
    """获取任务详情"""
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}/", headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ 获取任务详情失败: {response.status_code} - {response.text}")
        return None

def process_voting_results():
    """手动触发投票结果处理"""
    response = requests.post(f"{BASE_URL}/api/tasks/process-voting/")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 投票结果处理完成: {data.get('message', '未知')}")
        return data
    else:
        print(f"❌ 投票结果处理失败: {response.status_code} - {response.text}")
        return None

def test_vote_penalty_for_difficulty(difficulty, expected_penalty):
    """测试特定难度的投票失败惩罚"""
    print(f"\n📝 测试{difficulty}难度任务的投票失败惩罚")
    print("-" * 50)

    # 创建任务发布者和投票者
    publisher_token, publisher_username = register_and_login(f"publisher_{difficulty}")
    voter_token, voter_username = register_and_login(f"voter_{difficulty}")

    if not publisher_token or not voter_token:
        return False

    # 创建投票解锁任务
    task = create_vote_unlock_task(publisher_token, difficulty)
    if not task:
        return False

    task_id = task['id']

    # 等待任务时间结束
    print("⏳ 等待任务时间结束...")
    time.sleep(65)  # 等待1分钟多一点

    # 开始投票
    if not start_voting(publisher_token, task_id):
        return False

    # 投反对票
    if not vote_against_task(voter_token, task_id):
        return False

    # 等待投票期结束
    print("⏳ 等待投票期结束...")
    time.sleep(65)  # 等待投票期结束

    # 获取投票前的任务状态
    task_before = get_task_details(publisher_token, task_id)
    if not task_before:
        return False

    print(f"   投票前任务状态: {task_before.get('status')}")

    # 处理投票结果
    voting_results = process_voting_results()
    if not voting_results:
        return False

    # 获取投票后的任务状态
    task_after = get_task_details(publisher_token, task_id)
    if not task_after:
        return False

    print(f"   投票后任务状态: {task_after.get('status')}")

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

    if matching_task['result'] != 'failed':
        print(f"❌ 期望投票失败，但结果是: {matching_task['result']}")
        return False

    penalty_minutes = matching_task.get('penalty_minutes')
    if penalty_minutes != expected_penalty:
        print(f"❌ 惩罚时间不正确！期望: {expected_penalty}分钟，实际: {penalty_minutes}分钟")
        return False

    print(f"✅ 投票失败惩罚正确: {penalty_minutes}分钟（{difficulty}难度）")
    return True

def test_vote_penalty_system():
    """测试投票失败惩罚系统"""
    print("🧪 测试带锁任务投票失败时的惩罚加时功能")
    print("="*60)
    print("测试规则：")
    print("- easy难度：10分钟惩罚")
    print("- normal难度：20分钟惩罚")
    print("- hard难度：30分钟惩罚")
    print("- hell难度：60分钟惩罚")
    print()

    # 测试不同难度的惩罚
    test_cases = [
        ('easy', 10),
        ('normal', 20),
        ('hard', 30),
        ('hell', 60)
    ]

    results = []
    for difficulty, expected_penalty in test_cases:
        result = test_vote_penalty_for_difficulty(difficulty, expected_penalty)
        results.append((difficulty, result))

    # 总结结果
    print("\n" + "="*60)
    print("📋 测试总结")
    print("="*60)

    all_passed = True
    for difficulty, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{difficulty}难度惩罚测试: {status}")
        if not result:
            all_passed = False

    if all_passed:
        print("\n🎉 所有投票失败惩罚测试通过！")
        print("💡 不同难度的任务投票失败时都应用了正确的惩罚时间")
    else:
        print("\n💥 部分测试失败，投票失败惩罚系统存在问题")

    return all_passed

if __name__ == "__main__":
    try:
        success = test_vote_penalty_system()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        exit(1)