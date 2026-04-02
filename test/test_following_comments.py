#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关注列表评论器：自动为所有关注用户的帖子生成并发布评论
"""

import json
import time
import requests
import random
import os

CONFIG_FILE = '../backend/config.json'
FOLLOWING_LIST_FILE = '../backend/following_list.json'

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
        with open(FOLLOWING_LIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载关注列表失败: {e}")
        return None

def get_user_posts(user_uid, cookie_str, max_posts=10):
    """获取用户最近发表的文章"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": f"https://xueqiu.com/u/{user_uid}",
        "Cookie": cookie_str,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    
    all_posts = []
    page = 1
    page_size = 20
    
    while len(all_posts) < max_posts:
        api_url = "https://xueqiu.com/statuses/user_timeline.json"
        params = {
            "user_id": user_uid,
            "page": page,
            "count": page_size,
            "max_id": 0
        }
        
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            statuses = data.get('statuses', [])
            
            if not statuses:
                break
            
            for status in statuses:
                if isinstance(status, dict):
                    post_data = {
                        'id': status.get('id'),
                        'title': status.get('title', ''),
                        'description': status.get('description', ''),
                        'text': status.get('text', ''),
                        'created_at': status.get('created_at'),
                        'author_uid': user_uid,
                        'view_count': status.get('view_count', 0),
                        'reply_count': status.get('reply_count', 0),
                        'like_count': status.get('like_count', 0)
                    }
                    all_posts.append(post_data)
                    
                    if len(all_posts) >= max_posts:
                        break
            
            page += 1
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"  获取帖子失败: {e}")
            break
    
    return all_posts[:max_posts]

def generate_share_link(author_uid, post_id, share_uid):
    """生成分享链接"""
    return f"https://xueqiu.com/{author_uid}/{post_id}?scene=1036&share_uid={share_uid}"

