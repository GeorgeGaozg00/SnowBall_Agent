#!/usr/bin/env python3
# 雪球长文发布测试 - 最终版

import requests
import json
import os
import re
from playwright.sync_api import sync_playwright

# 从配置文件读取cookie
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', 'config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
    COOKIE = config.get('xueQiuCookie', '')

# 文章内容（普通长文）
ARTICLE = {
    "title": "API 发文测试标题",
    "status": """<p>这是正文内容，测试普通长文发布功能。</p>
<p>支持换行和基本格式。</p>
<p>这是一段足够长的内容，确保超过100字的要求。我们需要测试API发布功能是否正常工作，以及文章类型是否正确识别。</p>
<p>本文主要测试以下几点：</p>
<ul>
<li>文章标题是否正确显示</li>
<li>文章内容格式是否保留</li>
<li>文章类型是否为普通长文</li>
</ul>
<p>感谢您的关注！</p>""",
    "cover_pic": "",          # 封面图URL（可选）
    "show_cover_pic": "true", # 是否显示封面
    "original": "false",      # 是否声明原创（需开通专栏）
    "comment_disabled": "false", # 是否关闭评论
    "type": "1"               # 1: 普通长文, 8: 专栏文章
}

# 专栏文章内容
ARTICLE_COLUMN = {
    "title": "API 专栏文章测试标题",
    "status": """<p>这是专栏文章正文内容，测试专栏文章发布功能。</p>
<p>专栏文章需要满足以下条件：</p>
<ol>
<li>必须有标题（title字段）</li>
<li>内容必须有HTML标签</li>
<li>内容长度至少100字</li>
<li>Referer必须正确设置</li>
<li>type参数需要设置为8</li>
</ol>
<p>本文将测试这些条件是否满足。专栏文章是雪球平台上的重要内容形式，可以获得更多的曝光和推荐。</p>
<p>专栏文章的优势：</p>
<ul>
<li>获得更多推荐机会</li>
<li>可以建立个人品牌</li>
<li>获得版权保护</li>
<li>有机会参与出版计划</li>
</ul>
<p>感谢您的关注和支持！</p>""",
    "cover_pic": "",          # 封面图URL（可选）
    "show_cover_pic": "true", # 是否显示封面
    "original": "false",      # 是否声明原创（需开通专栏）
    "comment_disabled": "false", # 是否关闭评论
    "type": "8"               # 1: 普通长文, 8: 专栏文章
}

def publish_xueqiu_article_api(cookie, article):
    """使用API发布雪球长文"""
    session = requests.Session()
    
    # 1. 构造请求头
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": cookie.strip().replace("\n", ""),
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://xueqiu.com/write",
        "Origin": "https://xueqiu.com",
        "Host": "xueqiu.com"
    }
    
    # 2. 先访问mp.xueqiu.com/write/页面建立会话
    print("访问mp.xueqiu.com/write/页面...")
    try:
        write_response = session.get("https://mp.xueqiu.com/write/", headers=headers)
        print(f"页面访问状态码: {write_response.status_code}")
        
        if "login" in write_response.url or write_response.status_code == 302:
            print("被重定向到登录页面，cookie可能无效")
            return None
        
        if write_response.status_code == 200:
            print("页面访问成功")
    except Exception as e:
        print(f"访问页面时出错: {str(e)}")
        return None
    
    # 3. 尝试获取session_token
    token_urls = [
        "https://mp.xueqiu.com/xq/provider/session/token.json?api_path=%2Fstatuses%2Fupdate.json",
        "https://mp.xueqiu.com/xq/provider/session/token.json",
        "https://xueqiu.com/provider/session/token.json?api_path=%2Fstatuses%2Fupdate.json",
        "https://xueqiu.com/provider/session/token.json"
    ]
    
    session_token = None
    for token_url in token_urls:
        print(f"\n尝试获取session_token: {token_url}")
        try:
            res = session.get(token_url, headers=headers)
            print(f"响应状态码: {res.status_code}")
            print(f"响应内容: {res.text}")
            
            if res.status_code == 200:
                try:
                    result = res.json()
                    if "session_token" in result:
                        session_token = result["session_token"]
                        print(f"获取 session_token 成功：{session_token[:16]}...")
                        break
                    else:
                        print(f"响应中没有session_token: {result}")
                except Exception as e:
                    print(f"解析JSON时出错: {str(e)}")
            elif res.status_code == 400:
                print("请求失败，可能需要更新cookie")
            else:
                print(f"请求失败，状态码: {res.status_code}")
        except Exception as e:
            print(f"获取session_token时出错: {str(e)}")
    
    if not session_token:
        print("无法获取session_token")
        return None
    
    # 4. 尝试发文
    post_urls = [
        "https://xueqiu.com/statuses/update.json",
        "https://mp.xueqiu.com/xq/statuses/update.json",
        "https://mp.xueqiu.com/statuses/update.json"
    ]
    
    for post_url in post_urls:
        print(f"\n尝试发文接口: {post_url}")
        
        # 构造请求数据
        data = {
            "title": article["title"],
            "status": article["status"],
            "cover_pic": article["cover_pic"],
            "show_cover_pic": article["show_cover_pic"],
            "original": article["original"],
            "comment_disabled": article["comment_disabled"],
            "session_token": session_token,
            "device": "Web",
            "right": "0",
            "draft_id": "0",
            "type": article.get("type", "1"),  # 1: 普通长文, 8: 专栏文章
            "is_column": "true" if article.get("type") == "8" else "false",
            "column": "true" if article.get("type") == "8" else "false"
        }
        
        # 5. 发送请求
        try:
            resp = session.post(post_url, data=data, headers=headers)
            print(f"响应状态码: {resp.status_code}")
            print(f"响应内容: {resp.text}")
            
            if resp.status_code == 200:
                try:
                    result = resp.json()
                    if result.get("id"):
                        article_url = f"https://xueqiu.com/{result['user_id']}/{result['id']}"
                        print("✅ 发文成功！")
                        print(f"文章ID：{result['id']}")
                        print(f"文章链接：{article_url}")
                        return article_url
                    else:
                        print(f"❌ 发文失败：{result}")
                except Exception as e:
                    print(f"解析响应时出错: {str(e)}")
            else:
                print(f"请求失败，状态码: {resp.status_code}")
        except Exception as e:
            print(f"请求异常：{e}")
            if resp.text:
                print(f"返回内容：{resp.text}")
    
    return None

