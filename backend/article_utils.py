#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章工具类：用于获取文章的完整信息和属性
"""

import requests
import json
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


def get_article_from_url(url, cookie_str):
    """
    从分享URL获取文章的标题和内容
    
    Args:
        url: 文章分享链接
        cookie_str: Cookie字符串
    
    Returns:
        文章信息字典，包含所有属性
    """
    try:
        # 从URL中提取文章ID
        # URL格式: https://xueqiu.com/{uid}/{post_id}?scene=1036&share_uid={share_uid}
        parts = url.split('/')
        if len(parts) >= 2:
            post_id = parts[3].split('?')[0]
        else:
            return None
        
        # 获取文章详情
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://xueqiu.com/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": cookie_str
        }
        
        # 先访问首页建立会话
        session = requests.Session()
        session.get("https://xueqiu.com/", headers=headers)
        
        # 获取文章详情
        api_url = f"https://xueqiu.com/statuses/show.json?id={post_id}"
        response = session.get(api_url, headers=headers)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        # 解析文章信息
        created_at = data.get("created_at")
        if created_at:
            created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
        else:
            created_time = "未知"
        
        # 获取完整内容
        content = data.get("text", "")
        if not content:
            content = data.get("description", "")
        
        # 解析打赏/悬赏信息
        reward_info = parse_article_reward(data)
        
        article_info = {
            "ID": data.get("id"),
            "标题": data.get("title") or "无标题 (可能是短贴)",
            "内容": content,
            "属性": {
                "点赞数": data.get("like_count", 0),
                "评论数": data.get("reply_count", 0),
                "转发数": data.get("retweet_count", 0),
                "阅读数": data.get("view_count", 0),
                "收藏数": data.get("fav_count", 0),
                "是否专栏": "是" if data.get("is_column", False) else "否",
                "是否原创声明": "是" if data.get("is_original_declare", False) else "否",
                "创建时间": created_time
            },
            "打赏/悬赏信息": reward_info
        }
        
        return article_info
        
    except Exception as e:
        print(f"从URL获取文章失败: {e}")
        return None


def get_article_full_attributes(art):
    """
    从文章数据中提取完整属性
    
    Args:
        art: 文章数据字典
    
    Returns:
        包含所有属性的文章信息字典
    """
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
    
    # 解析打赏/悬赏信息
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
    
    return article_info
