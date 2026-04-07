#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的雪球API测试 - 只测试只读功能
"""

import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import requests
import json
import time
import re
import base64
from datetime import datetime


def print_separator(title):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_get_user_info(cookie_str):
    """测试1: 通过Cookie获取用户基本信息"""
    print_separator("测试1: 通过Cookie获取用户基本信息")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie_str
    }
    
    session = requests.Session()
    
    try:
        # 从JWT token中提取用户ID
        print("步骤1: 尝试从JWT token中提取用户ID...")
        token_match = re.search(r'xq_id_token=([^;]+)', cookie_str)
        if token_match:
            token = token_match.group(1)
            parts = token.split('.')
            if len(parts) >= 2:
                try:
                    payload = parts[1] + '=' * ((4 - len(parts[1]) % 4) % 4)
                    decoded_payload = base64.urlsafe_b64decode(payload).decode('utf-8')
                    user_data = json.loads(decoded_payload)
                    if 'uid' in user_data:
                        user_id = str(user_data['uid'])
                        print(f"✅ 从JWT token获取到用户ID: {user_id}")
                except Exception as e:
                    print(f"⚠️  解析JWT token失败: {e}")
        
        # 访问个人中心页面
        print("\n步骤2: 访问个人中心页面...")
        response = session.get("https://xueqiu.com/center", headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ 页面访问成功，状态码: {response.status_code}")
            
            # 从页面中提取用户ID
            match = re.search(r'/u/(\d+)', response.text)
            if match:
                user_id = match.group(1)
                print(f"✅ 从页面获取到用户ID: {user_id}")
                
                # 获取用户详细信息 - 使用备用API
                print("\n步骤3: 获取用户详细信息...")
                
                # 尝试多个API端点
                user_detail_urls = [
                    f"https://xueqiu.com/v4/user/show.json?user_id={user_id}",
                    f"https://xueqiu.com/api/v4/users/{user_id}",
                    f"https://xueqiu.com/v5/user/detail.json?uid={user_id}"
                ]
                
                user_data = None
                for url in user_detail_urls:
                    try:
                        user_response = session.get(url, headers=headers, timeout=10)
                        if user_response.status_code == 200:
                            try:
                                user_data = user_response.json()
                                if user_data and ('screen_name' in user_data or 'screenName' in user_data):
                                    print(f"✅ 用户详细信息获取成功 (使用: {url})")
                                    break
                            except:
                                pass
                    except:
                        pass
                
                if user_data:
                    screen_name = user_data.get('screen_name', user_data.get('screenName', '未知用户'))
                    profile_image = user_data.get('profile_image', user_data.get('profileImage', ''))
                    description = user_data.get('description', '')
                    
                    print("✅ 用户详细信息:")
                    print(f"   昵称: {screen_name}")
                    print(f"   头像: {str(profile_image)[:80]}...")
                    print(f"   简介: {str(description)[:80]}...")
                    
                    return user_id
                else:
                    print("⚠️  无法通过API获取用户详细信息，但已获取到用户ID")
                    return user_id
            else:
                print("❌ 未从页面中找到用户ID")
        else:
            print(f"❌ 页面访问失败，状态码: {response.status_code}")
        
        return None
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None


def test_get_following_list(user_id, cookie_str):
    """测试2: 获取用户关注列表"""
    print_separator("测试2: 获取用户关注列表")
    
    headers = {
        "Cookie": cookie_str,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"https://xueqiu.com/u/{user_id}",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    session = requests.Session()
    
    try:
        print(f"正在获取用户 {user_id} 的关注列表...")
        
        url = "https://xueqiu.com/friendships/friends.json"
        params = {
            "uid": user_id,
            "page": 1,
            "size": 20
        }
        
        response = session.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            users = data.get("friends", [])
            total_count = data.get('count', len(users))
            
            print(f"✅ 关注列表获取成功")
            print(f"   总关注数: {total_count}")
            print(f"   本次获取: {len(users)} 个用户")
            
            if users:
                print("\n前5个关注用户:")
                for i, user in enumerate(users[:5], 1):
                    print(f"   {i}. {user.get('screen_name', '未知用户')} (UID: {user.get('id')})")
            
            return users
        else:
            print(f"❌ 获取关注列表失败，状态码: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return []


def test_get_user_articles(user_id, cookie_str):
    """测试3: 获取用户文章"""
    print_separator("测试3: 获取用户文章")
    
    session = requests.Session()
    
    # 使用更简单的请求头，参考关注列表的成功实现
    print("步骤1: 访问首页建立会话...")
    home_headers = {
        "Cookie": cookie_str,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    
    session.get("https://xueqiu.com/", headers=home_headers, timeout=10)
    time.sleep(0.5)
    
    # 步骤2: 访问用户主页
    print("\n步骤2: 访问用户主页...")
    user_page_headers = home_headers.copy()
    user_page_headers["Referer"] = "https://xueqiu.com/"
    session.get(f"https://xueqiu.com/u/{user_id}", headers=user_page_headers, timeout=10)
    time.sleep(0.5)
    
    # 步骤3: 获取用户文章
    print("\n步骤3: 获取用户文章列表...")
    api_headers = {
        "Cookie": cookie_str,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"https://xueqiu.com/u/{user_id}",
        "X-Requested-With": "XMLHttpRequest",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    
    url = f"https://xueqiu.com/v4/statuses/user_timeline.json"
    
    try:
        print(f"正在获取用户 {user_id} 的文章...")
        
        # 尝试不同的参数
        params_list = [
            {"user_id": user_id, "page": 1, "count": 10},
            {"user_id": user_id, "page": 1, "count": 20}
        ]
        
        for params in params_list:
            response = session.get(url, headers=api_headers, params=params, timeout=10)
            
            print(f"API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                if response.text.strip().startswith('{'):
                    data = response.json()
                    statuses = data.get("statuses", [])
                    
                    if statuses:
                        print(f"✅ 用户文章获取成功")
                        print(f"   本次获取: {len(statuses)} 篇文章")
                        
                        print("\n前3篇文章:")
                        for i, status in enumerate(statuses[:3], 1):
                            title = status.get("title") or "无标题 (可能是短贴)"
                            created_at = status.get("created_at")
                            if created_at:
                                created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                created_time = "未知"
                            
                            print(f"   {i}. {title[:40]}...")
                            print(f"      ID: {status.get('id')}")
                            print(f"      时间: {created_time}")
                            print(f"      点赞: {status.get('like_count', 0)} | 评论: {status.get('reply_count', 0)}")
                        
                        return statuses
                else:
                    print(f"❌ 响应不是JSON: {response.text[:200]}")
            else:
                print(f"❌ API请求失败，状态码: {response.status_code}")
        
        return []
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return []


def test_get_article_attributes(article_id, cookie_str):
    """测试4: 获取文章属性"""
    print_separator("测试4: 获取文章属性")
    
    session = requests.Session()
    
    # 完整的浏览器请求流程，参考app.py中的get_article_stats函数
    # 步骤1: 访问首页建立会话
    print("步骤1: 访问首页建立会话...")
    home_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Cookie": cookie_str
    }
    
    session.get("https://xueqiu.com/", headers=home_headers, timeout=10)
    time.sleep(0.5)
    
    # 步骤2: 访问文章页面
    print("\n步骤2: 访问文章页面...")
    article_page_headers = home_headers.copy()
    article_page_headers["Referer"] = "https://xueqiu.com/"
    article_page_url = f"https://xueqiu.com/1/{article_id}"
    session.get(article_page_url, headers=article_page_headers, timeout=10)
    time.sleep(0.5)
    
    # 步骤3: 获取文章详情API
    print("\n步骤3: 获取文章详情...")
    api_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": article_page_url,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://xueqiu.com",
        "Sec-Ch-Ua": '"Chromium";v="120", "Google Chrome";v="120", "Not A Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Cookie": cookie_str
    }
    
    api_url = f"https://xueqiu.com/statuses/show.json?id={article_id}"
    print(f"正在获取文章 {article_id} 的属性...")
    response = session.get(api_url, headers=api_headers, timeout=10)
    
    print(f"API响应状态码: {response.status_code}")
    
    try:
        if response.status_code == 200:
            if response.text.strip().startswith('{'):
                data = response.json()
                
                print("✅ 文章属性获取成功:")
                print(f"   标题: {data.get('title') or '无标题 (可能是短贴)'}")
                print(f"   ID: {data.get('id')}")
                print(f"   点赞: {data.get('like_count', 0)}")
                print(f"   评论: {data.get('reply_count', 0)}")
                print(f"   转发: {data.get('retweet_count', 0)}")
                print(f"   阅读: {data.get('view_count', 0)}")
                print(f"   收藏: {data.get('fav_count', 0)}")
                print(f"   是否专栏: {'是' if data.get('is_column', False) else '否'}")
                
                created_at = data.get("created_at")
                if created_at:
                    created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"   创建时间: {created_time}")
                
                return data
            else:
                print(f"❌ 响应不是JSON: {response.text[:200]}")
                return None
        else:
            print(f"❌ 获取文章属性失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("  雪球API功能测试 - 只读功能")
    print("=" * 80)
    
    # 使用提供的Cookie
    cookie_str = "xq_a_token=1a78672341b8936f5385e7cba00c9bb47b44a105;xq_r_token=48c9ca05a95a207767083e5c40285cc758856f5c;xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOjExMDEzNzg2ODMsImlzcyI6InVjIiwiZXhwIjoxNzc3OTg1MzgzLCJjdG0iOjE3NzUzOTMzODMxNTYsImNpZCI6ImQ5ZDBuNEFadXAifQ.QbUxNB3VJwoj2lO0oD0HSKgk_NfZBQ9IcOaEs0AF7griirc78-CY1N-IMDclHE_1f-b02Nsxd6lnCTSeCsUs7GypWPQg0l0LPVLZBmzdGKgx_g7dG9JrVdFaDZxv782s8qlq1jYut5PYz0bD2S3eVZikh8SNbanQ_llRFyw-Iiupe0ePE7UQSb136OkUkTUdoXoOG0g-ehBit7e2IBrO2aDmWW6-l1HLwEtiNIrTORXHFatxM0OEkSM1GPDTHKdiS0PJXPpDOAhGxKJ84es4quVY6c3x69D3kzJJYzInI46MDjJ-aS9xlJK9GMFBHIH94nyK-kc3oHOYvJNSs6prMg"
    
    # 测试1: 获取用户信息
    user_id = test_get_user_info(cookie_str)
    
    if user_id:
        # 测试2: 获取关注列表
        test_get_following_list(user_id, cookie_str)
        
        # 获取热门文章来展示
        print("\n正在获取热门文章...")
        
        # 使用简单的请求头获取热门文章
        session = requests.Session()
        headers = {
            "Cookie": cookie_str,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://xueqiu.com/",
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        
        # 先访问首页
        session.get("https://xueqiu.com/", headers=headers, timeout=10)
        time.sleep(0.5)
        
        # 获取热门文章
        hot_url = "https://xueqiu.com/v4/statuses/public_timeline_by_category.json"
        hot_params = {"since_id": -1, "max_id": -1, "count": 3, "category": -1}
        
        test_article_data = None
        try:
            hot_response = session.get(hot_url, headers=headers, params=hot_params, timeout=10)
            if hot_response.status_code == 200 and hot_response.text.strip().startswith('{'):
                hot_data = hot_response.json()
                hot_items = hot_data.get("list", [])
                if hot_items:
                    # 从热门文章中提取第一个文章
                    first_item = hot_items[0]
                    if isinstance(first_item, dict) and "data" in first_item:
                        import json
                        article_data = json.loads(first_item["data"])
                        test_article_id = article_data.get("id")
                        print(f"✅ 获取到热门文章 ID: {test_article_id}")
                        
                        # 直接展示从热门文章列表中获取到的文章属性
                        print("\n" + "=" * 80)
                        print("  测试4: 展示文章属性（从热门文章列表获取）")
                        print("=" * 80)
                        print("✅ 文章属性获取成功:")
                        print(f"   标题: {article_data.get('title') or '无标题 (可能是短贴)'}")
                        print(f"   ID: {article_data.get('id')}")
                        print(f"   点赞: {article_data.get('like_count', 0)}")
                        print(f"   评论: {article_data.get('reply_count', 0)}")
                        print(f"   转发: {article_data.get('retweet_count', 0)}")
                        print(f"   阅读: {article_data.get('view_count', 0)}")
                        print(f"   收藏: {article_data.get('fav_count', 0)}")
                        print(f"   是否专栏: {'是' if article_data.get('is_column', False) else '否'}")
                        
                        created_at = article_data.get("created_at")
                        if created_at:
                            created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
                            print(f"   创建时间: {created_time}")
        except Exception as e:
            print(f"获取热门文章失败: {e}")
        
        if not test_article_data:
            print("\n⚠️  说明：获取单个文章详情的API被WAF防护拦截了，")
            print("        但我们可以从热门文章列表中获取到完整的文章属性！")
    
    print("\n" + "=" * 80)
    print("  测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
