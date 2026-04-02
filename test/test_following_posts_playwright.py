#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试程序：使用Playwright获取雪球首页"关注"标签下的所有帖子
通过监听网络请求来找到正确的API端点
"""

import json
import time
from playwright.sync_api import sync_playwright

# 从环境变量或配置文件读取Cookie
XUEQIU_COOKIE = "acw_tc=2760820517451024281765153e7c9b0a9e0f0f3e2e3c5e3e3e3e3e3e3e3e3e3; xq_a_token=7e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3; xq_r_token=3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e; xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1aWQiOjU2Nzg1OTczMjYsImV4cCI6MTc3NTYwNjI4M30.abc123; u=5678597326; device_id=3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e; Hm_lvt_1db88642e346389874251b5a1eded6e3=1745102428; Hm_lpvt_1db88642e346389874251b5a1eded6e3=1745102428"

def parse_cookie_string(cookie_string):
    """解析cookie字符串为字典列表"""
    cookies = []
    for item in cookie_string.split(';'):
        item = item.strip()
        if '=' in item:
            name, value = item.split('=', 1)
            cookies.append({
                'name': name.strip(),
                'value': value.strip(),
                'domain': '.xueqiu.com',
                'path': '/'
            })
    return cookies

def capture_following_posts():
    """
    使用Playwright访问雪球首页，点击"关注"标签，并捕获帖子数据
    """
    print("=" * 60)
    print("使用Playwright获取关注页面帖子")
    print("=" * 60)
    
    captured_requests = []
    captured_posts = []
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False)  # 非无头模式，方便观察
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        
        # 创建新页面
        page = context.new_page()
        
        # 监听网络请求
        def handle_route(route, request):
            url = request.url
            if 'xueqiu.com' in url and ('timeline' in url or 'statuses' in url or 'friendships' in url or 'list' in url):
                print(f"\n📡 捕获到API请求:")
                print(f"   URL: {url}")
                print(f"   方法: {request.method}")
                
                captured_requests.append({
                    'url': url,
                    'method': request.method,
                    'headers': dict(request.headers)
                })
            
            route.continue_()
        
        page.route("**/*", handle_route)
        
        # 步骤1：访问雪球首页
        print("\n步骤1：访问雪球首页...")
        try:
            page.goto("https://xueqiu.com", wait_until="networkidle", timeout=30000)
            time.sleep(2)
        except Exception as e:
            print(f"❌ 访问首页失败: {str(e)}")
            print("请检查网络连接，然后重试...")
            browser.close()
            return
        
        # 步骤2：等待用户手动登录
        print("\n" + "=" * 60)
        print("步骤2：请手动登录")
        print("=" * 60)
        print("请在浏览器中完成以下操作：")
        print("1. 点击页面右上角的'登录'按钮")
        print("2. 使用手机扫码或其他方式登录")
        print("3. 登录成功后，确认页面显示您的用户名")
        print("4. 完成登录后，按回车键继续...")
        print("=" * 60)
        print("⚠️  注意：请不要关闭浏览器窗口！")
        print("=" * 60)
        
        try:
            input()
        except KeyboardInterrupt:
            print("\n用户中断程序")
            browser.close()
            return
        
        # 步骤3：确保在首页
        print("\n步骤3：导航到首页...")
        try:
            page.goto("https://xueqiu.com", wait_until="networkidle", timeout=30000)
            time.sleep(3)
        except Exception as e:
            print(f"❌ 导航到首页失败: {str(e)}")
            browser.close()
            return
        
        # 步骤4：点击"关注"标签
        print("\n步骤4：点击'关注'标签...")
        print("=" * 60)
        print("请在浏览器中完成以下操作：")
        print("1. 找到页面上的'关注'标签（通常在顶部导航栏）")
        print("2. 点击'关注'标签")
        print("3. 等待关注页面的帖子加载完成")
        print("4. 可以滚动页面加载更多帖子")
        print("5. 完成后按回车键继续...")
        print("=" * 60)
        print("⚠️  注意：请不要关闭浏览器窗口！")
        print("=" * 60)
        
        try:
            input()
        except KeyboardInterrupt:
            print("\n用户中断程序")
            browser.close()
            return
        
        # 步骤5：提取页面上的帖子
        print("\n步骤5：提取页面上的帖子...")
        
        # 尝试多种选择器来找到帖子
        post_selectors = [
            '.status-item',  # 帖子项
            '.timeline-item',  # 时间线项
            '[data-type="status"]',  # 状态数据
            '.article-item',  # 文章项
            '.card',  # 卡片
        ]
        
        for selector in post_selectors:
            try:
                posts = page.locator(selector).all()
                if posts:
                    print(f"   ✅ 使用选择器 '{selector}' 找到 {len(posts)} 个帖子")
                    
                    for i, post in enumerate(posts[:5], 1):
                        try:
                            # 尝试提取帖子信息
                            user_name = post.locator('.user-name, .author-name, .name').first.inner_text()
                            content = post.locator('.content, .text, .description').first.inner_text()
                            
                            print(f"\n   帖子 {i}:")
                            print(f"     作者: {user_name[:30]}")
                            print(f"     内容: {content[:100]}...")
                            
                            captured_posts.append({
                                'user_name': user_name,
                                'content': content[:200]
                            })
                        except:
                            pass
                    
                    break
            except Exception as e:
                print(f"   ❌ 选择器 {selector} 失败: {str(e)}")
                continue
        
        # 保存页面HTML以便分析
        html_content = page.content()
        with open("xueqiu_following_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("\n✅ 已保存页面HTML到 xueqiu_following_page.html")
        
        # 保存捕获的请求
        with open("captured_following_requests.json", "w", encoding="utf-8") as f:
            json.dump(captured_requests, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存 {len(captured_requests)} 个捕获的请求到 captured_following_requests.json")
        
        # 保存提取的帖子
        with open("captured_following_posts.json", "w", encoding="utf-8") as f:
            json.dump(captured_posts, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存 {len(captured_posts)} 个提取的帖子到 captured_following_posts.json")
        
        # 关闭浏览器
        browser.close()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    capture_following_posts()
