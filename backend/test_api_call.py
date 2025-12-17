#!/usr/bin/env python
"""
测试实际的API调用
"""

import requests
import json

def test_take_api():
    """测试take API调用"""
    task_id = 'b4989c58-f7a6-4e09-b998-09fa5ca49f75'
    api_url = f'http://localhost:8000/api/tasks/{task_id}/take/'

    print(f"🔗 测试API: {api_url}")
    print()

    # 模拟前端请求（需要认证）
    # 注意：这里需要实际的认证token，可能需要先登录
    headers = {
        'Content-Type': 'application/json',
        # 这里需要实际的认证头，但我们先测试不需要认证的情况
    }

    try:
        response = requests.post(api_url, headers=headers)
        print(f"📊 响应状态码: {response.status_code}")
        print(f"📝 响应内容: {response.text}")

        if response.status_code == 400:
            try:
                error_data = response.json()
                print(f"❌ 错误信息: {error_data.get('error', '未知错误')}")
            except:
                print(f"❌ 无法解析错误响应: {response.text}")
        elif response.status_code == 401:
            print("🔐 需要认证，这是正常的")
        elif response.status_code == 200 or response.status_code == 201:
            print("✅ 请求成功！")
        else:
            print(f"⚠️ 未预期的状态码: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请确认Django服务器正在运行")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == '__main__':
    test_take_api()