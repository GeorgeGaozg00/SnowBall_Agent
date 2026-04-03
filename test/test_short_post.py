#!/usr/bin/env python3
# 测试雪球短文发布API

import requests
import json
import os
import time

# 从配置文件读取cookie
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', 'config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
    COOKIE = config.get('xueQiuCookie', '')

def get_session_token(cookie):
    """获取会话token"""
    headers = {
        "Cookie": cookie.strip(),
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # 尝试多个token获取URL
    token_urls = [
        "https://xueqiu.com/provider/session/token.json?api_path=%2Fstatuses%2Fupdate.json",
        "https://xueqiu.com/provider/session/token.json",
        "https://mp.xueqiu.com/xq/provider/session/token.json?api_path=%2Fstatuses%2Fupdate.json",
        "https://mp.xueqiu.com/xq/provider/session/token.json"
    ]
    
    for token_url in token_urls:
        try:
            print(f"尝试获取session_token: {token_url}")
            token_response = requests.get(token_url, headers=headers)
            print(f"响应状态码: {token_response.status_code}")
            
            if token_response.status_code == 200:
                token_data = token_response.json()
                if "session_token" in token_data:
                    session_token = token_data["session_token"]
                    print(f"获取 session_token 成功：{session_token[:16]}...")
                    return session_token
                else:
                    print(f"响应中没有session_token: {token_data}")
            else:
                print(f"获取token失败，状态码: {token_response.status_code}")
        except Exception as e:
            print(f"获取token时出错: {str(e)}")
    
    return None

def publish_short_post(cookie, content):
    """发布短文到雪球"""
    # 创建会话
    session = requests.Session()
    
    headers = {
        "Cookie": cookie.strip(),
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    
    # 1. 先访问首页建立会话
    print("访问雪球首页建立会话...")
    try:
        home_response = session.get("https://xueqiu.com/", headers=headers)
        print(f"首页访问状态码: {home_response.status_code}")
    except Exception as e:
        print(f"访问首页失败: {str(e)}")
        return None
    
    # 2. 获取session_token
    session_token = get_session_token(cookie)
    if not session_token:
        print("无法获取session_token")
        return None
    
    # 3. 尝试多个API路径
    post_urls = [
        "https://xueqiu.com/statuses/update.json",
        "https://api.xueqiu.com/statuses/update.json",
        "https://xueqiu.com/notes/create",
        "https://xueqiu.com/notes/create.json"
    ]
    
    for post_url in post_urls:
        print(f"\n尝试发文接口: {post_url}")
        
        # 构造请求数据
        data = {
            "status": content,
            "device": "Web",
            "right": "0",
            "session_token": session_token
        }
        
        # 4. 发送请求
        try:
            resp = session.post(post_url, data=data, headers=headers)
            print(f"响应状态码: {resp.status_code}")
            print(f"响应内容: {resp.json()}")
            
            if resp.status_code == 200:
                result = resp.json()
                if "id" in result:
                    return result
        except Exception as e:
            print(f"请求异常：{e}")
            if resp.text:
                print(f"返回内容：{resp.text[:200]}")
    
    return None

if __name__ == "__main__":
    print("测试雪球短文发布API")
    print("=" * 60)
    
    if not COOKIE:
        print("错误: 缺少Cookie")
    else:
        print(f"Cookie: {COOKIE[:50]}...")
        print()
        
        # 测试内容
        test_content = "这是一条API发的短帖，测试短文发布功能"
        print(f"测试内容: {test_content}")
        print()
        
        # 调用发布函数
        result = publish_short_post(COOKIE, test_content)
        
        # 分析结果
        if result and "id" in result:
            print("\n✅ 短文发布成功！")
            print(f"文章ID: {result['id']}")
            if "user_id" in result:
                print(f"文章链接: https://xueqiu.com/{result['user_id']}/{result['id']}")
        else:
            print("\n❌ 短文发布失败")
