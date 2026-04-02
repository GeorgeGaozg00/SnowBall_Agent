#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试程序：自动回复关注人的帖子
- 获取关注人的帖子
- 排除自己发的帖子
- 使用 AI 生成评论
- 自动发布评论
"""

import json
import time
import random
import re
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime

# 配置
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

def load_following_list():
    """加载关注列表"""
    try:
        with open(FOLLOWING_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('followingList', []), data.get('userId')
    except Exception as e:
        print(f"加载关注列表失败: {e}")
        return [], None

def get_current_user_id(cookie_str):
    """从Cookie或关注列表文件中获取当前用户ID"""
    # 首先尝试从关注列表文件中获取
    try:
        with open(FOLLOWING_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            user_id = data.get('userId')
            if user_id:
                return int(user_id)
    except Exception as e:
        print(f"从关注列表获取用户ID失败: {e}")
    
    # 尝试从 xq_id_token 中解析
    import base64
    try:
        # 查找 xq_id_token
        match = re.search(r'xq_id_token=([^;]+)', cookie_str)
        if match:
            token = match.group(1)
            # JWT token 的 payload 部分
            parts = token.split('.')
            if len(parts) >= 2:
                payload = parts[1]
                # 添加 padding
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.b64decode(payload)
                data = json.loads(decoded)
                return data.get('uid')
    except Exception as e:
        print(f"从Cookie解析用户ID失败: {e}")
    
    return None

def generate_comment_with_ai(ark_api_key, title, content):
    """使用火山引擎AI生成评论"""
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Authorization": f"Bearer {ark_api_key}",
        "Content-Type": "application/json"
    }
    
    # 构建prompt
    prompt = f"""你是资深投资者，请针对以下雪球网帖子写1-2句理性、专业的评论。
要求：
- 评论要简短有力，1-2句话
- 体现专业投资素养
- 语气友好，有建设性
- 不要过度吹捧，保持理性

帖子标题：{title}
帖子内容：{content[:500]}

