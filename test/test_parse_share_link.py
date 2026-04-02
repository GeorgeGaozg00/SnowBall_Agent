#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析雪球分享链接并获取帖子详细信息
"""

import json
import time
import re
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

def parse_share_link(link):
    """
    解析分享链接，提取作者UID、帖子ID、分享者UID
    """
    print(f"\n解析分享链接: {link}")
    
    # 解析URL结构
    pattern = r'https://xueqiu\.com/(\d+)/(\d+)\?.*share_uid=(\d+)'  # 带share_uid的格式
    match = re.match(pattern, link)
    
    if not match:
        # 尝试不带share_uid的格式
        pattern2 = r'https://xueqiu\.com/(\d+)/(\d+)'  
        match = re.match(pattern2, link)
        if match:
            author_uid = match.group(1)
            post_id = match.group(2)
            share_uid = None
        else:
            print("  ❌ 无效的雪球链接")
            return None
    else:
        author_uid = match.group(1)
        post_id = match.group(2)
        share_uid = match.group(3)
    
    result = {
        'author_uid': author_uid,
        'post_id': post_id,
        'share_uid': share_uid
    }
    
    print(f"  ✅ 解析成功")
    print(f"  作者UID: {author_uid}")
    print(f"  帖子ID: {post_id}")
    if share_uid:
        print(f"  分享者UID: {share_uid}")
    
    return result

def get_post_detail(post_id, cookie_str):
    """
    获取帖子详细信息
    """
    print(f"\n获取帖子 {post_id} 的详细信息...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": f"https://xueqiu.com/query/query?code={post_id}",
        "Cookie": cookie_str
    }
    
    # 访问帖子页面
    post_url = f"https://xueqiu.com/query/query?code={post_id}"
    
    try:
        response = requests.get(post_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取帖子信息
        post_detail = {
            'id': post_id,
            'title': '',
            'content': '',
            'created_at': '',
            'view_count': 0,
            'reply_count': 0,
            'like_count': 0,
            'author_name': '',
            'author_uid': ''
        }
        
        # 查找标题
        title_elem = soup.find('h1', class_='article__title')
        if not title_elem:
            title_elem = soup.find('h2', class_='title')
        if not title_elem:
            title_elem = soup.find('div', class_='article-title')
        if title_elem:
            post_detail['title'] = title_elem.get_text(strip=True)
        
        # 查找内容
        content_elem = soup.find('div', class_='article__content')
        if not content_elem:
            content_elem = soup.find('div', class_='article-content')
        if not content_elem:
            content_elem = soup.find('div', class_='content')
        if content_elem:
            post_detail['content'] = content_elem.get_text(separator='\n', strip=True)
        
        # 查找作者信息
        author_elem = soup.find('div', class_='article__author')
        if not author_elem:
            author_elem = soup.find('div', class_='user-info')
        if author_elem:
            name_elem = author_elem.find('a', class_='user-name')
            if not name_elem:
                name_elem = author_elem.find('span', class_='name')
            if name_elem:
                post_detail['author_name'] = name_elem.get_text(strip=True)
        
        # 查找统计信息
        stats_elem = soup.find('div', class_='article__stats')
        if not stats_elem:
            stats_elem = soup.find('div', class_='article-stats')
        if stats_elem:
            # 浏览量
            view_elem = stats_elem.find('span', class_='view-count')
            if not view_elem:
                view_elem = stats_elem.find('span', text=re.compile('浏览'))
            if view_elem:
                view_text = view_elem.get_text(strip=True)
                view_match = re.search(r'([0-9,]+)', view_text)
                if view_match:
                    post_detail['view_count'] = int(view_match.group(1).replace(',', ''))
            
            # 回复数
            reply_elem = stats_elem.find('span', class_='reply-count')
            if not reply_elem:
                reply_elem = stats_elem.find('span', text=re.compile('回复'))
            if reply_elem:
                reply_text = reply_elem.get_text(strip=True)
                reply_match = re.search(r'([0-9,]+)', reply_text)
                if reply_match:
                    post_detail['reply_count'] = int(reply_match.group(1).replace(',', ''))
            
            # 点赞数
            like_elem = stats_elem.find('span', class_='like-count')
            if not like_elem:
                like_elem = stats_elem.find('span', text=re.compile('点赞'))
            if like_elem:
                like_text = like_elem.get_text(strip=True)
                like_match = re.search(r'([0-9,]+)', like_text)
                if like_match:
                    post_detail['like_count'] = int(like_match.group(1).replace(',', ''))
        
        # 查找时间
        time_elem = soup.find('div', class_='article__meta')
        if not time_elem:
            time_elem = soup.find('div', class_='article-meta')
        if time_elem:
            time_text = time_elem.get_text(strip=True)
            post_detail['created_at'] = time_text
        
        # 如果HTML解析失败，尝试API
        if not post_detail['content']:
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
                    post_detail['author_uid'] = user.get('id', '')
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
    print("解析雪球分享链接并获取帖子信息")
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
    
    # 输入分享链接
    share_link = input("请输入雪球分享链接: ").strip()
    if not share_link:
        print("错误: 请输入有效的分享链接")
        return
    
    # 解析链接
    parsed_data = parse_share_link(share_link)
    if not parsed_data:
        return
    
    # 获取帖子详细信息
    post_detail = get_post_detail(parsed_data['post_id'], cookie_str)
    
    if post_detail:
        # 保存详细信息
        output_file = f"post_detail_{parsed_data['post_id']}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(post_detail, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 已保存详细信息到 {output_file}")
        
        # 显示详细信息
        print("\n帖子详细信息:")
        print("=" * 60)
        print(f"ID: {post_detail['id']}")
        print(f"标题: {post_detail['title']}")
        print(f"作者: {post_detail['author_name']} (UID: {post_detail['author_uid']})")
        print(f"时间: {post_detail['created_at']}")
        print(f"浏览: {post_detail['view_count']} | 回复: {post_detail['reply_count']} | 点赞: {post_detail['like_count']}")
        print(f"\n内容:")
        print("-" * 60)
        print(post_detail['content'])
        print("-" * 60)
    
    print("\n完成！")

if __name__ == "__main__":
    main()
