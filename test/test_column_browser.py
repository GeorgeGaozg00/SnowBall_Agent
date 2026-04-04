#!/usr/bin/env python3
"""
雪球专栏文章发布 - 浏览器自动化完整版
模拟完整的专栏文章发布流程
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
        
        # 访问专栏管理页面
        print("访问雪球专栏管理页面...")
        await page.goto('https://xueqiu.com/columns/manage')
        await page.wait_for_load_state('networkidle')
        
        # 等待页面加载完成
        print("等待页面加载完成...")
        await asyncio.sleep(3)
        
        # 检查是否需要登录
        title = await page.title()
        if "登录" in title or "login" in page.url:
            print("\n❌ 需要登录，请在浏览器中手动登录")
            print("登录完成后，按回车键继续...")
            input()
            await page.wait_for_load_state('networkidle')
        
        # 查找"写专栏"按钮
        print("查找'写专栏'按钮...")
        try:
            # 尝试不同的选择器
            write_buttons = [
                'button:has-text("写专栏")',
                'a:has-text("写专栏")',
                'button:has-text("发布专栏")',
                'a:has-text("发布专栏")'
            ]
            
            for selector in write_buttons:
                if await page.query_selector(selector):
                    print(f"找到'写专栏'按钮: {selector}")
                    await page.click(selector)
                    break
            else:
                print("未找到'写专栏'按钮，尝试直接访问写长文页面")
                await page.goto('https://xueqiu.com/write')
                await page.wait_for_load_state('networkidle')
        except Exception as e:
            print(f"查找'写专栏'按钮失败: {e}")
            await page.goto('https://xueqiu.com/write')
            await page.wait_for_load_state('networkidle')
        
        # 等待页面加载完成
        print("等待写文章页面加载完成...")
        await asyncio.sleep(3)
        
        # 输入标题
        print("输入文章标题...")
        try:
            await page.fill('input[placeholder="请输入标题"]', '浏览器自动化测试 - 专栏文章')
        except Exception as e:
            print(f"输入标题失败: {e}")
        
        # 等待编辑器加载
        print("等待编辑器加载...")
        await asyncio.sleep(2)
        
        # 输入文章内容
        print("输入文章内容...")
        content = """
这是一篇通过浏览器自动化发布的专栏文章。
本文测试以下功能：
1. 浏览器自动化发布专栏文章
2. 自动勾选"收录到我的专栏"选项
3. 确保文章成功发布为专栏文章

专栏文章需要满足以下条件：
- 必须有标题
- 内容必须有HTML标签
- 内容长度至少100字
- 必须勾选"收录到我的专栏"选项

通过浏览器自动化，我们可以完全模拟真实用户的操作流程，确保文章能够成功发布为专栏文章。
感谢您的关注！
"""
        
        # 填充编辑器内容
        try:
            editor = await page.query_selector('.ql-editor')
            if editor:
                await editor.fill(content)
                print("内容填充成功")
            else:
                print("未找到编辑器")
        except Exception as e:
            print(f"填充内容失败: {e}")
        
        # 等待内容填充完成
        await asyncio.sleep(2)
        
        # 查找并勾选"收录到我的专栏"选项
        print("查找并勾选'收录到我的专栏'选项...")
        try:
            # 尝试不同的选择器
            column_checkboxes = [
                'input[name="column"]',
                'input[type="checkbox"]',
                'label:has-text("收录到我的专栏")',
                'label:has-text("专栏")'
            ]
            
            for selector in column_checkboxes:
                checkbox = await page.query_selector(selector)
                if checkbox:
                    print(f"找到'收录到我的专栏'选项: {selector}")
                    await checkbox.check()
                    print("成功勾选'收录到我的专栏'选项")
                    break
            else:
                print("未找到'收录到我的专栏'选项")
        except Exception as e:
            print(f"勾选专栏选项失败: {e}")
        
        # 等待勾选完成
        await asyncio.sleep(1)
        
        # 点击发布按钮
        print("点击发布按钮...")
        try:
            # 尝试不同的选择器
            publish_buttons = [
                'button:has-text("发布")',
                'button[type="submit"]',
                'button.primary',
                'button.submit'
            ]
            
            for selector in publish_buttons:
                button = await page.query_selector(selector)
                if button:
                    print(f"找到发布按钮: {selector}")
                    await button.click()
                    break
            else:
                print("未找到发布按钮")
        except Exception as e:
            print(f"点击发布按钮失败: {e}")
        
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
