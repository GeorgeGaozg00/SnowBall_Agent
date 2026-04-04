#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试程序：检查文章列表API返回的字段
"""

import requests
import json
import os

def check_article_fields():
    """检查文章列表API返回的所有字段"""
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
    
    # 获取文章列表
    uid = "7437424816"
    api_url = f"https://xueqiu.com/statuses/user_timeline.json?user_id={uid}&page=1&type=edit"
    
    response = session.get(api_url, headers=headers)
    data = response.json()
    articles = data.get("statuses", [])
    
    if articles:
        # 打印第一篇文章的所有字段
        first_article = articles[0]
        print("第一篇文章的所有字段:")
        print("=" * 80)
        for key, value in sorted(first_article.items()):
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            print(f"  {key}: {value_str}")
        
        # 检查是否有打赏相关字段
        print("\n" + "=" * 80)
        print("检查打赏相关字段:")
        reward_fields = [k for k in first_article.keys() if 'reward' in k.lower()]
        if reward_fields:
            for field in reward_fields:
                print(f"  ✓ {field}: {first_article[field]}")
        else:
            print("  未找到打赏相关字段")
        
        # 检查是否有完整内容字段
        print("\n检查内容字段:")
        content_fields = [k for k in first_article.keys() if any(word in k.lower() for word in ['text', 'content', 'description'])]
        for field in content_fields:
            value = str(first_article.get(field, ''))
            print(f"  {field}: {value[:100]}...")

if __name__ == "__main__":
    check_article_fields()
