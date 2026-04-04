#!/usr/bin/env python3
"""
雪球专栏文章发布 - 简化版抓包工具
使用更通用的选择器和更详细的调试信息
"""

import asyncio
from playwright.async_api import async_playwright
import json
import os

async def capture_column_requests():
    """捕获发布专栏文章的真实请求"""
    
    # 读取配置文件
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    cookie_str = config.get('xueQiuCookie', '')
    
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
        
        # 存储所有请求
        all_requests = []
        
        # 监听网络请求
        async def handle_request(request):
            # 只记录POST请求和关键API请求
            if (request.method == 'POST' and 
                ('update' in request.url or 'create' in request.url or 'notes' in request.url)):
                
                request_info = {
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'post_data': request.post_data
                }
                
                all_requests.append(request_info)
                
                print(f"\n[捕获到请求]")
                print(f"URL: {request.url}")
                print(f"方法: {request.method}")
                print(f"POST数据: {request.post_data[:300]}...")
                print(f"Referer: {request.headers.get('Referer', 'N/A')}")
        
        page.on('request', handle_request)
        
        # 监听响应
        async def handle_response(response):
            if (response.request.method == 'POST' and 
                ('update' in response.request.url or 'create' in response.request.url or 'notes' in response.request.url)):
                
                print(f"\n[响应信息]")
                print(f"状态码: {response.status}")
                try:
                    body = await response.text()
                    print(f"响应内容: {body[:300]}...")
                except:
                    print("无法获取响应内容")
        
        page.on('response', handle_response)
        
        # 访问发布页面
        print("访问雪球发布页面...")
        await page.goto('https://xueqiu.com/write')
        await page.wait_for_load_state('networkidle')
        
        # 等待页面加载完成
        print("等待页面加载完成...")
        await asyncio.sleep(5)
        
        # 打印当前页面URL
        print(f"当前页面URL: {page.url}")
        
        # 打印页面内容，查看页面结构
        print("\n页面标题:")
        title = await page.title()
        print(title)
        
        # 检查是否需要登录
        if "登录" in title or "login" in page.url:
            print("\n❌ 需要登录，请在浏览器中手动登录")
            print("登录完成后，按回车键继续...")
            input()
            await page.wait_for_load_state('networkidle')
        
        print("\n" + "="*80)
        print("请在浏览器中手动完成以下操作:")
        print("1. 输入文章标题")
        print("2. 输入文章内容")
        print("3. 勾选'收录到我的专栏'选项")
        print("4. 点击发布按钮")
        print("="*80)
        print("\n操作完成后，按回车键继续...")
        
        # 等待用户操作
        input()
        
        # 保存捕获的请求数据
        if all_requests:
            output_file = os.path.join(os.path.dirname(__file__), 'column_requests.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_requests, f, indent=2, ensure_ascii=False)
            print(f"\n请求数据已保存到: {output_file}")
            print(f"共捕获到 {len(all_requests)} 个请求")
            
            # 分析请求数据
            print("\n" + "="*80)
            print("请求分析结果:")
            print("="*80)
            
            for i, req in enumerate(all_requests):
                print(f"\n请求 {i+1}:")
                print(f"URL: {req['url']}")
                print(f"POST数据: {req['post_data']}")
                print(f"Referer: {req['headers'].get('Referer', 'N/A')}")
                print(f"User-Agent: {req['headers'].get('User-Agent', 'N/A')}")
        else:
            print("\n未捕获到任何请求")
        
        # 关闭浏览器
        await browser.close()

if __name__ == '__main__':
    asyncio.run(capture_column_requests())
