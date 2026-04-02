#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过用户UID获取最近10个帖子（Playwright版）
"""

import json
import time
import random
from playwright.sync_api import sync_playwright

CONFIG_FILE = '../backend/config.json'

def load_config():
    """加载配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置失败: {e}")
        return None

def parse_cookie(cookie_str):
    """解析Cookie字符串为字典"""
    cookies = {}
    if cookie_str:
        for item in cookie_str.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key] = value
    return cookies

def get_user_posts(user_uid, cookie_str, max_posts=10):
    """
    通过Playwright获取用户最近的帖子
    """
    print(f"\n" + "=" * 60)
    print(f"获取用户 {user_uid} 的最近 {max_posts} 个帖子")
    print("=" * 60)
    
    api_responses = []
    
    with sync_playwright() as p:
        print("\n启动浏览器...")
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        # 设置Cookie
        print("设置Cookie...")
        page.goto("https://xueqiu.com", wait_until="networkidle")
        
        cookies = parse_cookie(cookie_str)
        for name, value in cookies.items():
            try:
                context.add_cookies([{
                    'name': name,
                    'value': value,
                    'domain': '.xueqiu.com',
                    'path': '/'
                }])
            except Exception as e:
                print(f"设置Cookie {name} 失败: {e}")
        
        # 监听网络请求
        print("\n开始监听API请求...")
        
        def handle_response(response):
            """处理响应，捕获包含帖子的API"""
            url = response.url
            if any(keyword in url for keyword in ['timeline', 'statuses', 'user_timeline']):
                try:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'json' in content_type:
                            data = response.json()
                            api_responses.append({
                                'url': url,
                                'data': data,
                                'time': time.strftime('%H:%M:%S')
                            })
                            print(f"✅ 捕获API [{len(api_responses)}]: {url.split('?')[0][:60]}...")
                except Exception as e:
                    print(f"处理响应失败: {e}")
        
        page.on("response", handle_response)
        
        # 访问用户主页
        user_url = f"https://xueqiu.com/{user_uid}"
        print(f"\n访问用户主页: {user_url}")
        page.goto(user_url, wait_until="networkidle")
        time.sleep(3)
        
        # 检查登录状态
        print("\n检查登录状态...")
        page_content = page.content()
        if "登录" in page_content and "login" in page_content.lower():
            print("⚠️  可能需要登录，请在浏览器中完成登录操作")
            print("等待10秒...")
            time.sleep(10)
        else:
            print("✅ 已登录状态")
        
        # 自动滚动页面加载更多帖子
        print(f"\n自动滚动页面加载帖子...")
        for i in range(5):
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(random.uniform(2, 3))
            print(f"  已滚动 {i+1}/5 次")
        
        print("\n✅ 滚动完成")
        browser.close()
    
    # 解析数据
    all_posts = []
    seen_ids = set()
    
    print(f"\n{'='*60}")
    print("解析API数据...")
    print(f"{'='*60}")
    
    for resp in api_responses:
        data = resp.get('data', {})
        url = resp.get('url', '')
        
        # 尝试不同的数据结构
        statuses = None
        if isinstance(data, dict):
            if 'statuses' in data:
                statuses = data['statuses']
            elif 'list' in data:
                statuses = data['list']
            elif 'data' in data and isinstance(data['data'], list):
                statuses = data['data']
        elif isinstance(data, list):
            statuses = data
        
        if statuses and isinstance(statuses, list):
            print(f"  从 {url[:50]}... 解析到 {len(statuses)} 条数据")
            
            for status in statuses:
                if isinstance(status, dict):
                    # 有些API返回的是包装格式
                    if 'data' in status and isinstance(status['data'], dict):
                        post = status['data']
                    else:
                        post = status
                    
                    # 获取帖子ID用于去重
                    post_id = post.get('id') or post.get('article_id') or post.get('status_id')
                    
                    if not post_id or post_id in seen_ids:
                        continue
                    
                    # 提取关键字段
                    post_data = {
                        'id': post_id,
                        'title': post.get('title', ''),
                        'description': post.get('description', ''),
                        'text': post.get('text', ''),
                        'created_at': post.get('created_at'),
                        'view_count': post.get('view_count', 0),
                        'reply_count': post.get('reply_count', 0),
                        'like_count': post.get('like_count', 0),
                        'source': post.get('source', '')
                    }
                    
                    # 只添加有内容的帖子
                    if post_data['title'] or post_data['description'] or post_data['text']:
                        seen_ids.add(post_id)
                        all_posts.append(post_data)
    
    # 按时间排序（最新的在前）
    all_posts.sort(key=lambda x: x.get('created_at', 0), reverse=True)
    
    # 截取前max_posts个
    all_posts = all_posts[:max_posts]
    
    print(f"\n✅ 成功获取 {len(all_posts)} 个帖子")
    
    # 保存数据
    if all_posts:
        output_file = f'user_{user_uid}_posts.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存到 {output_file}")
        
        # 显示帖子
        print("\n帖子列表:")
        print("=" * 60)
        for i, post in enumerate(all_posts, 1):
            print(f"\n{i}. ID: {post['id']}")
            if post['title']:
                print(f"   标题: {post['title'][:60]}")
            content = post['description'] or post['text'] or ''
            print(f"   内容: {content[:80]}...")
            if post['created_at']:
                try:
                    print(f"   时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(post['created_at']/1000))}")
                except:
                    pass
            print(f"   浏览: {post['view_count']} | 回复: {post['reply_count']} | 点赞: {post['like_count']}")
    
    return all_posts

def main():
    """主函数"""
    print("=" * 60)
    print("通过UID获取用户最近帖子（Playwright版）")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    if not config:
        print("错误: 无法加载配置")
        return
    
    cookie_str = config.get('xueQiuCookie')
    if not cookie_str:
        print("错误: 缺少Cookie")
        return
    
    # 输入用户UID
    user_uid = input("请输入用户UID: ").strip()
    if not user_uid:
        print("错误: 请输入有效的用户UID")
        return
    
    # 输入要获取的帖子数量
    max_posts = input("请输入要获取的帖子数量（默认10）: ").strip()
    max_posts = int(max_posts) if max_posts.isdigit() else 10
    max_posts = min(max_posts, 50)  # 最多50个
    
    # 获取帖子
    get_user_posts(user_uid, cookie_str, max_posts)

if __name__ == "__main__":
    main()
