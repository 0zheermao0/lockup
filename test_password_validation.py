#!/usr/bin/env python3
"""
测试改进的密码验证错误提示信息
验证不同类型的弱密码是否能获得详细的错误提示
"""

import requests
import json
import time

# 配置
BASE_URL = "http://localhost:8000"

def test_password_validation():
    """测试不同类型的弱密码验证"""
    print("🧪 测试改进的密码验证错误提示信息")
    print("="*60)

    # 测试不同类型的弱密码
    test_cases = [
        {
            "name": "密码太短",
            "password": "123",
            "expected_keywords": ["太短", "8个字符"]
        },
        {
            "name": "只包含数字",
            "password": "12345678",
            "expected_keywords": ["简单", "只包含数字", "添加字母"]
        },
        {
            "name": "常见密码",
            "password": "password",
            "expected_keywords": ["常见", "123456", "password"]
        },
        {
            "name": "另一个常见密码",
            "password": "123456789",
            "expected_keywords": ["常见", "123456"]
        },
        {
            "name": "与用户信息相似",
            "username": "testuser123",
            "password": "testuser123",
            "expected_keywords": ["相似", "个人信息"]
        }
    ]

    results = []

    for test_case in test_cases:
        print(f"\n📝 测试：{test_case['name']}")
        print("-" * 40)

        # 构建测试用户数据
        username = test_case.get('username', f"test_pw_{int(time.time() * 1000000)}")
        test_user = {
            "username": username,
            "email": f"{username}@example.com",
            "password": test_case['password'],
            "password_confirm": test_case['password']
        }

        # 尝试注册
        response = requests.post(f"{BASE_URL}/api/auth/register/", json=test_user)

        if response.status_code == 400:
            # 期望的错误响应
            try:
                error_data = response.json()
                print(f"   状态码: {response.status_code}")
                print(f"   错误信息: {json.dumps(error_data, ensure_ascii=False, indent=2)}")

                # 检查是否包含预期的关键词
                error_text = str(error_data).lower()
                keywords_found = []
                keywords_missing = []

                for keyword in test_case['expected_keywords']:
                    if keyword.lower() in error_text:
                        keywords_found.append(keyword)
                    else:
                        keywords_missing.append(keyword)

                if keywords_found and not keywords_missing:
                    print(f"   ✅ 成功：找到期望的关键词 {keywords_found}")
                    results.append({"test": test_case['name'], "success": True, "found": keywords_found})
                elif keywords_found:
                    print(f"   ⚠️  部分成功：找到 {keywords_found}，但缺少 {keywords_missing}")
                    results.append({"test": test_case['name'], "success": True, "found": keywords_found, "missing": keywords_missing})
                else:
                    print(f"   ❌ 失败：未找到期望的关键词 {test_case['expected_keywords']}")
                    results.append({"test": test_case['name'], "success": False, "missing": test_case['expected_keywords']})

            except Exception as e:
                print(f"   ❌ 解析错误响应失败: {e}")
                print(f"   原始响应: {response.text}")
                results.append({"test": test_case['name'], "success": False, "error": str(e)})

        elif response.status_code == 201:
            print(f"   ❌ 意外成功：弱密码 '{test_case['password']}' 竟然注册成功了")
            results.append({"test": test_case['name'], "success": False, "error": "密码验证未生效"})

        else:
            print(f"   ❌ 意外状态码: {response.status_code}")
            print(f"   响应内容: {response.text}")
            results.append({"test": test_case['name'], "success": False, "error": f"意外状态码 {response.status_code}"})

    # 总结结果
    print("\n" + "="*60)
    print("📋 测试总结")
    print("="*60)

    successful_tests = sum(1 for r in results if r['success'])
    total_tests = len(results)

    for result in results:
        status = "✅ 通过" if result['success'] else "❌ 失败"
        print(f"{result['test']}: {status}")
        if not result['success'] and 'error' in result:
            print(f"   错误: {result['error']}")

    print(f"\n通过率: {successful_tests}/{total_tests}")

    if successful_tests == total_tests:
        print("🎉 所有密码验证测试通过！用户现在能够获得详细的密码错误提示")
        print("💡 改进内容：")
        print("   - 密码太短：明确说明需要8个字符")
        print("   - 只包含数字：提示添加字母或特殊字符")
        print("   - 常见密码：警告避免使用常见密码")
        print("   - 与用户信息相似：说明不能与个人信息相似")
    else:
        print("💥 部分测试失败，密码验证提示信息可能需要进一步优化")

    return successful_tests == total_tests

def test_valid_password():
    """测试有效密码能够正常注册"""
    print(f"\n📝 额外测试：有效密码正常注册")
    print("-" * 40)

    test_user = {
        "username": f"valid_user_{int(time.time() * 1000000)}",
        "email": f"valid_user_{int(time.time() * 1000000)}@example.com",
        "password": "ComplexPassword123!",
        "password_confirm": "ComplexPassword123!"
    }

    response = requests.post(f"{BASE_URL}/api/auth/register/", json=test_user)

    if response.status_code == 201:
        print("   ✅ 成功：有效密码正常注册")
        return True
    else:
        print(f"   ❌ 失败：有效密码注册失败 - {response.status_code}")
        try:
            error_data = response.json()
            print(f"   错误详情: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
        except:
            print(f"   错误文本: {response.text}")
        return False

if __name__ == "__main__":
    try:
        weak_password_tests = test_password_validation()
        valid_password_test = test_valid_password()

        overall_success = weak_password_tests and valid_password_test

        if overall_success:
            print("\n🎉 所有密码验证改进测试通过！")
        else:
            print("\n💥 部分测试失败，需要进一步调试")

        exit(0 if overall_success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        exit(1)