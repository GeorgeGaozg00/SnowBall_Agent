#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 hashtag 页面内容"""

import requests
import json
import re
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://xueqiu.com/hot/spot",
    "Accept-Language": "zh-CN,zh;q=0.9"
}

session = requests.Session()
session.get("https://xueqiu.com/", headers=headers)

# 使用找到的第三个 hashtag
hashtag = "I-mmluiJmOa2suWMluWkqeeEtuawlOiIuemAmui_h-mYv-abvOa1t-WyuOWNl-e6vyM"
url = f"https://xueqiu.com/hashtag/{hashtag}"

print(f"正在请求 hashtag 页面: {url}")
response = session.get(url, headers=headers, timeout=30)
print(f"响应状态码: {response.status_code}")

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("\n=== 页面标题 ===")
    print(soup.title.string if soup.title else "无标题")
    
    print("\n=== 查找热点直击内容 ===")
    # 查找包含"热点直击"或"核心标的"的内容
    all_text = soup.get_text()
    
    # 查找相关段落
    keywords = ['热点直击', '核心标的', '当地时间', '市场方面', '核心标的']
    for keyword in keywords:
        print(f"\n--- 查找 '{keyword}' ---")
        if keyword in all_text:
            # 查找附近的内容
            idx = all_text.find(keyword)
            context = all_text[max(0, idx-50):min(len(all_text), idx+500)]
            print(context)
    
    # 保存完整页面
    with open('hashtag_page.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("\n已保存完整页面到 hashtag_page.html")
    
    # 查找 script 中的数据
    print("\n=== 查找 script 中的数据 ===")
    scripts = soup.find_all('script')
    for i, script in enumerate(scripts):
        content = script.string
        if content and ('hot' in content.lower() or 'spot' in content.lower() or 'hashtag' in content.lower()):
            print(f"\nScript {i+1} 包含相关内容")
            
            patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'window\.__NUXT__\s*=\s*({.*?});',
                r'_useSSRState\s*\(\s*({.*?})\s*\)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                if matches:
                    try:
                        json_str = matches[0]
                        data = json.loads(json_str)
                        print(f"成功解析JSON！")
                        
                        with open('hashtag_data.json', 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        print("已保存到 hashtag_data.json")
                        
                        # 尝试查找话题内容
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if isinstance(value, dict) or isinstance(value, list):
                                    value_str = str(value)
                                    if '热点' in value_str or '直击' in value_str:
                                        print(f"\n在 key '{key}' 中找到相关内容")
                                        break
                        break
                    except Exception as e:
                        print(f"解析失败: {e}")
                        continue
