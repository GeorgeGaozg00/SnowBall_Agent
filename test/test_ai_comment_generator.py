#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI评论生成器：从用户UID到生成评论
"""

import json
import time
import requests
import random

CONFIG_FILE = '../backend/config.json'

def load_config():
    """加载配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置失败: {e}")
        return None

def get_user_posts(user_uid, cookie_str, max_posts=10):
    """获取用户最近发表的文章"""
    print(f"\n" + "=" * 60)
    print(f"获取用户 {user_uid} 的最近 {max_posts} 个帖子")
    print("=" * 60)
    
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
            print(f"  正在获取第 {page} 页...")
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            statuses = data.get('statuses', [])
            
            if not statuses:
                print("  没有更多帖子")
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
            time.sleep(2)
            
        except Exception as e:
            print(f"  获取失败: {e}")
            break
    
    all_posts = all_posts[:max_posts]
    
    print(f"\n✅ 成功获取 {len(all_posts)} 个帖子")
    
    if all_posts:
        print("\n帖子列表:")
        print("=" * 60)
        for i, post in enumerate(all_posts, 1):
            print(f"\n{i}. ID: {post['id']}")
            if post['title']:
                print(f"   标题: {post['title'][:60]}")
            content = post['description'] or post['text'] or ''
            print(f"   内容: {content[:80]}...")
            if post['created_at']:
                try:
                    print(f"   时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(post['created_at']/1000))}")
                except:
                    pass
            print(f"   浏览: {post['view_count']} | 回复: {post['reply_count']} | 点赞: {post['like_count']}")
    
    return all_posts

def generate_share_link(author_uid, post_id, share_uid):
    """生成分享链接"""
    share_link = f"https://xueqiu.com/{author_uid}/{post_id}?scene=1036&share_uid={share_uid}"
    print(f"\n生成分享链接: {share_link}")
    return share_link

def generate_comment_with_ai(url, api_key):
    """使用AI API生成评论"""
    print(f"\n使用AI生成评论...")
    
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
        print(f"  ✅ 生成评论成功")
        print(f"  评论: {comment}")
        return comment
    except Exception as e:
        print(f"  ❌ 生成评论失败: {str(e)}")
        return "分析到位，学习了"

def main():
    """主函数"""
    print("=" * 60)
    print("AI评论生成器：从用户UID到生成评论")
    print("=" * 60)
    
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
    
    # 输入用户UID
    user_uid = input("请输入用户UID: ").strip()
    if not user_uid:
        print("错误: 请输入有效的用户UID")
        return
    
    # 输入分享者UID（自己的UID）
    share_uid = input("请输入分享者UID（通常是自己的UID）: ").strip()
    if not share_uid:
        print("错误: 请输入分享者UID")
        return
    
    # 输入要获取的帖子数量
    max_posts = input("请输入要获取的帖子数量（默认3）: ").strip()
    max_posts = int(max_posts) if max_posts.isdigit() else 3
    max_posts = min(max_posts, 10)
    
    # 1. 获取用户最近的帖子
    posts = get_user_posts(user_uid, cookie_str, max_posts)
    
    if not posts:
        print("未找到帖子")
        return
    
    # 2. 为每个帖子生成分享链接并使用AI生成评论
    results = []
    for i, post in enumerate(posts, 1):
        print(f"\n" + "=" * 60)
        print(f"处理第 {i} 个帖子")
        print("=" * 60)
        
        # 生成分享链接
        share_link = generate_share_link(user_uid, post['id'], share_uid)
        
        # 使用AI生成评论
        comment = generate_comment_with_ai(share_link, api_key)
        
        # 保存结果
        result = {
            'post_id': post['id'],
            'title': post['title'],
            'share_link': share_link,
            'comment': comment
        }
        results.append(result)
        
        # 延迟
        if i < len(posts):
            delay = random.uniform(3, 5)
            print(f"\n等待 {delay:.1f} 秒...")
            time.sleep(delay)
    
    # 保存所有结果
    output_file = f"ai_comments_{user_uid}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已保存所有评论到 {output_file}")
    
    # 显示总结
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print(f"成功为 {len(results)} 个帖子生成评论")
    print("\n生成的评论：")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['comment']}")
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
