#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试程序：检查文章382305373的所有字段，找出打赏相关字段
"""

import requests
import json
import os


def check_article_fields():
    """检查文章382305373的所有字段"""
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
    
    if cookie:
        headers["Cookie"] = cookie
    
    # 先访问首页
    session.get("https://xueqiu.com/", headers=headers)
    
    # 获取用户8152922548的文章列表
    uid = "8152922548"
    api_url = f"https://xueqiu.com/statuses/user_timeline.json?user_id={uid}&page=1&type=edit"
    
    response = session.get(api_url, headers=headers)
    data = response.json()
    articles = data.get("statuses", [])
    
    # 找到文章382305373
    target_article = None
    for art in articles:
        if art.get("id") == 382305373:
            target_article = art
            break
    
    if target_article:
        print("=" * 80)
        print("文章 382305373 的所有字段:")
        print("=" * 80)
        
        # 打印所有字段
        for key, value in sorted(target_article.items()):
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            print(f"  {key}: {value_str}")
        
        # 检查可能的打赏相关字段
        print("\n" + "=" * 80)
        print("可能的打赏/悬赏相关字段:")
        print("=" * 80)
        
        reward_keywords = ['reward', 'bonus', 'offer', 'order', 'paid', 'donate', '悬赏', '打赏', '红包']
        for key, value in target_article.items():
            if any(keyword in key.lower() for keyword in reward_keywords):
                print(f"  ✓ {key}: {value}")
        
        # 特别检查offer字段（截图显示有悬赏）
        print("\n" + "=" * 80)
        print("特别检查 offer 字段:")
        print("=" * 80)
        offer = target_article.get("offer")
        if offer:
            print(f"offer: {json.dumps(offer, ensure_ascii=False, indent=2)}")
        else:
            print("offer: None")
            
        # 检查其他可能相关的字段
        print("\n" + "=" * 80)
        print("其他可能相关的字段:")
        print("=" * 80)
        for key in ['can_reward', 'reward', 'reward_count', 'reward_amount', 'reward_user_count', 
                    'donate_count', 'donate_snowcoin', 'bonus_screen_name', 'is_bonus']:
            if key in target_article:
                print(f"  {key}: {target_article[key]}")
    else:
        print("未找到文章 382305373")


if __name__ == "__main__":
    check_article_fields()
