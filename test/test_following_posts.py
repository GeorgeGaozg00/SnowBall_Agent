#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试程序：获取雪球首页"关注"标签下的所有帖子
"""

import requests
import json
import time
import random

# 从环境变量或配置文件读取Cookie
XUEQIU_COOKIE = "acw_tc=2760820517451024281765153e7c9b0a9e0f0f3e2e3c5e3e3e3e3e3e3e3e3e3; xq_a_token=7e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3; xq_r_token=3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e; xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1aWQiOjU2Nzg1OTczMjYsImV4cCI6MTc3NTYwNjI4M30.abc123; u=5678597326; device_id=3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e3c1e; Hm_lvt_1db88642e346389874251b5a1eded6e3=1745102428; Hm_lpvt_1db88642e346389874251b5a1eded6e3=1745102428"

# 请求头
headers = {
    "Cookie": XUEQIU_COOKIE,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://xueqiu.com",
    "X-Requested-With": "XMLHttpRequest",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

def get_following_posts(page=1, count=20):
    """
    获取关注页面（首页-关注标签）的帖子列表
    
    这个API端点获取的是用户关注的人发布的帖子
    """
    print(f"\n获取关注页面的帖子（第 {page} 页）...")
    
    # 尝试多个API端点
    api_endpoints = [
        # 方法1：使用timeline API
        {
            "url": "https://xueqiu.com/v4/statuses/public_timeline_by_category.json",
            "params": {
                "since_id": -1,
                "max_id": -1,
                "count": count,
                "category": -1,
                "page": page,
            }
        },
        # 方法2：使用home timeline API
        {
            "url": "https://xueqiu.com/v4/statuses/home_timeline.json",
            "params": {
                "page": page,
                "count": count,
            }
        },
        # 方法3：使用friendships timeline API
        {
            "url": "https://xueqiu.com/v4/statuses/friendships_timeline.json",
            "params": {
                "page": page,
                "count": count,
            }
        },
        # 方法4：使用关注动态API
        {
            "url": "https://xueqiu.com/friendships/dynamics.json",
            "params": {
                "page": page,
                "count": count,
            }
        }
    ]
    
    for i, endpoint in enumerate(api_endpoints, 1):
        print(f"\n尝试方法 {i}: {endpoint['url']}")
        
        try:
            response = requests.get(
                endpoint["url"], 
                headers=headers, 
                params=endpoint["params"], 
                timeout=10
            )
            print(f"请求URL: {response.url}")
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # 保存响应数据以便分析
                with open(f"following_posts_page{page}_method{i}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ 方法 {i} 成功！")
                
                # 尝试提取帖子列表（不同API可能有不同的字段名）
                posts = None
                if "list" in data:
                    posts = data.get("list", [])
                elif "statuses" in data:
                    posts = data.get("statuses", [])
                elif "data" in data and isinstance(data["data"], list):
                    posts = data.get("data", [])
                
                if posts is not None:
                    print(f"✅ 成功获取 {len(posts)} 条帖子")
                    
                    # 显示帖子信息
                    for j, post in enumerate(posts[:3], 1):
                        # 不同API的数据结构可能不同
                        if isinstance(post, dict):
                            if "data" in post:
                                status = post.get("data", {})
                            else:
                                status = post
                            
                            user = status.get("user", {}) if isinstance(status, dict) else {}
                            user_name = user.get("screen_name", "未知用户") if isinstance(user, dict) else "未知用户"
                            title = status.get("title", "") if isinstance(status, dict) else ""
                            description = status.get("description", "")[:100] if isinstance(status, dict) else ""
                            
                            print(f"\n  帖子 {j}:")
                            print(f"    作者: {user_name}")
                            print(f"    标题: {title}")
                            print(f"    内容: {description}...")
                    
                    return data
            else:
                print(f"❌ 方法 {i} 失败: {response.status_code}")
                print(f"响应内容: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ 方法 {i} 异常: {str(e)}")
    
    print("\n❌ 所有方法都失败了")
    return None

def get_all_following_posts(max_pages=10):
    """
    获取所有关注页面的帖子（多页）
    """
    print("=" * 60)
    print("开始获取关注页面的所有帖子")
    print("=" * 60)
    
    all_posts = []
    
    for page in range(1, max_pages + 1):
        print(f"\n{'='*60}")
        print(f"正在获取第 {page} 页...")
        print(f"{'='*60}")
        
        data = get_following_posts(page=page, count=20)
        
        if data is None:
            print(f"❌ 第 {page} 页获取失败，停止获取")
            break
        
        posts = data.get("list", [])
        
        if not posts:
            print(f"✅ 第 {page} 页没有更多帖子，停止获取")
            break
        
        all_posts.extend(posts)
        
        # 检查是否还有更多页面
        next_max_id = data.get("next_max_id", -1)
        if next_max_id == -1:
            print(f"✅ 已到达最后一页")
            break
        
        # 添加随机延迟，模拟人类操作
        delay = random.uniform(2, 4)
        print(f"\n等待 {delay:.2f} 秒后继续...")
        time.sleep(delay)
    
    # 保存所有帖子
    print(f"\n{'='*60}")
    print(f"✅ 总共获取到 {len(all_posts)} 条帖子")
    print(f"{'='*60}")
    
    with open("all_following_posts.json", "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已保存所有帖子到 all_following_posts.json")
    
    return all_posts

def analyze_posts(posts):
    """
    分析帖子数据，提取关键信息
    """
    print("\n" + "=" * 60)
    print("帖子分析")
    print("=" * 60)
    
    # 统计每个作者的帖子数量
    author_stats = {}
    
    for post in posts:
        status = post.get("data", {})
        user = status.get("user", {})
        user_name = user.get("screen_name", "未知用户")
        user_id = user.get("id", "未知ID")
        
        if user_name not in author_stats:
            author_stats[user_name] = {
                "count": 0,
                "user_id": user_id
            }
        author_stats[user_name]["count"] += 1
    
    # 按帖子数量排序
    sorted_authors = sorted(author_stats.items(), key=lambda x: x[1]["count"], reverse=True)
    
    print("\n作者统计（按帖子数量排序）：")
    for i, (author, stats) in enumerate(sorted_authors[:20], 1):
        print(f"{i:3d}. {author:20s} - {stats['count']:3d} 条帖子 (UID: {stats['user_id']})")
    
    # 保存统计结果
    with open("following_posts_analysis.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_posts": len(posts),
            "total_authors": len(author_stats),
            "author_stats": sorted_authors
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 已保存分析结果到 following_posts_analysis.json")

def main():
    """
    主函数
    """
    print("=" * 60)
    print("雪球首页关注页面帖子获取测试程序")
    print("=" * 60)
    
    print("\n请选择运行模式:")
    print("1. 获取单页帖子（第1页）")
    print("2. 获取多页帖子（自动翻页）")
    print("3. 分析已保存的帖子数据")
    
    choice = input("\n请输入选项（1/2/3）: ").strip()
    
    if choice == "1":
        # 获取单页帖子
        data = get_following_posts(page=1, count=20)
        if data:
            posts = data.get("list", [])
            print(f"\n✅ 成功获取 {len(posts)} 条帖子")
            
            # 显示所有帖子
            print("\n" + "=" * 60)
            print("帖子列表：")
            print("=" * 60)
            
            for i, post in enumerate(posts, 1):
                status = post.get("data", {})
                user = status.get("user", {})
                
                user_name = user.get("screen_name", "未知用户")
                title = status.get("title", "")
                description = status.get("description", "")[:150]
                created_at = status.get("created_at", 0)
                
                # 转换时间戳
                if created_at:
                    from datetime import datetime
                    created_time = datetime.fromtimestamp(created_at / 1000).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    created_time = "未知时间"
                
                print(f"\n{i}. 作者: {user_name}")
                print(f"   时间: {created_time}")
                print(f"   标题: {title}")
                print(f"   内容: {description}...")
                print("-" * 60)
    
    elif choice == "2":
        # 获取多页帖子
        max_pages = input("请输入要获取的页数（默认10页）: ").strip()
        max_pages = int(max_pages) if max_pages.isdigit() else 10
        
        posts = get_all_following_posts(max_pages=max_pages)
        
        if posts:
            analyze_posts(posts)
    
    elif choice == "3":
        # 分析已保存的数据
        try:
            with open("all_following_posts.json", "r", encoding="utf-8") as f:
                posts = json.load(f)
            
            print(f"✅ 成功加载 {len(posts)} 条帖子")
            analyze_posts(posts)
        except FileNotFoundError:
            print("❌ 未找到已保存的帖子数据，请先运行选项2获取帖子")
    
    else:
        print("❌ 无效的选项")

if __name__ == "__main__":
    main()
