#!/usr/bin/env python3
"""
测试改进后的投票状态逻辑
验证：
1. 投票期任务可以被随机加时
2. 投票通过后任务不会立即完成，而是回到active状态等待实际时间结束
3. 投票期任务可以参与小时奖励
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
        "username": f"test_improved_voting_{username_suffix}_{int(time.time() * 1000000)}",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "email": f"test_improved_voting_{username_suffix}_{int(time.time() * 1000000)}@example.com"
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
        "title": f"测试改进投票_{difficulty}_{int(time.time())}",
        "description": f"测试改进后的{difficulty}难度投票逻辑",
        "task_type": "lock",
        "difficulty": difficulty,
        "duration_type": "fixed",
        "duration_value": 2,  # 2分钟任务
        "unlock_type": "vote",
        "vote_threshold": 1,
        "vote_agreement_ratio": 0.8,
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

def get_task_status(token, task_id):
    """获取任务状态"""
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}/", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ 获取任务状态失败: {response.status_code}")
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

def vote_for_task(token, task_id, agree=True):
    """对任务投票"""
    headers = {'Authorization': f'Token {token}'}
    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/vote/",
                           json={"agree": agree}, headers=headers)

    if response.status_code == 201:
        print(f"✅ 投票成功（{'同意' if agree else '反对'}）")
        return True
    else:
        print(f"❌ 投票失败: {response.status_code} - {response.text}")
        return False

def process_voting_results(token):
    """处理投票结果"""
    headers = {'Authorization': f'Token {token}'}
    response = requests.post(f"{BASE_URL}/api/tasks/process-voting/", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 投票结果处理完成: {data.get('message', '未知')}")
        return data
    else:
        print(f"❌ 投票结果处理失败: {response.status_code} - {response.text}")
        return None

def test_voting_overtime():
    """测试投票期任务可以被随机加时"""
    print("📝 测试1：投票期任务可以被随机加时")
    print("-" * 40)

    # 创建任务发布者和加时操作者
    publisher_token, publisher_username = register_and_login("publisher")
    overtime_user_token, overtime_user_username = register_and_login("overtime_user")

    if not publisher_token or not overtime_user_token:
        return False

    # 创建投票解锁任务
    task = create_vote_unlock_task(publisher_token, 'normal')
    if not task:
        return False

    task_id = task['id']

    # 等待任务时间结束
    print("⏳ 等待任务时间结束...")
    time.sleep(125)  # 等待2分钟多一点

    # 开始投票
    if not start_voting(publisher_token, task_id):
        return False

    # 检查任务是否进入投票状态
    task_status = get_task_status(publisher_token, task_id)
    if not task_status or task_status.get('status') != 'voting':
        print(f"❌ 任务未进入投票状态: {task_status.get('status') if task_status else 'unknown'}")
        return False

    print(f"✅ 任务已进入投票状态")

    # 尝试对投票期任务进行随机加时
    overtime_success = add_overtime_to_task(overtime_user_token, task_id)

    if overtime_success:
        print("✅ 测试1通过：投票期任务可以被随机加时")
        return True
    else:
        print("❌ 测试1失败：投票期任务无法被随机加时")
        return False

def test_voting_passed_logic():
    """测试投票通过后的逻辑"""
    print("\n📝 测试2：投票通过后任务不立即完成，而是等待实际时间结束")
    print("-" * 50)

    # 创建任务发布者和投票者
    publisher_token, publisher_username = register_and_login("publisher2")
    voter_token, voter_username = register_and_login("voter")

    if not publisher_token or not voter_token:
        return False

    # 创建投票解锁任务
    task = create_vote_unlock_task(publisher_token, 'normal')
    if not task:
        return False

    task_id = task['id']

    # 等待任务时间结束
    print("⏳ 等待任务时间结束...")
    time.sleep(125)  # 等待2分钟多一点

    # 开始投票
    if not start_voting(publisher_token, task_id):
        return False

    # 投同意票
    if not vote_for_task(voter_token, task_id, agree=True):
        return False

    # 等待投票期结束
    print("⏳ 等待投票期结束...")
    time.sleep(65)

    # 获取投票前的任务状态
    task_before = get_task_status(publisher_token, task_id)
    if not task_before:
        return False

    print(f"   投票期结束后任务状态: {task_before.get('status')}")

    # 处理投票结果
    voting_results = process_voting_results(publisher_token)
    if not voting_results:
        return False

    # 获取投票后的任务状态
    task_after = get_task_status(publisher_token, task_id)
    if not task_after:
        return False

    print(f"   投票处理后任务状态: {task_after.get('status')}")
    print(f"   任务结束时间: {task_after.get('end_time')}")

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

    if matching_task['result'] != 'passed':
        print(f"❌ 期望投票通过，但结果是: {matching_task['result']}")
        return False

    if task_after.get('status') != 'active':
        print(f"❌ 期望投票通过后回到active状态，但状态是: {task_after.get('status')}")
        return False

    if matching_task.get('status') != 'waiting_for_time_end':
        print(f"❌ 期望返回waiting_for_time_end状态，但是: {matching_task.get('status')}")
        return False

    print("✅ 测试2通过：投票通过后任务回到active状态，等待实际时间结束")
    return True

def test_improved_voting_system():
    """测试改进后的投票系统"""
    print("🧪 测试改进后的投票状态逻辑")
    print("="*60)
    print("改进内容：")
    print("1. 投票期任务可以被随机加时")
    print("2. 投票通过后任务不立即完成，而是等待实际时间结束")
    print("3. 投票期任务可以参与小时奖励（已有功能）")
    print()

    # 测试1：投票期随机加时
    test1_result = test_voting_overtime()

    # 测试2：投票通过逻辑
    test2_result = test_voting_passed_logic()

    # 总结结果
    print("\n" + "="*60)
    print("📋 测试总结")
    print("="*60)

    all_passed = True

    if test1_result:
        print("✅ 测试1通过：投票期任务可以被随机加时")
    else:
        print("❌ 测试1失败：投票期任务无法被随机加时")
        all_passed = False

    if test2_result:
        print("✅ 测试2通过：投票通过后正确等待实际时间结束")
    else:
        print("❌ 测试2失败：投票通过后逻辑不正确")
        all_passed = False

    if all_passed:
        print("\n🎉 所有测试通过！投票状态逻辑改进成功")
        print("💡 投票期现在真正成为了一种特殊的带锁状态")
    else:
        print("\n💥 部分测试失败，需要进一步调试")

    return all_passed

if __name__ == "__main__":
    try:
        success = test_improved_voting_system()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        exit(1)