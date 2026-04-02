#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过用户UID获取最近10个帖子
"""

import json
import time
import requests

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
    """
    通过用户UID获取最近的帖子
    """
    print(f"\n" + "=" * 60)
    print(f"获取用户 {user_uid} 的最近 {max_posts} 个帖子")
    print("=" * 60)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": f"https://xueqiu.com/{user_uid}",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_str
    }
    
    all_posts = []
    page = 1
    page_size = 20  # 每页20条
    
    while len(all_posts) < max_posts:
        url = f"https://xueqiu.com/v4/statuses/user_timeline.json"
        params = {
            "page": page,
            "user_id": user_uid,
            "count": page_size,
            "max_id": 0,
            "feed": "stock"
        }
        
        try:
            print(f"  正在获取第 {page} 页...")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            statuses = data.get('statuses', [])
            
            if not statuses:
                print("  没有更多帖子")
                break
            
            for status in statuses:
                if isinstance(status, dict):
                    # 提取关键字段
                    post_data = {
                        'id': status.get('id'),
                        'title': status.get('title', ''),
                        'description': status.get('description', ''),
                        'text': status.get('text', ''),
                        'created_at': status.get('created_at'),
                        'view_count': status.get('view_count', 0),
                        'reply_count': status.get('reply_count', 0),
                        'like_count': status.get('like_count', 0),
                        'source': status.get('source', '')
                    }
                    all_posts.append(post_data)
                    
                    if len(all_posts) >= max_posts:
                        break
            
            page += 1
            time.sleep(2)  # 防止请求过快
            
        except Exception as e:
            print(f"  获取失败: {e}")
            break
    
    # 截取前max_posts个
    all_posts = all_posts[:max_posts]
    
    print(f"\n✅ 成功获取 {len(all_posts)} 个帖子")
    
    # 保存数据
    if all_posts:
        output_file = f'user_{user_uid}_posts.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存到 {output_file}")
        
        # 显示帖子
        print("\n帖子列表:")
        print("=" * 60)
        for i, post in enumerate(all_posts, 1):
            print(f"\n{i}. ID: {post['id']}")
            if post['title']:
                print(f"   标题: {post['title'][:60]}")
            content = post['description'] or post['text'] or ''
            print(f"   内容: {content[:80]}...")
            print(f"   时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(post['created_at']/1000))}")
            print(f"   浏览: {post['view_count']} | 回复: {post['reply_count']} | 点赞: {post['like_count']}")
    
    return all_posts

def main():
    """主函数"""
    print("=" * 60)
    print("通过UID获取用户最近帖子")
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
    
    # 输入用户UID
    user_uid = input("请输入用户UID: ").strip()
    if not user_uid:
        print("错误: 请输入有效的用户UID")
        return
    
    # 输入要获取的帖子数量
    max_posts = input("请输入要获取的帖子数量（默认10）: ").strip()
    max_posts = int(max_posts) if max_posts.isdigit() else 10
    max_posts = min(max_posts, 50)  # 最多50个
    
    # 获取帖子
    get_user_posts(user_uid, cookie_str, max_posts)

if __name__ == "__main__":
    main()
