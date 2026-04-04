#!/usr/bin/env python3
"""
雪球专栏文章发布研究
通过浏览器自动化捕获发布专栏文章时的API请求
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
        
        # 监听网络请求
        requests_data = []
        
        async def handle_request(request):
            if 'statuses/update' in request.url or 'notes/create' in request.url:
                print(f"\n捕获到发布请求: {request.url}")
                print(f"方法: {request.method}")
                print(f"Headers: {json.dumps(dict(request.headers), indent=2, ensure_ascii=False)}")
                
                if request.method == 'POST':
                    post_data = request.post_data
                    if post_data:
                        print(f"POST数据: {post_data}")
                        requests_data.append({
                            'url': request.url,
                            'method': request.method,
                            'headers': dict(request.headers),
                            'post_data': post_data
                        })
        
        page.on('request', handle_request)
        
        # 访问发布页面
        print("访问雪球发布页面...")
        await page.goto('https://mp.xueqiu.com/write/')
        await page.wait_for_load_state('networkidle')
        
        print("\n请在浏览器中操作：")
        print("1. 输入文章标题")
        print("2. 输入文章内容")
        print("3. 勾选'收录到我的原创专栏'")
        print("4. 点击发布按钮")
        print("\n操作完成后，按回车键继续...")
        
        # 等待用户操作
        input()
        
        # 保存捕获的请求数据
        if requests_data:
            output_file = os.path.join(os.path.dirname(__file__), 'column_publish_request.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(requests_data, f, indent=2, ensure_ascii=False)
            print(f"\n请求数据已保存到: {output_file}")
        else:
            print("\n未捕获到发布请求")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(capture_column_publish())
