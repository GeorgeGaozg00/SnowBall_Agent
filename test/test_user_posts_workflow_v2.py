#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版：从用户UID到文章详细内容
"""

import json
import time
import requests
from bs4 import BeautifulSoup

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
        "Cookie": cookie_str
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
                        'created_at': status.get('created_at'),
                        'author_uid': user_uid
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
            content = post['description'] or ''
            print(f"   内容: {content[:80]}...")
            if post['created_at']:
                try:
                    print(f"   时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(post['created_at']/1000))}")
                except:
                    pass
    
    return all_posts

def generate_share_link(author_uid, post_id, share_uid):
    """生成分享链接"""
    share_link = f"https://xueqiu.com/{author_uid}/{post_id}?scene=1036&share_uid={share_uid}"
    print(f"\n生成分享链接: {share_link}")
    return share_link

def get_post_detail_from_link(share_link, cookie_str):
    """从分享链接获取帖子详细信息"""
    print(f"\n从分享链接获取详细信息...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": share_link,
        "Cookie": cookie_str,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    
    # 直接访问分享链接
    try:
        response = requests.get(share_link, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 检查是否重定向
        if response.history:
            print(f"  重定向到: {response.url}")
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取帖子信息
        post_detail = {
            'title': '',
            'content': '',
            'created_at': '',
            'view_count': 0,
            'reply_count': 0,
            'like_count': 0,
            'author_name': ''
        }
        
        # 查找标题（多种可能的选择器）
        title_selectors = [
            'h1.article__title',
            'h2.title',
            'div.article-title',
            'div.title',
            'h1.title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                post_detail['title'] = title_elem.get_text(strip=True)
                break
        
        # 查找内容（多种可能的选择器）
        content_selectors = [
            'div.article__content',
            'div.article-content',
            'div.content',
            'div.article-body',
            'div.post-content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                post_detail['content'] = content_elem.get_text(separator='\n', strip=True)
                break
        
        # 查找作者信息
        author_selectors = [
            'div.article__author',
            'div.user-info',
            'div.author-info',
            'a.user-name'
        ]
        
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                post_detail['author_name'] = author_elem.get_text(strip=True)
                break
        
        # 查找统计信息
        stats_selectors = [
            'div.article__stats',
            'div.article-stats',
            'div.stats',
            'div.post-stats'
        ]
        
        for selector in stats_selectors:
            stats_elem = soup.select_one(selector)
            if stats_elem:
                # 浏览量
                view_elem = stats_elem.find('span', text=lambda t: t and '浏览' in t)
                if view_elem:
                    import re
                    view_text = view_elem.get_text(strip=True)
                    view_match = re.search(r'([0-9,]+)', view_text)
                    if view_match:
                        post_detail['view_count'] = int(view_match.group(1).replace(',', ''))
                
                # 回复数
                reply_elem = stats_elem.find('span', text=lambda t: t and '回复' in t)
                if reply_elem:
                    reply_text = reply_elem.get_text(strip=True)
                    reply_match = re.search(r'([0-9,]+)', reply_text)
                    if reply_match:
                        post_detail['reply_count'] = int(reply_match.group(1).replace(',', ''))
                
                # 点赞数
                like_elem = stats_elem.find('span', text=lambda t: t and '点赞' in t)
                if like_elem:
                    like_text = like_elem.get_text(strip=True)
                    like_match = re.search(r'([0-9,]+)', like_text)
                    if like_match:
                        post_detail['like_count'] = int(like_match.group(1).replace(',', ''))
                break
        
        # 查找时间
        time_selectors = [
            'div.article__meta',
            'div.article-meta',
            'div.meta',
            'span.time'
        ]
        
        for selector in time_selectors:
            time_elem = soup.select_one(selector)
            if time_elem:
                post_detail['created_at'] = time_elem.get_text(strip=True)
                break
        
        # 如果HTML解析失败，尝试API
        if not post_detail['content']:
            # 从URL中提取帖子ID
            import re
            post_id_match = re.search(r'/([0-9]+)\?', share_link)
            if post_id_match:
                post_id = post_id_match.group(1)
                api_url = f"https://xueqiu.com/statuses/show.json"
                params = {"id": post_id}
                
                try:
                    api_response = requests.get(api_url, headers=headers, params=params, timeout=10)
                    api_response.raise_for_status()
                    
                    api_data = api_response.json()
                    if isinstance(api_data, dict):
                        post_detail['title'] = api_data.get('title', '')
                        post_detail['content'] = api_data.get('text', '') or api_data.get('description', '')
                        post_detail['created_at'] = api_data.get('created_at', '')
                        post_detail['view_count'] = api_data.get('view_count', 0)
                        post_detail['reply_count'] = api_data.get('reply_count', 0)
                        post_detail['like_count'] = api_data.get('like_count', 0)
                        
                        user = api_data.get('user', {})
                        post_detail['author_name'] = user.get('screen_name', '')
                except Exception as e:
                    print(f"  API获取失败: {e}")
        
        print(f"  ✅ 成功获取详细信息")
        return post_detail
        
    except Exception as e:
        print(f"  ❌ 获取失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("完整流程：从用户UID到文章详细内容")
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
    
    # 2. 为每个帖子生成分享链接并获取详细信息
    for i, post in enumerate(posts, 1):
        print(f"\n" + "=" * 60)
        print(f"处理第 {i} 个帖子")
        print("=" * 60)
        
        # 生成分享链接
        share_link = generate_share_link(user_uid, post['id'], share_uid)
        
        # 获取详细信息
        detail = get_post_detail_from_link(share_link, cookie_str)
        
        if detail:
            # 保存详细信息
            output_file = f"post_detail_{post['id']}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(detail, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 已保存详细信息到 {output_file}")
            
            # 显示详细信息
            print("\n帖子详细信息:")
            print("=" * 60)
            print(f"标题: {detail['title']}")
            print(f"作者: {detail['author_name']}")
            print(f"时间: {detail['created_at']}")
            print(f"浏览: {detail['view_count']} | 回复: {detail['reply_count']} | 点赞: {detail['like_count']}")
            print(f"\n内容:")
            print("-" * 60)
            print(detail['content'])
            print("-" * 60)
        
        # 延迟
        if i < len(posts):
            import random
            delay = random.uniform(3, 5)
            print(f"\n等待 {delay:.1f} 秒...")
            time.sleep(delay)
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
