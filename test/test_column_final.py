#!/usr/bin/env python3
"""
雪球专栏文章发布 - 最终测试版
添加原创声明和文章类型参数
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
    "title": "最终测试 - 专栏文章",
    "status": """<p>这是一篇最终测试的专栏文章。</p>
<p>本文尝试通过API发布为专栏文章，包含原创声明和文章类型。</p>
<p>专栏文章需要满足以下条件：</p>
<ol>
<li>必须有标题</li>
<li>内容必须有HTML标签</li>
<li>内容长度至少100字</li>
<li>必须声明原创</li>
<li>必须选择文章类型</li>
</ol>
<p>通过添加这些必要的参数，我们希望能够成功发布专栏文章。</p>
<p>感谢您的关注！</p>""",
    "cover_pic": "",
    "show_cover_pic": "true",
    "original": "true",  # 必须声明原创
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

def test_publish(cookie, article):
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
        "original": article["original"],  # 声明原创
        "comment_disabled": article["comment_disabled"],
        "session_token": session_token,
        "device": "Web",
        "right": "0",
        "draft_id": "0",
        "type": "8",  # 专栏文章类型
        "is_column": "true",
        "column": "true",
        "article_type": "1"  # 1: 个人文章
    }
    
    # 发送请求
    try:
        resp = session.post("https://xueqiu.com/statuses/update.json", data=data, headers=headers)
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
    print("雪球专栏文章发布测试 - 最终测试版")
    print("=" * 60)
    
    if not COOKIE:
        print("❌ 未找到cookie，请检查配置文件")
        return
    
    print(f"文章标题: {ARTICLE['title']}")
    print(f"是否原创: {ARTICLE['original']}")
    print()
    
    result = test_publish(COOKIE, ARTICLE)
    
    if result:
        print("\n✅ 专栏文章发布成功！")
    else:
        print("\n❌ 专栏文章发布失败！")

if __name__ == "__main__":
    main()
