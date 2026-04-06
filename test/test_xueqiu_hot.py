#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试雪球热点页面"""

import requests
from bs4 import BeautifulSoup

url = "https://xueqiu.com/hot/spot"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

print(f"正在请求: {url}")
response = requests.get(url, headers=headers, timeout=30)
print(f"响应状态码: {response.status_code}")

if response.status_code == 200:
    print("\n=== 页面前2000字符 ===")
    print(response.text[:2000])
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("\n=== 查找所有链接 ===")
    links = soup.find_all('a')
    for i, link in enumerate(links[:20]):
        href = link.get('href', '')
        text = link.get_text(strip=True)[:50]
        print(f"{i+1}. {text} -> {href}")
    
    print("\n=== 查找所有script标签 ===")
    scripts = soup.find_all('script')
    for i, script in enumerate(scripts):
        src = script.get('src', '')
        if src:
            print(f"{i+1}. {src}")
        else:
            content = script.string
            if content and ('hot' in content.lower() or 'spot' in content.lower()):
                print(f"\n=== Script {i+1} 包含热点相关内容 ===")
                print(content[:1000])
