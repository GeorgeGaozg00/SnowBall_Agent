#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试程序：使用 Playwright 自动获取雪球首页"关注"标签下的所有帖子
自动滚动加载，无需人工干预
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

def get_following_posts_auto(max_scrolls=30):
    """
    自动获取关注页面的帖子
    """
    cookie_str = load_cookie_from_config()
    if not cookie_str:
        print("错误: 无法获取Cookie，请检查 backend/config.json 文件")
        return None
    
    print("=" * 60)
    print("自动获取关注页面帖子")
    print("=" * 60)
    
    api_responses = []
    
    with sync_playwright() as p:
        print("\n启动浏览器...")
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        
        page = context.new_page()
        
        # 先访问雪球主页设置Cookie
        print("设置Cookie...")
        page.goto("https://xueqiu.com", wait_until="networkidle")
        
        # 设置Cookie
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
        
        # 刷新页面使Cookie生效
        page.reload(wait_until="networkidle")
        time.sleep(2)
        
        # 监听网络请求
        print("\n开始监听API请求...")
        
        def handle_response(response):
            """处理响应，捕获包含帖子的API"""
            url = response.url
            if any(keyword in url for keyword in ['timeline', 'statuses', 'friendships', 'dynamics']):
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
                except:
                    pass
        
        page.on("response", handle_response)
        
        # 访问首页
        print("\n访问首页...")
        page.goto("https://xueqiu.com", wait_until="networkidle")
        time.sleep(3)
        
        # 检查是否需要登录
        print("\n检查登录状态...")
        page_content = page.content()
        if "登录" in page_content and "login" in page_content.lower():
            print("⚠️  可能需要登录，请在浏览器中完成登录操作")
            print("等待10秒...")
            time.sleep(10)
        else:
            print("✅ 已登录状态")
        
        # 尝试点击"关注"标签
        print("\n尝试点击'关注'标签...")
        try:
            # 寻找关注标签
            selectors = [
                'a[href="/"]:has-text("关注")',
                '.nav a:has-text("关注")',
                '[class*="tab"]:has-text("关注")',
                'a:has-text("关注"):not(:has-text("关注精选"))'
            ]
            
            clicked = False
            for selector in selectors:
                try:
                    elements = page.locator(selector).all()
                    for elem in elements:
                        text = elem.text_content()
                        if text and "关注" in text and len(text) < 5:
                            elem.click()
                            print(f"✅ 点击关注标签: {text}")
                            clicked = True
                            break
                    if clicked:
                        break
                except:
                    continue
            
            if not clicked:
                print("⚠️  未找到关注标签，可能已经在关注页面")
        except Exception as e:
            print(f"点击关注标签失败: {e}")
        
        # 等待内容加载
        time.sleep(3)
        
        # 自动滚动页面
        print(f"\n开始自动滚动页面（最多{max_scrolls}次）...")
        print("-" * 60)
        
        for scroll_count in range(1, max_scrolls + 1):
            # 滚动页面
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(random.uniform(2, 4))
            
            # 显示进度
            if scroll_count % 5 == 0:
                print(f"已滚动 {scroll_count}/{max_scrolls} 次，捕获 {len(api_responses)} 个API")
        
        print("-" * 60)
        print(f"✅ 滚动完成，总共捕获 {len(api_responses)} 个API响应")
        
        # 关闭浏览器
        browser.close()
    
    # 解析数据
    all_posts = parse_api_responses(api_responses)
    return all_posts

def parse_api_responses(api_responses):
    """
    解析API响应，提取帖子数据
    """
    print(f"\n{'='*60}")
    print("解析API数据...")
    print(f"{'='*60}")
    
    all_posts = []
    seen_ids = set()
    
    for resp in api_responses:
        data = resp.get('data', {})
        url = resp.get('url', '')
        
        # 尝试不同的字段名
        posts = None
        if isinstance(data, dict):
            if 'list' in data:
                posts = data['list']
            elif 'statuses' in data:
                posts = data['statuses']
            elif 'data' in data and isinstance(data['data'], list):
                posts = data['data']
        elif isinstance(data, list):
            posts = data
        
        if posts and isinstance(posts, list):
            print(f"  从 {url[:50]}... 解析到 {len(posts)} 条数据")
            
            for post in posts:
                if isinstance(post, dict):
                    # 有些API返回的是包装格式
                    if 'data' in post and isinstance(post['data'], dict):
                        status = post['data']
                    else:
                        status = post
                    
                    # 获取帖子ID用于去重
                    post_id = status.get('id') or status.get('article_id') or status.get('status_id')
                    
                    if post_id and post_id not in seen_ids:
                        seen_ids.add(post_id)
                        all_posts.append(status)
    
    print(f"\n✅ 去重后得到 {len(all_posts)} 条唯一帖子")
    
    # 保存数据
    if all_posts:
        output_file = 'following_posts_auto.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存到 {output_file}")
        
        # 显示前10条帖子
        print("\n前10条帖子预览:")
        print("=" * 60)
        for i, post in enumerate(all_posts[:10], 1):
            user = post.get('user', {})
            user_name = user.get('screen_name', '未知用户')
            title = post.get('title', '')
            description = post.get('description', '')[:80]
            
            print(f"\n{i}. 作者: {user_name}")
            if title:
                print(f"   标题: {title}")
            print(f"   内容: {description}...")
    
    return all_posts

def analyze_posts(posts):
    """
    分析帖子数据
    """
    print("\n" + "=" * 60)
    print("帖子统计分析")
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
    
    print(f"\n📊 统计结果:")
    print(f"   总帖子数: {len(posts)}")
    print(f"   作者数量: {len(author_stats)}")
    
    print(f"\n📈 作者发帖排行（前20）:")
    for i, (author, stats) in enumerate(sorted_authors[:20], 1):
        print(f"   {i:2d}. {author:20s} - {stats['count']:3d} 条帖子")
    
    # 保存分析结果
    analysis_file = 'following_posts_analysis.json'
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_posts': len(posts),
            'total_authors': len(author_stats),
            'author_stats': sorted_authors
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 分析结果已保存到 {analysis_file}")

def main():
    """
    主函数 - 自动运行，无需交互
    """
    print("=" * 60)
    print("雪球关注页面帖子自动获取工具")
    print("=" * 60)
    print("\n程序将自动:")
    print("  1. 读取配置文件中的Cookie")
    print("  2. 启动浏览器并访问雪球")
    print("  3. 自动滚动加载关注页面的帖子")
    print("  4. 保存所有帖子数据")
    print("\n" + "=" * 60)
    
    # 自动获取帖子
    posts = get_following_posts_auto(max_scrolls=30)
    
    if posts:
        analyze_posts(posts)
        print("\n" + "=" * 60)
        print("✅ 完成！数据已保存到:")
        print("   - following_posts_auto.json (帖子数据)")
        print("   - following_posts_analysis.json (统计分析)")
        print("=" * 60)
    else:
        print("\n❌ 获取失败，请检查Cookie和网络连接")

if __name__ == "__main__":
    main()
