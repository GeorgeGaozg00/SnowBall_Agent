#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试程序：测试获取单篇文章详情API
"""

import requests
import json
import os

def test_article_detail():
    """测试获取文章详情"""
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
    
    # 测试文章ID
    article_id = "382657313"
    
    # 测试不同的API端点
    apis = [
        f"https://xueqiu.com/statuses/show.json?id={article_id}",
        f"https://stock.xueqiu.com/v5/stock/quotepage.json?symbol=SH{article_id}",
        f"https://xueqiu.com/query/v1/symbol/search/status.json?symbol=SH{article_id}",
    ]
    
    for api_url in apis:
        print(f"\n测试API: {api_url}")
        try:
            response = session.get(api_url, headers=headers)
            print(f"状态码: {response.status_code}")
            print(f"内容类型: {response.headers.get('Content-Type', 'unknown')}")
            
            if 'application/json' in response.headers.get('Content-Type', ''):
                data = response.json()
                print(f"返回数据键: {list(data.keys())[:10]}")
                
                # 检查是否有打赏相关字段
                if 'reward_count' in str(data):
                    print("✓ 包含打赏相关字段")
                if 'text' in str(data):
                    print("✓ 包含文章内容字段")
            else:
                print(f"响应内容前200字符: {response.text[:200]}")
        except Exception as e:
            print(f"错误: {e}")

if __name__ == "__main__":
    test_article_detail()
