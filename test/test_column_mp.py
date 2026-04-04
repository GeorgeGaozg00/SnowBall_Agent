#!/usr/bin/env python3
"""
雪球专栏文章发布 - MP域名测试版
使用mp.xueqiu.com域名的API端点
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
    "title": "MP域名测试 - 专栏文章",
    "status": """<p>这是一篇使用MP域名API测试的专栏文章。</p>
<p>本文尝试通过mp.xueqiu.com域名的API发布为专栏文章。</p>
<p>专栏文章应该具有以下特点：</p>
<ol>
<li>显示在作者的专栏中</li>
<li>获得更多的曝光和推荐</li>
<li>有更高的权重</li>
</ol>
<p>通过使用mp域名的API，我们希望能够成功发布专栏文章。</p>
<p>感谢您的关注！</p>""",
    "cover_pic": "",
    "show_cover_pic": "true",
    "original": "false",
    "comment_disabled": "false"
}

def get_session_token(cookie, domain):
    """获取session_token"""
    session = requests.Session()
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": cookie.strip().replace("\n", ""),
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://{domain}/write",
        "Origin": f"https://{domain}",
        "Host": domain
    }
    
    try:
        # 尝试获取session_token
        token_url = f"https://{domain}/provider/session/token.json?api_path=%2Fstatuses%2Fupdate.json"
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

def test_mp_publish(cookie, article):
    """测试使用MP域名发布专栏文章"""
    # 测试不同的MP域名API端点
    mp_endpoints = [
        "https://mp.xueqiu.com/xq/statuses/update.json",
        "https://mp.xueqiu.com/statuses/update.json",
        "https://mp.xueqiu.com/notes/create.json"
    ]
    
    for endpoint in mp_endpoints:
        print(f"\n{'-' * 80}")
        print(f"测试MP API: {endpoint}")
        print(f"{'-' * 80}")
        
        # 提取域名
        domain = endpoint.split('/')[2]
        
        # 构造请求头
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie.strip().replace("\n", ""),
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"https://{domain}/write",
            "Origin": f"https://{domain}",
            "Host": domain
        }
        
        # 获取session_token
        session_token = get_session_token(cookie, domain)
        if not session_token:
            print("无法获取session_token")
            continue
        
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
            "draft_id": "0",
            "type": "8",
            "is_column": "true",
            "column": "true"
        }
        
        # 发送请求
        try:
            session = requests.Session()
            resp = session.post(endpoint, data=data, headers=headers)
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
    print("雪球专栏文章发布测试 - MP域名测试版")
    print("=" * 60)
    
    if not COOKIE:
        print("❌ 未找到cookie，请检查配置文件")
        return
    
    result = test_mp_publish(COOKIE, ARTICLE)
    
    if result:
        print("\n✅ MP域名测试成功！")
    else:
        print("\n❌ MP域名测试失败！")

if __name__ == "__main__":
    main()
