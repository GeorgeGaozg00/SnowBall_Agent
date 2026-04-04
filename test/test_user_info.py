import requests
import json
import os

def test_user_info():
    """测试用户信息获取功能"""
    try:
        # 读取用户配置文件
        users_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'users.json')
        if os.path.exists(users_file):
            with open(users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            
            if users_data.get('users'):
                user = users_data['users'][0]
                cookie = user.get('cookie')
                print(f"测试用户cookie: {cookie[:50]}...")
                
                # 测试获取用户信息
                url = "https://xueqiu.com/statuses/original/timeline.json"
                headers = {
                    "Cookie": cookie.strip(),
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                
                print("正在请求雪球API...")
                response = requests.get(url, headers=headers, timeout=10)
                print(f"HTTP状态码: {response.status_code}")
                print(f"响应内容: {response.text[:500]}...")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"响应JSON: {json.dumps(data, ensure_ascii=False)[:500]}...")
                    if 'user' in data:
                        print("成功获取用户信息")
                        print(f"用户ID: {data['user'].get('id')}")
                        print(f"用户名称: {data['user'].get('screen_name')}")
                        print(f"用户头像: {data['user'].get('profile_image_url')}")
                        print(f"用户简介: {data['user'].get('description')}")
                    else:
                        print("响应中没有user字段")
                else:
                    print(f"请求失败: {response.status_code}")
            else:
                print("用户列表为空")
        else:
            print("用户配置文件不存在")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    print("测试用户信息获取功能")
    print("=" * 50)
    test_user_info()
    print("\n测试完成")
