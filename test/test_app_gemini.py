import requests
import json
import os

def test_model(model_type, model_config):
    """测试单个模型"""
    try:
        api_key = model_config.get('apiKey', '')
        if not api_key:
            return {
                'success': False,
                'error': 'API Key 为空'
            }
        
        base_url = model_config.get('baseUrl', '')
        model_name = model_config.get('modelName', '')
        
        test_prompt = "你好，请回复'测试成功'"
        
        if model_type == 'gemini':
            base_url = base_url or "https://generativelanguage.googleapis.com/v1beta"
            model_name = model_name or "gemini-2.5-flash"
            url = f"{base_url}/models/{model_name}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": test_prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 100
                }
            }
            response = requests.post(url, headers=headers, json=data, timeout=30)
            print(f"请求URL: {url}")
            print(f"响应状态码: {response.status_code}")
            result = response.json()
            print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
            if 'candidates' in result:
                return {'success': True}
            else:
                return {'success': False, 'error': result.get('error', {}).get('message', '未知错误')}
        
        else:
            return {'success': False, 'error': '未知的模型类型'}
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

# 读取配置
config_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'config', 'defaultConfig.json')
with open(config_file, 'r', encoding='utf-8') as f:
    config = json.load(f)

gemini_config = config['models']['gemini']
print("Gemini配置:")
print(f"  API Key: {gemini_config['apiKey'][:15]}...")
print(f"  baseUrl: {gemini_config['baseUrl']}")
print(f"  modelName: {gemini_config['modelName']}")
print()

print("开始测试Gemini模型...")
result = test_model('gemini', gemini_config)
print(f"\n测试结果: {result}")

if result['success']:
    print("✓ Gemini模型测试成功！")
else:
    print(f"✗ Gemini模型测试失败: {result.get('error', '未知错误')}")
