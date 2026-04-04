#!/usr/bin/env python3
"""
雪球专栏文章发布 - 浏览器自动化版
通过模拟真实用户操作来发布专栏文章
"""

import asyncio
from playwright.async_api import async_playwright
import json
import os

async def publish_column_article():
    """使用浏览器自动化发布专栏文章"""
    
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
        
        # 访问发布页面
        print("访问雪球发布页面...")
        await page.goto('https://xueqiu.com/write')
        await page.wait_for_load_state('networkidle')
        
        # 等待页面加载完成
        print("等待页面加载完成...")
        await page.wait_for_selector('input[placeholder="请输入标题"]')
        
        # 输入标题
        print("输入文章标题...")
        await page.fill('input[placeholder="请输入标题"]', '浏览器自动化测试 - 专栏文章')
        
        # 等待编辑器加载
        print("等待编辑器加载...")
        await page.wait_for_selector('div.ql-editor')
        
        # 输入文章内容
        print("输入文章内容...")
        content = """
<p>这是一篇通过浏览器自动化发布的专栏文章。</p>
<p>本文测试以下功能：</p>
<ol>
<li>浏览器自动化发布专栏文章</li>
<li>自动勾选"收录到我的专栏"选项</li>
<li>确保文章成功发布为专栏文章</li>
</ol>
<p>专栏文章需要满足以下条件：</p>
<ul>
<li>必须有标题</li>
<li>内容必须有HTML标签</li>
<li>内容长度至少100字</li>
<li>必须勾选"收录到我的专栏"选项</li>
</ul>
<p>通过浏览器自动化，我们可以完全模拟真实用户的操作流程，确保文章能够成功发布为专栏文章。</p>
<p>感谢您的关注！</p>
"""
        
        # 填充编辑器内容
        await page.evaluate('''
            (content) => {
                const editor = document.querySelector('.ql-editor');
                editor.innerHTML = content;
            }
        ''', content)
        
        # 确保内容已经填充
        await asyncio.sleep(2)
        
        # 勾选"收录到我的专栏"选项
        print("勾选'收录到我的专栏'选项...")
        await page.check('input[name="column"]')
        
        # 等待一段时间，确保勾选成功
        await asyncio.sleep(1)
        
        # 点击发布按钮
        print("点击发布按钮...")
        await page.click('button:has-text("发布")')
        
        # 等待发布完成
        print("等待发布完成...")
        try:
            # 等待发布成功提示
            await page.wait_for_selector('.toast-success', timeout=30000)
            print("✅ 发布成功！")
            
            # 等待页面跳转
            await page.wait_for_load_state('networkidle')
            
            # 获取当前URL
            current_url = page.url
            print(f"发布后页面URL: {current_url}")
            
        except Exception as e:
            print(f"❌ 发布失败: {e}")
        
        # 关闭浏览器
        await browser.close()

if __name__ == '__main__':
    asyncio.run(publish_column_article())