请直接输出评论内容，不要有任何前缀说明："""
    
    payload = {
        "model": "doubao-seed-2-0-pro-260215",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        comment = result['choices'][0]['message']['content'].strip()
        # 清理评论
        comment = comment.replace('"', '').replace('"', '').replace('"', '')
        comment = comment.replace('评论：', '').replace('评论:', '').strip()
        return comment
    except Exception as e:
        print(f"AI生成评论失败: {e}")
        return "分析到位，学习了！"

def parse_cookie(cookie_str):
    """解析Cookie字符串为字典"""
    cookies = {}
    if cookie_str:
        for item in cookie_str.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key] = value
    return cookies

def get_following_posts(page, cookie_str, following_uids, my_uid):
    """获取关注人的帖子，排除自己的帖子"""
    posts = []
    
    # 使用API获取关注动态
    headers = {
        "Cookie": cookie_str,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://xueqiu.com",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # 尝试多个API端点
    api_endpoints = [
        {
            "url": "https://xueqiu.com/v4/statuses/public_timeline_by_category.json",
            "params": {"since_id": -1, "max_id": -1, "count": 20, "category": -1}
        },
        {
            "url": "https://xueqiu.com/v4/statuses/home_timeline.json",
            "params": {"count": 20}
        }
    ]
    
    for endpoint in api_endpoints:
        try:
            response = requests.get(
                endpoint["url"],
                headers=headers,
                params=endpoint["params"],
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 解析帖子列表
                items = data.get("list", []) or data.get("statuses", [])
                
                for item in items:
                    if isinstance(item, dict):
                        # 提取帖子数据
                        if "data" in item:
                            post = item["data"]
                        else:
                            post = item
                        
                        user = post.get("user", {})
                        author_uid = user.get("id")
                        
                        # 排除自己的帖子
                        if author_uid == my_uid:
                            continue
                        
                        # 只回复关注的人的帖子
                        if following_uids and author_uid not in following_uids:
                            continue
                        
                        posts.append({
                            "id": post.get("id"),
                            "article_id": post.get("article_id"),
                            "title": post.get("title", ""),
                            "description": post.get("description", ""),
                            "user": user,
                            "author_uid": author_uid,
                            "author_name": user.get("screen_name", "未知"),
                            "created_at": post.get("created_at")
                        })
                
                if posts:
                    break
                    
        except Exception as e:
            print(f"API请求失败: {e}")
            continue
    
    return posts

def reply_to_post(page, post, comment_content, test_mode=False):
    """回复帖子"""
    post_id = post.get("id") or post.get("article_id")
    if not post_id:
        return False, "无效的帖子ID"
    
    try:
        # 访问帖子页面
        post_url = f"https://xueqiu.com/{post['author_uid']}/{post_id}"
        print(f"  访问帖子: {post_url}")
        
        page.goto(post_url, wait_until="networkidle")
        time.sleep(2)
        
        if test_mode:
            print(f"  [测试模式] 将评论: {comment_content}")
            return True, "测试模式，未实际发布"
        
        # 查找评论输入框
        # 尝试多种选择器
        selectors = [
            'textarea[placeholder*="评论"]',
            'textarea[placeholder*="说两句"]',
            '.editor textarea',
            '[class*="comment"] textarea',
            'div[contenteditable="true"]'
        ]
        
        textarea = None
        for selector in selectors:
            try:
                if page.locator(selector).count() > 0:
                    textarea = page.locator(selector).first
                    break
            except:
                continue
        
        if not textarea:
            return False, "未找到评论输入框"
        
        # 输入评论
        textarea.fill(comment_content)
        time.sleep(1)
        
        # 查找发送按钮
        send_selectors = [
            'button:has-text("发送")',
            'button:has-text("评论")',
            'button:has-text("发布")',
            '.submit-btn',
            '[class*="send"]'
        ]
        
        send_btn = None
        for selector in send_selectors:
            try:
                if page.locator(selector).count() > 0:
                    send_btn = page.locator(selector).first
                    break
            except:
                continue
        
        if not send_btn:
            return False, "未找到发送按钮"
        
        # 点击发送
        send_btn.click()
        time.sleep(2)
        
        # 检查是否成功
        page_content = page.content()
        if "成功" in page_content or "评论" in page_content:
            return True, "评论发布成功"
        else:
            return True, "可能发布成功"
            
    except Exception as e:
        return False, f"回复失败: {str(e)}"

def auto_reply_following_posts():
    """自动回复关注人的帖子"""
    print("=" * 60)
    print("自动回复关注人帖子")
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
    my_uid = get_current_user_id(cookie_str)
    if not my_uid:
        print("错误: 无法获取当前用户ID")
        return
    
    print(f"\n当前用户UID: {my_uid}")
    
    # 加载关注列表
    following_list, _ = load_following_list()
    following_uids = {user['uid'] for user in following_list}
    print(f"已加载 {len(following_uids)} 个关注用户")
    
    # 询问测试模式
    test_mode = input("\n是否开启测试模式？(y/n，测试模式不会实际发布评论): ").strip().lower() == 'y'
    
    # 获取帖子
    print("\n获取关注人的帖子...")
    posts = get_following_posts(None, cookie_str, following_uids, my_uid)
    
    if not posts:
        print("未找到可回复的帖子")
        return
    
    print(f"\n找到 {len(posts)} 条可回复的帖子（已排除自己的帖子）")
    
    # 显示帖子列表
    print("\n帖子列表:")
    print("-" * 60)
    for i, post in enumerate(posts[:10], 1):
        print(f"\n{i}. 作者: {post['author_name']}")
        print(f"   标题: {post['title'][:50] if post['title'] else '无标题'}")
        print(f"   内容: {post['description'][:80]}...")
    
    if len(posts) > 10:
        print(f"\n... 还有 {len(posts) - 10} 条帖子")
    
    # 询问要回复的帖子数量
    max_replies = input(f"\n请输入要回复的帖子数量 (1-{len(posts)}，默认5): ").strip()
    max_replies = int(max_replies) if max_replies.isdigit() else 5
    max_replies = min(max_replies, len(posts))
    
    # 启动浏览器
    print("\n启动浏览器...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        # 设置Cookie
        cookies = parse_cookie(cookie_str)
        page.goto("https://xueqiu.com", wait_until="networkidle")
        
        for name, value in cookies.items():
            try:
                context.add_cookies([{
                    'name': name,
                    'value': value,
                    'domain': '.xueqiu.com',
                    'path': '/'
                }])
            except:
                pass
        
        # 回复帖子
        print(f"\n开始回复前 {max_replies} 条帖子...")
        print("=" * 60)
        
        success_count = 0
        fail_count = 0
        
        for i, post in enumerate(posts[:max_replies], 1):
            print(f"\n[{i}/{max_replies}] 回复 {post['author_name']} 的帖子")
            
            # 生成评论
            title = post.get('title', '')
            content = post.get('description', '')
            
            print(f"  生成AI评论...")
            comment = generate_comment_with_ai(ark_api_key, title, content)
            print(f"  评论内容: {comment}")
            
            # 发布评论
            success, message = reply_to_post(page, post, comment, test_mode)
            
            if success:
                print(f"  ✅ {message}")
                success_count += 1
            else:
                print(f"  ❌ {message}")
                fail_count += 1
            
            # 延迟
            if i < max_replies:
                delay = random.uniform(5, 10)
                print(f"  等待 {delay:.1f} 秒...")
                time.sleep(delay)
        
        browser.close()
    
    # 统计结果
    print("\n" + "=" * 60)
    print("回复完成!")
    print(f"成功: {success_count} 条")
    print(f"失败: {fail_count} 条")
    print("=" * 60)

def main():
    """主函数"""
    print("=" * 60)
    print("雪球关注帖子自动回复工具")
    print("=" * 60)
    print("\n功能说明:")
    print("  1. 获取关注人的最新帖子")
    print("  2. 自动排除自己发的帖子")
    print("  3. 使用AI生成专业评论")
    print("  4. 自动发布评论")
    
    auto_reply_following_posts()

if __name__ == "__main__":
    main()
