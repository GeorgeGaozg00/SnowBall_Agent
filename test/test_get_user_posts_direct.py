#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过用户URL直接获取最近帖子（不需要浏览器模拟）
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

def extract_user_uid_from_url(url):
    """从URL中提取用户UID"""
    import re
    match = re.search(r'/u/([0-9]+)', url)
    if match:
        return match.group(1)
    return None

def get_user_posts_direct(user_uid, cookie_str, max_posts=10):
    """
    直接通过HTTP请求获取用户最近的帖子
    """
    print(f"\n" + "=" * 60)
    print(f"获取用户 {user_uid} 的最近 {max_posts} 个帖子")
    print("=" * 60)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": f"https://xueqiu.com/u/{user_uid}",
        "Cookie": cookie_str
    }
    
    all_posts = []
    
    # 方法1: 直接访问用户主页，解析HTML
    print("\n1. 访问用户主页...")
    user_url = f"https://xueqiu.com/u/{user_uid}"
    
    try:
        response = requests.get(user_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print("✅ 成功访问用户主页")
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找包含帖子数据的script标签
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and 'SNB.cube' in script.string:
                print("  找到数据脚本")
                # 提取JSON数据
                import re
                match = re.search(r'SNB\.cube\s*=\s*(\{.*?\});', script.string, re.DOTALL)
                if match:
                    cube_data = match.group(1)
                    try:
                        # 处理可能的JavaScript语法
                        cube_data = cube_data.replace('undefined', 'null')
                        cube_data = cube_data.replace('true', 'true')
                        cube_data = cube_data.replace('false', 'false')
                        
                        data = json.loads(cube_data)
                        
                        # 查找帖子数据
                        if 'data' in data:
                            data_content = data['data']
                            if isinstance(data_content, dict):
                                # 检查不同的数据结构
                                if 'statuses' in data_content:
                                    statuses = data_content['statuses']
                                    print(f"  找到 {len(statuses)} 条帖子")
                                    for status in statuses[:max_posts]:
                                        if isinstance(status, dict):
                                            post_data = {
                                                'id': status.get('id'),
                                                'title': status.get('title', ''),
                                                'description': status.get('description', ''),
                                                'text': status.get('text', ''),
                                                'created_at': status.get('created_at'),
                                                'view_count': status.get('view_count', 0),
                                                'reply_count': status.get('reply_count', 0),
                                                'like_count': status.get('like_count', 0)
                                            }
                                            all_posts.append(post_data)
                            
                        if all_posts:
                            break
                    except Exception as e:
                        print(f"  解析JSON失败: {e}")
    except Exception as e:
        print(f"  访问主页失败: {e}")
    
    # 方法2: 如果方法1失败，尝试API
    if not all_posts:
        print("\n2. 尝试API获取...")
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
                print(f"  API请求失败: {e}")
                break
    
    # 方法3: 尝试另一个API端点
    if not all_posts:
        print("\n3. 尝试另一个API...")
        api_url = "https://xueqiu.com/v4/statuses/user_timeline.json"
        params = {
            "user_id": user_uid,
            "page": 1,
            "count": max_posts,
            "max_id": 0
        }
        
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            statuses = data.get('statuses', [])
            
            for status in statuses:
                if isinstance(status, dict):
                    post_data = {
                        'id': status.get('id'),
                        'title': status.get('title', ''),
                        'description': status.get('description', ''),
                        'text': status.get('text', ''),
                        'created_at': status.get('created_at'),
                        'view_count': status.get('view_count', 0),
                        'reply_count': status.get('reply_count', 0),
                        'like_count': status.get('like_count', 0)
                    }
                    all_posts.append(post_data)
        except Exception as e:
            print(f"  备用API请求失败: {e}")
    
    # 处理结果
    all_posts = all_posts[:max_posts]
    
    print(f"\n✅ 成功获取 {len(all_posts)} 个帖子")
    
    # 保存数据
    if all_posts:
        output_file = f'user_{user_uid}_posts_direct.json'
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
            if post['created_at']:
                try:
                    print(f"   时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(post['created_at']/1000))}")
                except:
                    pass
            print(f"   浏览: {post['view_count']} | 回复: {post['reply_count']} | 点赞: {post['like_count']}")
    
    return all_posts

def main():
    """主函数"""
    print("=" * 60)
    print("通过URL直接获取用户最近帖子")
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
    
    # 输入用户URL或UID
    user_input = input("请输入用户URL或UID: ").strip()
    if not user_input:
        print("错误: 请输入有效的用户URL或UID")
        return
    
    # 提取UID
    if 'xueqiu.com' in user_input:
        user_uid = extract_user_uid_from_url(user_input)
        if not user_uid:
            print("错误: 无法从URL中提取UID")
            return
    else:
        user_uid = user_input
    
    # 输入要获取的帖子数量
    max_posts = input("请输入要获取的帖子数量（默认10）: ").strip()
    max_posts = int(max_posts) if max_posts.isdigit() else 10
    max_posts = min(max_posts, 50)  # 最多50个
    
    # 获取帖子
    get_user_posts_direct(user_uid, cookie_str, max_posts)

if __name__ == "__main__":
    main()
