#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试程序：获取雪球用户文章列表（包含完整内容和悬赏/打赏信息）
测试UID: 8152922548
"""

import requests
import json
import os
from datetime import datetime


def parse_article_reward(art):
    """
    解析文章悬赏/打赏信息
    
    Args:
        art: 文章数据字典
    
    Returns:
        悬赏/打赏信息字典
    """
    # 1. 检查是否有悬赏（offer字段）
    offer = art.get("offer")
    
    if offer and isinstance(offer, dict):
        # 有悬赏信息
        amount = offer.get("amount", 0)  # 单位：分
        balance = offer.get("balance", 0)  # 剩余金额（分）
        state = offer.get("state", "")
        offer_type = offer.get("type", "")
        desc = offer.get("desc", "")
        due_time = offer.get("due_time", 0)
        
        # 转换截止时间
        if due_time:
            due_time_str = datetime.fromtimestamp(due_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
        else:
            due_time_str = "未知"
        
        # 计算已分配金额
        used_amount = amount - balance
        
        return {
            "类型": "悬赏",
            "是否开启": True,
            "状态": "进行中" if state == "NORMAL" else state,
            "悬赏类型": offer_type,
            "总金额(元)": round(amount / 100, 2),
            "剩余金额(元)": round(balance / 100, 2),
            "已分配(元)": round(used_amount / 100, 2),
            "描述": desc,
            "截止时间": due_time_str
        }
    
    # 2. 检查传统打赏（reward字段）
    is_reward_enabled = art.get("can_reward", False)
    reward_count = art.get("reward_count", 0)
    reward_user_count = art.get("reward_user_count", 0)
    reward_amount = art.get("reward_amount", 0)
    
    if is_reward_enabled:
        if reward_count > 0:
            status_text = f"打赏中 (已有 {reward_count} 人打赏)"
        else:
            status_text = "已开启但无人打赏"
        
        return {
            "类型": "打赏",
            "是否开启": True,
            "状态": status_text,
            "打赏人数": reward_count,
            "打赏用户人数": reward_user_count,
            "累计金额(元)": round(reward_amount / 100, 2) if reward_amount > 0 else 0
        }
    
    # 3. 未开启任何打赏/悬赏
    return {
        "类型": "无",
        "是否开启": False,
        "状态": "未开启打赏/悬赏"
    }


def get_xueqiu_articles(uid, count=10):
    """
    获取雪球用户的文章列表
    
    Args:
        uid: 用户ID
        count: 获取文章数量
    
    Returns:
        文章列表或错误信息
    """
    # 从配置文件读取cookie
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'config.json')
    cookie = ""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            cookie = config.get('xueQiuCookie', '')
    except Exception as e:
        print(f"读取配置文件失败: {e}")
    
    # 初始化 Session
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://xueqiu.com/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # 如果有cookie，添加到headers
    if cookie:
        headers["Cookie"] = cookie
        print("使用配置文件中的Cookie")
    
    # 先访问首页建立会话
    print("正在访问雪球首页建立会话...")
    home_response = session.get("https://xueqiu.com/", headers=headers)
    print(f"首页访问状态码: {home_response.status_code}")
    
    # 构造获取文章列表的API URL
    api_url = f"https://xueqiu.com/statuses/user_timeline.json?user_id={uid}&page=1&type=edit"
    
    print(f"\n正在请求API: {api_url}")
    
    try:
        response = session.get(api_url, headers=headers)
        response.raise_for_status()
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容类型: {response.headers.get('Content-Type', 'unknown')}")
        
        # 检查是否是JSON响应
        if 'application/json' in response.headers.get('Content-Type', ''):
            data = response.json()
            articles = data.get("statuses", [])[:count]
            
            print(f"\n获取到 {len(articles)} 篇文章\n")
            
            result = []
            for art in articles:
                # 转换时间戳为可读格式
                created_at = art.get("created_at")
                if created_at:
                    created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    created_time = "未知"
                
                # 获取完整内容（优先使用text字段，如果没有则使用description）
                content = art.get("text", "")
                if not content:
                    content = art.get("description", "")
                
                # 解析悬赏/打赏信息
                reward_info = parse_article_reward(art)
                
                article_info = {
                    "ID": art.get("id"),
                    "标题": art.get("title") or "无标题 (可能是短贴)",
                    "内容": content,
                    "属性": {
                        "点赞数": art.get("like_count", 0),
                        "评论数": art.get("reply_count", 0),
                        "转发数": art.get("retweet_count", 0),
                        "阅读数": art.get("view_count", 0),
                        "收藏数": art.get("fav_count", 0),
                        "是否专栏": "是" if art.get("is_column", False) else "否",
                        "是否原创声明": "是" if art.get("is_original_declare", False) else "否",
                        "创建时间": created_time
                    },
                    "打赏/悬赏信息": reward_info
                }
                result.append(article_info)
            
            return result
        else:
            print(f"\n响应内容前500字符:\n{response.text[:500]}")
            return f"API返回非JSON格式，可能是被WAF拦截或需要登录"

    except requests.exceptions.RequestException as e:
        return f"网络请求错误: {e}"
    except json.JSONDecodeError as e:
        return f"JSON解析错误: {e}"
    except Exception as e:
        return f"发生错误: {e}"


def print_articles(articles):
    """打印文章列表"""
    if isinstance(articles, list):
        print("\n" + "=" * 80)
        print(f"用户文章列表 (共 {len(articles)} 篇)")
        print("=" * 80)
        
        for i, item in enumerate(articles, 1):
            print(f"\n【文章 {i}】")
            print(f"ID: {item['ID']}")
            print(f"标题: {item['标题']}")
            
            # 显示完整内容（限制长度）
            content = item['内容'] or ""
            if len(content) > 300:
                content = content[:300] + "...\n(内容已截断，完整内容较长)"
            print(f"\n内容:\n{content}")
            
            # 显示属性
            print(f"\n属性:")
            attrs = item['属性']
            for key, value in attrs.items():
                print(f"  {key}: {value}")
            
            # 显示打赏/悬赏信息
            print(f"\n打赏/悬赏信息:")
            reward = item['打赏/悬赏信息']
            for key, value in reward.items():
                print(f"  {key}: {value}")
            
            print("-" * 80)
    else:
        print(f"错误: {articles}")


if __name__ == "__main__":
    # 测试UID
    user_uid = "8152922548"
    
    print(f"开始获取用户 {user_uid} 的文章列表...\n")
    
    # 获取文章（包含完整内容和悬赏/打赏信息）
    articles = get_xueqiu_articles(user_uid, count=5)
    
    # 打印结果
    print_articles(articles)
