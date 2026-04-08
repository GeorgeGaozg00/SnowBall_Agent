import requests
import os
import json

# 禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

print("其他API连接测试")
print("=" * 50)

# 读取配置文件
config_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'config', 'config.json')
config = {}
if os.path.exists(config_file):
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    print("✓ 配置文件读取成功")
else:
    print("✗ 配置文件不存在")
    exit(1)

# 1. 测试DeepSeek API
print("\n1. 测试DeepSeek API...")
try:
    deepseek_config = config.get('models', {}).get('deepseek', {})
    api_key = deepseek_config.get('apiKey')
    base_url = deepseek_config.get('baseUrl')
    
    if api_key and base_url:
        print(f"   API Key: {api_key[:10]}...")
        print(f"   Base URL: {base_url}")
        
        # 测试连接
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 先测试获取模型列表
        models_url = f"{base_url}/models"
        response = requests.get(models_url, headers=headers, timeout=10, proxies={'http': None, 'https': None})
        print(f"   模型列表状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✓ DeepSeek API 连接成功")
        else:
            print(f"   ✗ DeepSeek API 连接失败: {response.text[:200]}")
    else:
        print("   ✗ DeepSeek API 未配置")
except Exception as e:
    print(f"   ✗ DeepSeek API 测试失败: {str(e)}")

# 2. 测试通义千问API
print("\n2. 测试通义千问API...")
try:
    alibaba_config = config.get('models', {}).get('alibaba', {})
    api_key = alibaba_config.get('apiKey')
    
    if api_key:
        print(f"   API Key: {api_key[:10]}...")
        # 通义千问使用DashScope API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 测试连接（简单的ping）
        test_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        # 不实际调用，只测试连接
        print("   ✓ 通义千问API 配置存在")
    else:
        print("   ✗ 通义千问API 未配置")
except Exception as e:
    print(f"   ✗ 通义千问API 测试失败: {str(e)}")

# 3. 测试火山引擎API
print("\n3. 测试火山引擎API...")
try:
    ark_config = config.get('models', {}).get('ark', {})
    api_key = ark_config.get('apiKey')
    
    if api_key:
        print(f"   API Key: {api_key[:10]}...")
        print("   ✓ 火山引擎API 配置存在")
    else:
        print("   ✗ 火山引擎API 未配置")
except Exception as e:
    print(f"   ✗ 火山引擎API 测试失败: {str(e)}")

# 4. 测试Claude API
print("\n4. 测试Claude API...")
try:
    claude_config = config.get('models', {}).get('claude', {})
    api_key = claude_config.get('apiKey')
    base_url = claude_config.get('baseUrl')
    
    if api_key and base_url:
        print(f"   API Key: {api_key[:10]}...")
        print(f"   Base URL: {base_url}")
        
        # 测试连接
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 先测试获取模型列表
        models_url = f"{base_url}/models"
        response = requests.get(models_url, headers=headers, timeout=10, proxies={'http': None, 'https': None})
        print(f"   模型列表状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✓ Claude API 连接成功")
        else:
            print(f"   ✗ Claude API 连接失败: {response.text[:200]}")
    else:
        print("   ✗ Claude API 未配置")
except Exception as e:
    print(f"   ✗ Claude API 测试失败: {str(e)}")

print("\n" + "=" * 50)
print("API测试完成")
