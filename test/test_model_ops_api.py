import requests
import json

API_BASE_URL = 'http://127.0.0.1:5001/api'

print("测试模型操作日志API...")
try:
    response = requests.get(f'{API_BASE_URL}/model-operations', timeout=10)
    print(f"响应状态码: {response.status_code}")
    
    result = response.json()
    print(f"\n响应数据:")
    print(f"  success: {result.get('success')}")
    
    if result.get('success'):
        data = result.get('data', [])
        print(f"  日志数量: {len(data)}")
        if data:
            print(f"\n第一条日志:")
            print(json.dumps(data[0], indent=2, ensure_ascii=False)[:500])
    else:
        print(f"  message: {result.get('message')}")
        
except Exception as e:
    print(f"请求失败: {e}")
    import traceback
    traceback.print_exc()
