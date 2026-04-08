import requests
import os

print("网络连接测试（使用代理）")
print("=" * 50)

# 1. 测试访问百度（国内网站）
print("\n1. 测试访问百度...")
try:
    response = requests.get("https://www.baidu.com", timeout=10)
    print(f"   ✓ 成功，状态码: {response.status_code}")
except Exception as e:
    print(f"   ✗ 失败: {str(e)}")

# 2. 测试访问Google
print("\n2. 测试访问Google...")
try:
    response = requests.get("https://www.google.com", timeout=10)
    print(f"   ✓ 成功，状态码: {response.status_code}")
except Exception as e:
    print(f"   ✗ 失败: {str(e)}")

# 3. 测试访问Gemini API
print("\n3. 测试访问Gemini API...")
try:
    response = requests.get("https://generativelanguage.googleapis.com", timeout=10)
    print(f"   ✓ 成功，状态码: {response.status_code}")
except Exception as e:
    print(f"   ✗ 失败: {str(e)}")

print("\n" + "=" * 50)
print("网络测试完成")