def publish_xueqiu_article_browser(article):
    """使用浏览器自动化发布雪球长文"""
    print("\n=== 使用浏览器自动化发布 ===")
    
    with sync_playwright() as p:
        # 启动浏览器
        print("启动浏览器...")
        browser = p.chromium.launch(headless=False, args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox"
        ])
        page = browser.new_page()
        
        try:
            # 访问雪球写作页面
            print("访问雪球写作页面...")
            page.goto('https://mp.xueqiu.com/write/')
            
            # 等待页面加载完成
            print("等待页面加载完成...")
            page.wait_for_load_state('networkidle')
            
            # 提示用户登录
            print("\n请在浏览器中登录雪球账号")
            print("登录完成后按Enter键继续...")
            input()
            
            # 等待页面加载完成
            page.wait_for_load_state('networkidle')
            
            # 输入标题
            print("输入文章标题...")
            try:
                title_input = page.wait_for_selector('input[placeholder*="标题"]', timeout=10000)
                title_input.fill(article["title"])
                print("标题输入成功")
            except:
                print("未找到标题输入框")
                return None
            
            # 输入正文
            print("输入文章正文...")
            try:
                # 尝试找到正文输入框
                content_selectors = [
                    'textarea[placeholder*="正文"]',
                    'div[contenteditable="true"]',
                    '.editor-content',
                    '#editor'
                ]
                
                content_input = None
                for selector in content_selectors:
                    try:
                        content_input = page.wait_for_selector(selector, timeout=5000)
                        if content_input:
                            break
                    except:
                        continue
                
                if content_input:
                    content_input.fill(article["status"])
                    print("正文输入成功")
                else:
                    print("未找到正文输入框")
                    return None
            except Exception as e:
                print(f"输入正文时出错: {str(e)}")
                return None
            
            # 点击发布按钮
            print("点击发布按钮...")
            try:
                publish_button = page.wait_for_selector('button:has-text("发布")', timeout=10000)
                publish_button.click()
                print("点击发布按钮成功")
            except:
                print("未找到发布按钮")
                return None
            
            # 等待发布完成
            print("等待发布完成...")
            page.wait_for_load_state('networkidle')
            
            print("发布操作完成！")
            return True
            
        except Exception as e:
            print(f"浏览器自动化失败: {e}")
            return None
        finally:
            # 关闭浏览器
            browser.close()

def main():
    print("雪球长文发布测试 - 最终版")
    print("=" * 60)
    
    # 测试1：普通长文（type=1）
    print("\n【测试1】发布普通长文（type=1）")
    print("-" * 60)
    print(f"文章标题: {ARTICLE['title']}")
    print(f"文章内容: {ARTICLE['status'][:50]}...")
    print(f"内容类型: type={ARTICLE['type']}")
    print()
    
    # 方案1：使用API发布
    if COOKIE:
        print("=== 方案1：使用API发布 ===")
        print(f"Cookie: {COOKIE[:50]}...")
        print()
        
        result = publish_xueqiu_article_api(COOKIE, ARTICLE)
        
        if result:
            print("\n✅ 普通长文发布成功！")
        else:
            print("\n❌ 普通长文发布失败！")
    
    # 等待一段时间
    import time
    print("\n等待5秒后继续测试...")
    time.sleep(5)
    
    # 测试2：专栏文章（type=8）
    print("\n【测试2】发布专栏文章（type=8）")
    print("-" * 60)
    print(f"文章标题: {ARTICLE_COLUMN['title']}")
    print(f"文章内容: {ARTICLE_COLUMN['status'][:50]}...")
    print(f"内容类型: type={ARTICLE_COLUMN['type']}")
    print()
    
    # 方案1：使用API发布
    if COOKIE:
        print("=== 方案1：使用API发布 ===")
        print(f"Cookie: {COOKIE[:50]}...")
        print()
        
        result = publish_xueqiu_article_api(COOKIE, ARTICLE_COLUMN)
        
        if result:
            print("\n✅ 专题文章发布成功！")
        else:
            print("\n❌ 专题文章发布失败！")

if __name__ == "__main__":
    main()
