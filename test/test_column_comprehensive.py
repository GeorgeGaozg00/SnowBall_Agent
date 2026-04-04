#!/usr/bin/env python3
"""
雪球专栏文章发布 - 全面测试版
尝试多种API端点和参数组合
"""

import requests
import json
import os

# 读取配置文件
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

COOKIE = config.get('xueQiuCookie', '')

# 专栏文章内容
ARTICLE = {
    "title": "API 专栏文章测试",
    "status": """<p>这是一篇测试专栏文章。</p>
<p>本文尝试通过API发布为专栏文章。</p>
<p>专栏文章应该具有以下特点：</p>
<ol>
<li>显示在作者的专栏中</li>
<li>获得更多的曝光和推荐</li>
<li>有更高的权重</li>
</ol>
<p>通过测试不同的API端点和参数，我们希望找到发布专栏文章的正确方法。</p>
<p>感谢您的关注！</p>""",
    "cover_pic": "",
    "show_cover_pic": "true",
    "original": "false",
    "comment_disabled": "false"
}

def get_session_token(cookie):
    """获取session_token"""
    session = requests.Session()
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": cookie.strip().replace("\n", ""),
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://xueqiu.com/write",
        "Origin": "https://xueqiu.com",
        "Host": "xueqiu.com"
    }
    
    try:
        # 尝试获取session_token
        token_url = "https://xueqiu.com/provider/session/token.json?api_path=%2Fstatuses%2Fupdate.json"
        token_response = session.get(token_url, headers=headers)
        if token_response.status_code == 200:
            token_data = token_response.json()
            session_token = token_data.get('session_token')
            if session_token:
                print(f"获取 session_token 成功：{session_token[:20]}...")
                return session_token
    except Exception as e:
        print(f"获取session_token失败: {e}")
    return None

def test_publish(cookie, article, api_endpoint, params):
    """测试发布文章"""
    session = requests.Session()
    
    # 构造请求头
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": cookie.strip().replace("\n", ""),
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://xueqiu.com/write",
        "Origin": "https://xueqiu.com",
        "Host": "xueqiu.com"
    }
    
    # 获取session_token
    session_token = get_session_token(cookie)
    if not session_token:
        print("无法获取session_token")
        return False
    
    # 构造请求数据
    data = {
        "title": article["title"],
        "status": article["status"],
        "cover_pic": article["cover_pic"],
        "show_cover_pic": article["show_cover_pic"],
        "original": article["original"],
        "comment_disabled": article["comment_disabled"],
        "session_token": session_token,
        "device": "Web",
        "right": "0",
        "draft_id": "0"
    }
    
    # 添加额外参数
    data.update(params)
    
    # 发送请求
    try:
        resp = session.post(api_endpoint, data=data, headers=headers)
        print(f"响应状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            try:
                result = resp.json()
                print(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}...")
                
                if "id" in result:
                    print("✅ 发文成功！")
                    print(f"文章ID：{result['id']}")
                    print(f"文章链接：https://xueqiu.com/{result.get('user_id', '5678597326')}/{result['id']}")
                    print(f"文章类型：{result.get('type')}")
                    print(f"是否专栏：{result.get('is_column')}")
                    return True
                else:
                    print("❌ 发文失败，响应中没有id字段")
            except json.JSONDecodeError:
                print(f"❌ 响应不是JSON格式: {resp.text[:200]}...")
        else:
            print(f"❌ 请求失败，状态码: {resp.status_code}")
            print(f"响应内容: {resp.text[:200]}...")
            
    except Exception as e:
        print(f"❌ 发送请求失败: {e}")
    
    return False

def main():
    print("雪球专栏文章发布测试 - 全面测试版")
    print("=" * 60)
    
    if not COOKIE:
        print("❌ 未找到cookie，请检查配置文件")
        return
    
    # 测试不同的API端点
    api_endpoints = [
        "https://xueqiu.com/statuses/update.json",
        "https://xueqiu.com/notes/create.json",
        "https://mp.xueqiu.com/xq/statuses/update.json",
        "https://mp.xueqiu.com/statuses/update.json"
    ]
    
    # 测试不同的参数组合
    param_combinations = [
        {"type": "8", "is_column": "true", "column": "true"},
        {"type": "8", "is_column": "1", "column": "1"},
        {"type": "2", "is_column": "true", "column": "true"},
        {"type": "2", "is_column": "1", "column": "1"},
        {"type": "1", "is_column": "true", "column": "true"}
    ]
    
    # 测试所有组合
    for endpoint in api_endpoints:
        for params in param_combinations:
            print(f"\n{'-' * 80}")
            print(f"测试API: {endpoint}")
            print(f"参数: {params}")
            print(f"{'-' * 80}")
            
            result = test_publish(COOKIE, ARTICLE, endpoint, params)
            
            if result:
                print("\n✅ 测试成功！")
                break
        else:
            continue
        break

if __name__ == "__main__":
    main()
