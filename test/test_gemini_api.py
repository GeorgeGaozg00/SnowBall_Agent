import requests
import json
import os

# 1. 从系统配置文件获取API密钥
def test_gemini_api():
    try:
        # 读取系统配置文件
        config_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'config', 'config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 获取Gemini API密钥
            api_key = config.get('models', {}).get('gemini', {}).get('apiKey')
            if not api_key:
                print("系统配置文件中未找到Gemini API密钥")
                return
            
            print(f"从系统配置获取API密钥成功: {api_key[:10]}...")
        else:
            print("系统配置文件不存在")
            return
        
        # 2. 列出可用的模型
        print("\n列出可用的Gemini模型...")
        models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        models_response = requests.get(models_url, timeout=30)
        print(f"模型列表HTTP状态码: {models_response.status_code}")
        
        if models_response.status_code == 200:
            models_result = models_response.json()
            print("\n可用模型:")
            for model in models_result.get('models', []):
                print(f"- {model.get('name')} (基础模型: {model.get('baseModelId', 'N/A')})")
                print(f"  描述: {model.get('description', 'N/A')}")
                print(f"  支持的方法: {model.get('supportedGenerationMethods', [])}")
                print()
        else:
            print(f"获取模型列表失败: {models_response.text}")
            return
        
        # 3. 测试文本生成（使用可用的模型）
        print("\n测试文本生成...")
        # 使用gemini-2.5-flash模型
        text_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {
            "Content-Type": "application/json"
        }
        text_payload = {
            "contents": [{
                "parts": [{
                    "text": "请问你是谁？"
                }]
            }]
        }
        
        text_response = requests.post(text_url, headers=headers, json=text_payload, timeout=30)
        print(f"文本生成HTTP状态码: {text_response.status_code}")
        
        if text_response.status_code == 200:
            text_result = text_response.json()
            print("\n生成结果:")
            if 'candidates' in text_result and len(text_result['candidates']) > 0:
                text = text_result['candidates'][0]['content']['parts'][0]['text']
                print(text)
            else:
                print("未找到生成内容")
        else:
            print(f"文本生成失败: {text_response.text}")
        
        # 4. 测试图片生成（使用Imagen模型）
        print("\n测试图片生成能力...")
        # 使用Imagen 4.0模型
        image_url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={api_key}"
        image_payload = {
            "instances": [{
                "prompt": "生成一张关于投资分析的图片，展示金融图表和上升趋势，专业风格"
            }],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "16:9",
                "quality": "high"
            }
        }
        
        image_response = requests.post(image_url, headers=headers, json=image_payload, timeout=60)
        print(f"图片生成HTTP状态码: {image_response.status_code}")
        
        if image_response.status_code == 200:
            image_result = image_response.json()
            print("图片生成成功！")
            print("响应结果:", json.dumps(image_result, indent=2)[:500], "...")
        else:
            print(f"图片生成失败: {image_response.text}")
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    print("Google Gemini API 测试 (HTTP API)")
    print("=" * 50)
    test_gemini_api()
    print("\n测试完成")
