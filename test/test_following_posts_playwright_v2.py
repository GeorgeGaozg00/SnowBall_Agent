#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试程序：使用 Playwright 获取雪球首页"关注"标签下的所有帖子
通过模拟浏览器操作，获取关注用户的所有帖子
"""

import json
import time
import random
from playwright.sync_api import sync_playwright

# 从配置文件读取Cookie
def load_cookie_from_config():
    """从后端配置文件读取Cookie"""
    try:
        with open('../backend/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('xueQiuCookie', '')
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return input("请输入雪球Cookie: ").strip()

def parse_cookie(cookie_str):
    """解析Cookie字符串为字典"""
    cookies = {}
    if cookie_str:
        for item in cookie_str.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key] = value
    return cookies

def get_following_posts_with_playwright():
    """
    使用 Playwright 获取关注页面的帖子
    """
    cookie_str = load_cookie_from_config()
    if not cookie_str:
        print("错误: 无法获取Cookie")
        return None
    
    print("=" * 60)
    print("使用 Playwright 获取关注页面帖子")
    print("=" * 60)
    
    all_posts = []
    
    with sync_playwright() as p:
        # 启动浏览器
        print("\n启动浏览器...")
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        
        # 设置Cookie
        print("设置Cookie...")
        cookies = parse_cookie(cookie_str)
        
        # 先访问雪球主页
        page = context.new_page()
        page.goto("https://xueqiu.com", wait_until="networkidle")
        
        # 设置Cookie
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
        
        # 访问关注页面
        print("\n访问关注页面...")
        page.goto("https://xueqiu.com", wait_until="networkidle")
        
        # 等待页面加载
        time.sleep(3)
        
        # 点击"关注"标签
        print("点击'关注'标签...")
        try:
            # 尝试多种选择器
            selectors = [
                'a[href="/"].active',  # 当前选中的首页
                '.nav__item:has-text("关注")',
                'a:has-text("关注")',
                '[data-type="follow"]',
                '.home__tab:has-text("关注")'
            ]
            
            for selector in selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).first.click()
                        print(f"✅ 使用选择器点击成功: {selector}")
                        break
                except:
                    continue
        except Exception as e:
            print(f"点击关注标签失败: {e}")
        
        # 等待内容加载
        time.sleep(3)
        
        # 监听网络请求，获取API数据
        print("\n监听API请求...")
        
        api_responses = []
        
        def handle_response(response):
            """处理响应"""
            url = response.url
            if 'timeline' in url or 'statuses' in url or 'friendships' in url:
                try:
                    if response.status == 200:
                        data = response.json()
                        api_responses.append({
                            'url': url,
                            'data': data
                        })
                        print(f"✅ 捕获API: {url[:80]}...")
                except:
                    pass
        
        page.on("response", handle_response)
        
        # 滚动页面加载更多帖子
        print("\n滚动页面加载帖子...")
        print("提示: 如果需要登录或验证，请在浏览器中完成操作")
        print("按 Enter 键继续滚动，输入 'q' 停止滚动并保存数据")
        
        scroll_count = 0
        max_scrolls = 50
        
        while scroll_count < max_scrolls:
            # 滚动页面
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(random.uniform(1.5, 3))
            scroll_count += 1
            
            # 每5次滚动显示一次状态
            if scroll_count % 5 == 0:
                print(f"已滚动 {scroll_count} 次，捕获 {len(api_responses)} 个API响应")
            
            # 检查用户输入（非阻塞）
            import sys
            import select
            
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                user_input = input().strip().lower()
                if user_input == 'q':
                    print("停止滚动")
                    break
        
        # 关闭浏览器
        browser.close()
    
    # 处理获取的数据
    print(f"\n{'='*60}")
    print(f"总共捕获 {len(api_responses)} 个API响应")
    print(f"{'='*60}")
    
    # 解析并合并所有帖子
    all_posts = parse_api_responses(api_responses)
    
    return all_posts

def parse_api_responses(api_responses):
    """
    解析API响应，提取帖子数据
    """
    all_posts = []
    seen_ids = set()
    
    for resp in api_responses:
        data = resp.get('data', {})
        
        # 尝试不同的字段名
        posts = None
        if 'list' in data:
            posts = data['list']
        elif 'statuses' in data:
            posts = data['statuses']
        elif isinstance(data, list):
            posts = data
        
        if posts:
            for post in posts:
                # 提取帖子数据
                if isinstance(post, dict):
                    # 有些API返回的是包装格式
                    if 'data' in post:
                        status = post['data']
                    else:
                        status = post
                    
                    # 获取帖子ID用于去重
                    post_id = status.get('id') or status.get('article_id')
                    
                    if post_id and post_id not in seen_ids:
                        seen_ids.add(post_id)
                        all_posts.append(status)
    
    print(f"✅ 解析得到 {len(all_posts)} 条唯一帖子")
    
    # 保存数据
    if all_posts:
        with open('following_posts_playwright.json', 'w', encoding='utf-8') as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存到 following_posts_playwright.json")
        
        # 显示前5条帖子
        print("\n前5条帖子预览:")
        print("-" * 60)
        for i, post in enumerate(all_posts[:5], 1):
            user = post.get('user', {})
            user_name = user.get('screen_name', '未知用户')
            title = post.get('title', '')
            description = post.get('description', '')[:100]
            
            print(f"\n{i}. 作者: {user_name}")
            print(f"   标题: {title}")
            print(f"   内容: {description}...")
    
    return all_posts

def analyze_posts(posts):
    """
    分析帖子数据
    """
    print("\n" + "=" * 60)
    print("帖子分析")
    print("=" * 60)
    
    # 统计作者
    author_stats = {}
    for post in posts:
        user = post.get('user', {})
        user_name = user.get('screen_name', '未知用户')
        user_id = user.get('id', '未知ID')
        
        if user_name not in author_stats:
            author_stats[user_name] = {
                'count': 0,
                'user_id': user_id
            }
        author_stats[user_name]['count'] += 1
    
    # 排序
    sorted_authors = sorted(author_stats.items(), key=lambda x: x[1]['count'], reverse=True)
    
    print(f"\n总共 {len(posts)} 条帖子，来自 {len(author_stats)} 个作者")
    print("\n作者统计（前20）:")
    for i, (author, stats) in enumerate(sorted_authors[:20], 1):
        print(f"{i:3d}. {author:20s} - {stats['count']:3d} 条帖子")
    
    # 保存分析结果
    with open('following_posts_analysis.json', 'w', encoding='utf-8') as f:
        json.dump({
            'total_posts': len(posts),
            'total_authors': len(author_stats),
            'author_stats': sorted_authors
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 分析结果已保存到 following_posts_analysis.json")

def main():
    """
    主函数
    """
    print("=" * 60)
    print("雪球关注页面帖子获取工具 (Playwright版)")
    print("=" * 60)
    
    print("\n请选择运行模式:")
    print("1. 使用 Playwright 获取帖子（推荐）")
    print("2. 分析已保存的帖子数据")
    
    choice = input("\n请输入选项（1/2）: ").strip()
    
    if choice == "1":
        posts = get_following_posts_with_playwright()
        if posts:
            analyze_posts(posts)
    
    elif choice == "2":
        try:
            with open('following_posts_playwright.json', 'r', encoding='utf-8') as f:
                posts = json.load(f)
            print(f"✅ 成功加载 {len(posts)} 条帖子")
            analyze_posts(posts)
        except FileNotFoundError:
            print("❌ 找不到已保存的数据文件")
    
    else:
        print("无效的选项")

if __name__ == "__main__":
    main()
