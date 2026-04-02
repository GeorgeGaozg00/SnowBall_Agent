#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合版：获取关注帖子并自动回复
基于 test_following_posts_auto.py 的获取逻辑
"""

import json
import time
import random
import requests
from playwright.sync_api import sync_playwright

CONFIG_FILE = '../backend/config.json'
FOLLOWING_FILE = '../backend/following_list.json'

def load_config():
    """加载配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置失败: {e}")
        return None

def get_current_user_id():
    """从关注列表文件中获取当前用户ID"""
    try:
        with open(FOLLOWING_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            user_id = data.get('userId')
            if user_id:
                return int(user_id)
    except Exception as e:
        print(f"获取用户ID失败: {e}")
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

def generate_comment(ark_api_key, title, text):
    """使用火山引擎API生成评论"""
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ark_api_key}"
    }
    prompt = f"你是资深投资者，写1-2句理性雪球评论，专业简洁。文章：{title} 内容：{text[:500]} 评论："
    payload = {
        "model": "doubao-seed-2-0-pro-260215",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"生成评论失败: {e}")
        return "分析到位，学习了"

def post_comment(cookie_str, article_id, content):
    """使用雪球API发布评论"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_str
    }
    
    # 1. 文本审核
    print("  1) 文本审核...", end=" ")
    text_check_url = "https://xueqiu.com/statuses/text_check.json"
    text_check_data = {"text": f"<p>{content}</p>", "type": "3"}
    
    try:
        text_check_response = requests.post(text_check_url, headers=headers, data=text_check_data)
        if text_check_response.status_code != 200:
            print("❌")
            return {"success": False, "message": "文本审核失败"}
        print("✅")
    except Exception as e:
        print(f"❌ {e}")
        return {"success": False, "message": f"文本审核请求失败: {e}"}
    
    time.sleep(1)
    
    # 2. 获取会话token
    print("  2) 获取token...", end=" ")
    token_url = "https://xueqiu.com/provider/session/token.json"
    token_params = {"api_path": "/statuses/reply.json", "_": int(time.time() * 1000)}
    
    try:
        token_response = requests.get(token_url, headers=headers, params=token_params)
        if token_response.status_code != 200:
            print("❌")
            return {"success": False, "message": "获取token失败"}
        
        token_data = token_response.json()
        session_token = token_data.get("session_token", "")
        if not session_token:
            print("❌")
            return {"success": False, "message": "未获取到session_token"}
        print("✅")
    except Exception as e:
        print(f"❌ {e}")
        return {"success": False, "message": f"获取token失败: {e}"}
    
    time.sleep(1)
    
    # 3. 发布评论
    print("  3) 发布评论...", end=" ")
    reply_url = "https://xueqiu.com/statuses/reply.json"
    reply_data = {
        "comment": f"<p>{content}</p>",
        "forward": "1",
        "id": article_id,
        "post_source": "htl",
        "post_position": "pc_home_feedcard",
        "session_token": session_token
    }
    
    try:
        reply_response = requests.post(reply_url, headers=headers, data=reply_data)
        if reply_response.status_code == 200:
            reply_data = reply_response.json()
            if "id" in reply_data:
                print("✅")
                return {"success": True, "message": "评论发布成功", "comment_id": reply_data.get('id')}
            else:
                print("❌ 响应格式异常")
                return {"success": False, "message": "评论发布失败: 响应格式异常"}
        else:
            print(f"❌ 状态码{reply_response.status_code}")
            return {"success": False, "message": f"评论发布失败，状态码: {reply_response.status_code}"}
    except Exception as e:
        print(f"❌ {e}")
        return {"success": False, "message": f"发布评论请求失败: {e}"}

def get_following_posts(cookie_str, my_uid, max_scrolls=20):
    """
    使用Playwright获取关注页面的帖子
    """
    print("\n" + "=" * 60)
    print("自动获取关注页面帖子")
    print("=" * 60)
    
    api_responses = []
    
    with sync_playwright() as p:
        print("\n启动浏览器...")
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        # 设置Cookie
        print("设置Cookie...")
        page.goto("https://xueqiu.com", wait_until="networkidle")
        
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
        
        # 监听网络请求
        print("\n开始监听API请求...")
        
        def handle_response(response):
            """处理响应，捕获包含帖子的API"""
            url = response.url
            if 'home_timeline' in url or 'statuses' in url:
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
        
        # 检查登录状态
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
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(random.uniform(2, 4))
            
            if scroll_count % 5 == 0:
                print(f"已滚动 {scroll_count}/{max_scrolls} 次，捕获 {len(api_responses)} 个API")
        
        print("-" * 60)
        print(f"✅ 滚动完成，总共捕获 {len(api_responses)} 个API响应")
        
        browser.close()
    
    # 解析数据
    all_posts = parse_api_responses(api_responses, my_uid)
    return all_posts

def parse_api_responses(api_responses, my_uid):
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
        
        # home_timeline.json 返回的数据结构
        statuses = None
        if isinstance(data, dict):
            if 'statuses' in data:
                statuses = data['statuses']
            elif 'list' in data:
                statuses = data['list']
            elif 'data' in data and isinstance(data['data'], list):
                statuses = data['data']
        elif isinstance(data, list):
            statuses = data
        
        if statuses and isinstance(statuses, list):
            print(f"  从 {url[:50]}... 解析到 {len(statuses)} 条数据")
            
            for status in statuses:
                if isinstance(status, dict):
                    # 有些API返回的是包装格式
                    if 'data' in status and isinstance(status['data'], dict):
                        post = status['data']
                    else:
                        post = status
                    
                    # 获取帖子ID用于去重
                    post_id = post.get('id') or post.get('article_id') or post.get('status_id')
                    
                    if not post_id or post_id in seen_ids:
                        continue
                    
                    # 获取作者信息
                    user = post.get('user', {})
                    author_uid = user.get('id')
                    
                    # 排除自己的帖子
                    if author_uid == my_uid:
                        continue
                    
                    seen_ids.add(post_id)
                    
                    # 提取关键字段
                    post_data = {
                        'id': post_id,
                        'title': post.get('title', ''),
                        'description': post.get('description', ''),
                        'text': post.get('text', ''),
                        'author_uid': author_uid,
                        'author_name': user.get('screen_name', '未知用户'),
                        'author_id': user.get('id'),
                        'created_at': post.get('created_at', ''),
                        'view_count': post.get('view_count', 0)
                    }
                    all_posts.append(post_data)
    
    print(f"\n✅ 去重后得到 {len(all_posts)} 条唯一帖子（已排除自己的帖子）")
    
    # 保存数据
    if all_posts:
        output_file = 'following_posts_final.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存到 {output_file}")
        
        # 显示前10条帖子
        print("\n前10条帖子预览:")
        print("=" * 60)
        for i, post in enumerate(all_posts[:10], 1):
            print(f"\n{i}. 作者: {post['author_name']} (UID: {post['author_uid']})")
            if post['title']:
                print(f"   标题: {post['title'][:60]}")
            content = post['description'] or post['text'] or ''
            print(f"   内容: {content[:80]}...")
    
    return all_posts

def main():
    """主函数"""
    print("=" * 60)
    print("自动获取关注帖子并回复 - 整合版")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    if not config:
        print("错误: 无法加载配置")
        return
    
    ark_api_key = config.get('arkApiKey')
    cookie_str = config.get('xueQiuCookie')
    
    if not ark_api_key or not cookie_str:
        print("错误: 缺少API Key或Cookie")
        return
    
    # 获取当前用户ID
    my_uid = get_current_user_id()
    if not my_uid:
        print("错误: 无法获取当前用户ID")
        return
    
    print(f"\n当前用户UID: {my_uid}")
    
    # 获取关注人的帖子
    posts = get_following_posts(cookie_str, my_uid, max_scrolls=20)
    
    if not posts:
        print("未找到可回复的帖子")
        return
    
    # 询问要回复的数量
    max_replies = input(f"\n请输入要回复的帖子数量 (1-{len(posts)}，默认3): ").strip()
    max_replies = int(max_replies) if max_replies.isdigit() else 3
    max_replies = min(max_replies, len(posts))
    
    # 询问测试模式
    test_mode = input("是否开启测试模式？(y/n，默认y): ").strip().lower() != 'n'
    
    # 开始回复
    print(f"\n开始回复前 {max_replies} 条帖子...")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for i, post in enumerate(posts[:max_replies], 1):
        print(f"\n[{i}/{max_replies}] 回复 {post['author_name']} 的帖子")
        print(f"   ID: {post['id']}")
        
        # 生成评论
        title = post.get('title', '')
        content = post.get('description', '') or post.get('text', '')
        
        print(f"  生成AI评论...")
        comment = generate_comment(ark_api_key, title, content)
        print(f"  评论: {comment}")
        
        if test_mode:
            print(f"  [测试模式] 跳过发布")
            success_count += 1
        else:
            # 发布评论
            result = post_comment(cookie_str, post['id'], comment)
            if result['success']:
                print(f"  ✅ {result['message']}")
                success_count += 1
            else:
                print(f"  ❌ {result['message']}")
                fail_count += 1
        
        # 延迟
        if i < max_replies:
            delay = random.uniform(5, 10)
            print(f"  等待 {delay:.1f} 秒...")
            time.sleep(delay)
    
    # 统计结果
    print("\n" + "=" * 60)
    print("完成!")
    print(f"成功: {success_count} 条")
    print(f"失败: {fail_count} 条")
    print("=" * 60)

if __name__ == "__main__":
    main()
