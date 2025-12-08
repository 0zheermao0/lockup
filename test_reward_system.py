#!/usr/bin/env python3
"""
综合测试脚本：验证奖励系统
测试内容：
1. 每日登录奖励机制
2. 带锁任务完成奖励机制
3. 奖励计算逻辑
"""

import requests
import json
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"

def register_user():
    """注册测试用户"""
    test_user = {
        "username": f"test_rewards_{int(time.time() * 1000000)}",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "email": f"test_rewards_{int(time.time() * 1000000)}@example.com"
    }
    response = requests.post(f"{BASE_URL}/api/auth/register/", json=test_user)
    if response.status_code == 201:
        data = response.json()
        print(f"✅ 用户注册成功: {test_user['username']}")
        print(f"   初始积分: {data['user']['coins']}")
        return data['token'], test_user
    else:
        print(f"❌ 用户注册失败: {response.status_code} - {response.text}")
        return None, None

def login_user(test_user, token=None):
    """用户登录"""
    response = requests.post(f"{BASE_URL}/api/auth/login/", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 用户登录成功")
        print(f"   当前积分: {data['user']['coins']}")
        print(f"   登录消息: {data.get('message', '')}")
        return data['token'], data['user']['coins']
    else:
        print(f"❌ 用户登录失败: {response.status_code} - {response.text}")
        return None, None

def create_lock_task(token, difficulty='normal'):
    """创建带锁任务"""
    headers = {'Authorization': f'Token {token}'}
    task_data = {
        "title": f"测试带锁任务_{difficulty}_{int(time.time())}",
        "description": f"测试{difficulty}难度的带锁任务奖励",
        "task_type": "lock",
        "difficulty": difficulty,
        "duration_type": "fixed",
        "duration_value": 1,  # 1分钟，便于测试
        "unlock_type": "manual"
    }

    response = requests.post(f"{BASE_URL}/api/tasks/", json=task_data, headers=headers)
    if response.status_code == 201:
        task = response.json()
        print(f"✅ 创建{difficulty}难度带锁任务成功: {task['id']}")
        print(f"   任务状态: {task['status']}")
        return task
    else:
        print(f"❌ 创建带锁任务失败: {response.status_code} - {response.text}")
        return None

def complete_lock_task(token, task_id):
    """完成带锁任务"""
    headers = {'Authorization': f'Token {token}'}

    # 等待任务时间结束
    print("⏳ 等待任务时间结束...")
    time.sleep(65)  # 等待1分钟多一点

    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/complete/", headers=headers)
    if response.status_code == 200:
        task = response.json()
        print(f"✅ 任务完成成功")
        print(f"   任务状态: {task['status']}")
        return task
    else:
        print(f"❌ 任务完成失败: {response.status_code} - {response.text}")
        return None

def get_user_profile(token):
    """获取用户资料"""
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(f"{BASE_URL}/api/auth/profile/", headers=headers)
    if response.status_code == 200:
        user = response.json()
        print(f"📊 当前用户状态:")
        print(f"   积分: {user['coins']}")
        print(f"   等级: {user['level']}")
        return user
    else:
        print(f"❌ 获取用户资料失败: {response.status_code} - {response.text}")
        return None

def test_daily_login_rewards():
    """测试每日登录奖励"""
    print("\n" + "="*50)
    print("🧪 测试每日登录奖励")
    print("="*50)

    # 注册新用户
    token, test_user = register_user()
    if not token:
        return False

    # 记录初始积分
    initial_user = get_user_profile(token)
    initial_coins = initial_user['coins']

    # 第一次登录（应该有奖励）
    print("\n📝 第一次登录测试:")
    token1, coins1 = login_user(test_user, token)
    if coins1 is None:
        return False

    reward1 = coins1 - initial_coins
    print(f"   奖励积分: {reward1}")

    # 第二次登录（应该没有额外奖励）
    print("\n📝 第二次登录测试（同一天）:")
    token2, coins2 = login_user(test_user, token1)
    if coins2 is None:
        return False

    reward2 = coins2 - coins1
    print(f"   奖励积分: {reward2}")

    # 验证结果
    if reward1 > 0 and reward2 == 0:
        print("✅ 每日登录奖励测试通过")
        return True
    else:
        print("❌ 每日登录奖励测试失败")
        print(f"   期望: 第一次有奖励({reward1 > 0}), 第二次无奖励({reward2 == 0})")
        return False

def test_lock_task_rewards():
    """测试带锁任务完成奖励"""
    print("\n" + "="*50)
    print("🧪 测试带锁任务完成奖励")
    print("="*50)

    # 注册新用户
    token, test_user = register_user()
    if not token:
        return False

    # 测试不同难度的奖励
    difficulties = ['easy', 'normal', 'hard', 'hell']
    expected_rewards = {'easy': 2, 'normal': 5, 'hard': 10, 'hell': 20}

    for difficulty in difficulties:
        print(f"\n📝 测试{difficulty}难度任务:")

        # 获取完成前积分
        user_before = get_user_profile(token)
        coins_before = user_before['coins']

        # 创建任务
        task = create_lock_task(token, difficulty)
        if not task:
            continue

        # 完成任务
        completed_task = complete_lock_task(token, task['id'])
        if not completed_task:
            continue

        # 获取完成后积分
        user_after = get_user_profile(token)
        coins_after = user_after['coins']

        # 计算奖励
        actual_reward = coins_after - coins_before
        expected_reward = expected_rewards[difficulty]

        print(f"   期望奖励: {expected_reward} 积分")
        print(f"   实际奖励: {actual_reward} 积分")

        if actual_reward >= expected_reward:
            print(f"   ✅ {difficulty}难度奖励正确")
        else:
            print(f"   ❌ {difficulty}难度奖励不正确")
            return False

    print("✅ 带锁任务完成奖励测试通过")
    return True

def main():
    """主测试函数"""
    print("🚀 开始奖励系统综合测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 测试每日登录奖励
    login_test_passed = test_daily_login_rewards()

    # 测试带锁任务奖励
    task_test_passed = test_lock_task_rewards()

    # 总结
    print("\n" + "="*50)
    print("📋 测试总结")
    print("="*50)
    print(f"每日登录奖励: {'✅ 通过' if login_test_passed else '❌ 失败'}")
    print(f"带锁任务奖励: {'✅ 通过' if task_test_passed else '❌ 失败'}")

    if login_test_passed and task_test_passed:
        print("\n🎉 所有奖励系统测试通过！")
        return True
    else:
        print("\n💥 部分测试失败，请检查实现")
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        exit(1)