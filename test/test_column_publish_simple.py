#!/usr/bin/env python3
"""
雪球专栏文章发布研究 - 简化版
直接在浏览器中操作，捕获所有网络请求
"""

import asyncio
from playwright.async_api import async_playwright
import json
import os

async def capture_column_publish():
    """捕获发布专栏文章的API请求"""
    
    # 读取配置文件
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    cookie_str = config.get('xueqiu_cookie', '')
    
    # 解析cookie
    cookies = []
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies.append({
                'name': key.strip(),
                'value': value.strip(),
                'domain': '.xueqiu.com',
                'path': '/'
            })
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        # 设置cookie
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        # 监听所有网络请求
        all_requests = []
        
        async def handle_request(request):
            # 只记录POST请求和关键GET请求
            if request.method == 'POST' or 'update' in request.url or 'create' in request.url or 'column' in request.url:
                request_info = {
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers)
                }
                
                if request.method == 'POST':
                    post_data = request.post_data
                    if post_data:
                        request_info['post_data'] = post_data
                
                all_requests.append(request_info)
                print(f"\n捕获到请求: {request.method} {request.url}")
                if request.method == 'POST' and post_data:
                    print(f"POST数据: {post_data[:200]}...")
        
        page.on('request', handle_request)
        
        # 监听响应
        async def handle_response(response):
            if response.request.method == 'POST' and ('update' in response.url or 'create' in response.url):
                try:
                    body = await response.text()
                    print(f"\n响应状态码: {response.status}")
                    print(f"响应内容: {body[:300]}...")
                except:
                    pass
        
        page.on('response', handle_response)
        
        # 访问发布页面
        print("访问雪球发布页面...")
        await page.goto('https://xueqiu.com/write')
        await page.wait_for_load_state('networkidle')
        
        print("\n" + "="*60)
        print("请在浏览器中操作：")
        print("1. 输入文章标题")
        print("2. 输入文章内容（确保内容足够长，有HTML格式）")
        print("3. 勾选'收录到我的原创专栏'选项")
        print("4. 点击发布按钮")
        print("="*60)
        print("\n操作完成后，按回车键继续...")
        
        # 等待用户操作
        input()
        
        # 保存捕获的请求数据
        if all_requests:
            output_file = os.path.join(os.path.dirname(__file__), 'column_publish_request.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_requests, f, indent=2, ensure_ascii=False)
            print(f"\n请求数据已保存到: {output_file}")
            print(f"共捕获到 {len(all_requests)} 个请求")
        else:
            print("\n未捕获到任何请求")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(capture_column_publish())