def generate_comment_with_ai(url, api_key):
    """使用AI API生成评论"""
    api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 用户提供的提示词
    prompt = f"读取雪球指定 URL 帖子全文内容，贴合散户共情口吻，生成一条简短自然、适配社区氛围、可直接发布的暖心评论，不堆砌专业术语、不写长篇大论，纯贴合原文情绪输出。 `{url}`"
    
    payload = {
        "model": "doubao-seed-2-0-pro-260215",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        comment = result['choices'][0]['message']['content'].strip()
        return comment
    except Exception as e:
        print(f"  生成评论失败: {str(e)}")
        return "分析到位，学习了"

def post_comment(article_id, content, cookie_str):
    """使用雪球API发布评论"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_str
    }
    
    # 1. 文本审核
    try:
        text_check_url = "https://xueqiu.com/statuses/text_check.json"
        text_check_data = {
            "text": f"<p>{content}</p>",
            "type": "3"
        }
        text_check_response = requests.post(text_check_url, headers=headers, data=text_check_data)
        if text_check_response.status_code != 200:
            return {"success": False, "message": "文本审核失败"}
    except Exception as e:
        return {"success": False, "message": f"文本审核请求失败: {str(e)}"}
    
    time.sleep(1)
    
    # 2. 获取会话token
    try:
        token_url = "https://xueqiu.com/provider/session/token.json"
        token_params = {
            "api_path": "/statuses/reply.json",
            "_": int(time.time() * 1000)
        }
        token_response = requests.get(token_url, headers=headers, params=token_params)
        if token_response.status_code != 200:
            return {"success": False, "message": "获取token失败"}
        
        token_data = token_response.json()
        session_token = token_data.get("session_token", "")
        if not session_token:
            return {"success": False, "message": "未获取到session_token"}
    except Exception as e:
        return {"success": False, "message": f"获取token请求失败: {str(e)}"}
    
    time.sleep(1)
    
    # 3. 发布评论
    try:
        reply_url = "https://xueqiu.com/statuses/reply.json"
        reply_data = {
            "comment": f"<p>{content}</p>",
            "forward": "1",
            "id": article_id,
            "post_source": "htl",
            "post_position": "pc_home_feedcard",
            "session_token": session_token
        }
        reply_response = requests.post(reply_url, headers=headers, data=reply_data)
        if reply_response.status_code == 200:
            reply_data = reply_response.json()
            if "id" in reply_data:
                return {"success": True, "message": "评论发布成功", "comment_id": reply_data.get('id')}
            else:
                return {"success": False, "message": "评论发布失败: 响应格式异常"}
        else:
            return {"success": False, "message": f"评论发布请求失败，状态码: {reply_response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"发布评论请求失败: {str(e)}"}

def main():
    """主函数"""
    print("=" * 80)
    print("关注列表评论器：自动为所有关注用户的帖子生成并发布评论")
    print("=" * 80)
    
    # 加载配置
    config = load_config()
    if not config:
        print("错误: 无法加载配置")
        return
    
    cookie_str = config.get('xueQiuCookie')
    if not cookie_str:
        print("错误: 缺少Cookie")
        return
    
    api_key = config.get('arkApiKey')
    if not api_key:
        print("错误: 缺少AI API Key")
        return
    
    # 加载关注列表
    following_data = load_following_list()
    if not following_data:
        print("错误: 无法加载关注列表")
        return
    
    my_uid = following_data.get('userId')
    following_list = following_data.get('followingList', [])
    total_users = len(following_list)
    
    print(f"\n✅ 成功加载关注列表")
    print(f"当前用户UID: {my_uid}")
    print(f"关注用户数量: {total_users}")
    
    # 输入测试模式
    test_mode_input = input("是否开启测试模式（不实际发布评论）？ (y/N): ").strip().lower()
    test_mode = test_mode_input == 'y'
    
    # 输入要处理的用户数量
    user_limit_input = input(f"请输入要处理的用户数量（默认全部 {total_users}）: ").strip()
    user_limit = int(user_limit_input) if user_limit_input.isdigit() else total_users
    user_limit = min(user_limit, total_users)
    
    # 输入每个用户的帖子数量
    posts_per_user_input = input("请输入每个用户处理的帖子数量（默认10）: ").strip()
    posts_per_user = int(posts_per_user_input) if posts_per_user_input.isdigit() else 10
    posts_per_user = min(posts_per_user, 10)
    
    print(f"\n开始处理 {user_limit} 个用户，每个用户处理 {posts_per_user} 个帖子")
    print("=" * 80)
    
    # 统计信息
    total_users_processed = 0
    total_posts_processed = 0
    total_comments_success = 0
    
    # 处理每个用户
    for i, user in enumerate(following_list[:user_limit], 1):
        user_uid = user.get('uid')
        user_name = user.get('screen_name')
        
        print(f"\n" + "=" * 80)
        print(f"处理用户 {i}/{user_limit}: {user_name} (UID: {user_uid})")
        print("=" * 80)
        
        # 获取用户最近的帖子
        posts = get_user_posts(user_uid, cookie_str, posts_per_user)
        
        if not posts:
            print(f"  ❌ 未找到帖子")
            # 延迟
            delay = random.uniform(10, 15)
            print(f"  等待 {delay:.1f} 秒...")
            time.sleep(delay)
            continue
        
        print(f"  ✅ 成功获取 {len(posts)} 个帖子")
        
        # 处理每个帖子
        user_comments_success = 0
        for j, post in enumerate(posts, 1):
            print(f"\n  处理帖子 {j}/{len(posts)}")
            print(f"  帖子ID: {post['id']}")
            if post['title']:
                print(f"  标题: {post['title'][:50]}...")
            
            # 生成分享链接
            share_link = generate_share_link(user_uid, post['id'], my_uid)
            print(f"  分享链接: {share_link}")
            
            # 使用AI生成评论
            print("  生成评论...")
            comment = generate_comment_with_ai(share_link, api_key)
            print(f"  评论: {comment}")
            
            # 发布评论
            if test_mode:
                print("  测试模式：跳过发布评论")
                post_result = {"success": True, "message": "测试模式，未实际发布"}
            else:
                print("  发布评论...")
                post_result = post_comment(post['id'], comment, cookie_str)
            
            if post_result.get('success'):
                print("  ✅ 评论发布成功")
                if not test_mode:
                    print(f"  评论ID: {post_result.get('comment_id')}")
                user_comments_success += 1
                total_comments_success += 1
            else:
                print(f"  ❌ 评论发布失败: {post_result.get('message')}")
            
            # 帖子之间的延迟
            delay = random.uniform(8, 12)
            print(f"  等待 {delay:.1f} 秒...")
            time.sleep(delay)
        
        total_users_processed += 1
        total_posts_processed += len(posts)
        
        print(f"\n  用户 {user_name} 处理完成")
        print(f"  成功发布 {user_comments_success}/{len(posts)} 条评论")
        
        # 用户之间的延迟
        if i < user_limit:
            delay = random.uniform(15, 25)
            print(f"\n等待 {delay:.1f} 秒后处理下一个用户...")
            time.sleep(delay)
    
    # 显示总结
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    print(f"成功处理 {total_users_processed} 个用户")
    print(f"成功处理 {total_posts_processed} 个帖子")
    print(f"成功发布 {total_comments_success} 条评论")
    print(f"成功率: {total_comments_success}/{total_posts_processed} = {total_comments_success/total_posts_processed*100:.1f}%")
    
    print("\n" + "=" * 80)
    print("完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()
