#!/usr/bin/env python3
"""
雪球专栏文章发布 - 抓包分析版
使用浏览器自动化捕获真实的专栏文章发布请求
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
        await page.wait_for_selector('input[placeholder="请输入标题"]', timeout=30000)
        
        # 输入标题
        print("输入文章标题...")
        await page.fill('input[placeholder="请输入标题"]', '抓包测试 - 专栏文章')
        
        # 等待编辑器加载
        print("等待编辑器加载...")
        await page.wait_for_selector('div.ql-editor', timeout=30000)
        
        # 输入文章内容
        print("输入文章内容...")
        content = """
<p>这是一篇用于抓包测试的专栏文章。</p>
<p>本文用于捕获发布专栏文章时的真实API请求参数。</p>
<p>通过分析真实的请求，我们可以找出发布专栏文章的正确方法。</p>
<p>文章内容需要足够长，并且包含HTML标签，以满足专栏文章的要求。</p>
<p>专栏文章的发布流程可能与普通文章不同，需要特殊的参数和API端点。</p>
<p>通过抓包分析，我们可以了解：</p>
<ol>
<li>正确的API端点</li>
<li>必要的请求参数</li>
<li>正确的请求头设置</li>
<li>认证机制</li>
</ol>
<p>感谢您的参与！</p>
"""
        
        # 填充编辑器内容
        await page.evaluate('''
            (content) => {
                const editor = document.querySelector('.ql-editor');
                editor.innerHTML = content;
            }
        ''', content)
        
        # 等待内容填充完成
        await asyncio.sleep(2)
        
        # 勾选"收录到我的专栏"选项
        print("勾选'收录到我的专栏'选项...")
        try:
            column_checkbox = await page.query_selector('input[name="column"]')
            if column_checkbox:
                await column_checkbox.check()
                print("成功勾选'收录到我的专栏'选项")
            else:
                print("未找到'收录到我的专栏'选项")
        except Exception as e:
            print(f"勾选专栏选项失败: {e}")
        
        # 等待勾选完成
        await asyncio.sleep(1)
        
        print("\n" + "="*80)
        print("请手动点击发布按钮，完成发布操作")
        print("发布完成后，按回车键继续...")
        print("="*80)
        
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
