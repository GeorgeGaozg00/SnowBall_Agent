#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试雪球热点页面 - 详细分析"""

import requests
import json
import re

url = "https://xueqiu.com/hot/spot"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://xueqiu.com/",
    "Accept-Language": "zh-CN,zh;q=0.9"
}

session = requests.Session()
session.get("https://xueqiu.com/", headers=headers)

print(f"正在请求: {url}")
response = session.get(url, headers=headers, timeout=30)
print(f"响应状态码: {response.status_code}")

if response.status_code == 200:
    # 查找所有包含 hashtag 的链接
    print("\n=== 查找 hashtag 链接 ===")
    hashtag_pattern = r'/hashtag/([^"\'\s]+)'
    hashtag_matches = re.findall(hashtag_pattern, response.text)
    
    print(f"找到 {len(hashtag_matches)} 个 hashtag:")
    for i, hashtag in enumerate(hashtag_matches[:20]):
        print(f"{i+1}. /hashtag/{hashtag}")
    
    # 查找所有 a 标签
    print("\n=== 查找所有 a 标签 ===")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    all_links = soup.find_all('a')
    print(f"共找到 {len(all_links)} 个链接")
    
    hashtag_links = []
    for link in all_links:
        href = link.get('href', '')
        if '/hashtag/' in href:
            text = link.get_text(strip=True)[:80]
            hashtag_links.append((href, text))
    
    print(f"\n找到 {len(hashtag_links)} 个 hashtag 链接:")
    for i, (href, text) in enumerate(hashtag_links[:20]):
        print(f"{i+1}. {href}")
        print(f"    文本: {text}\n")
    
    # 保存完整响应到文件
    with open('hot_spot_page.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("\n已保存完整页面到 hot_spot_page.html")
    
    # 查找 script 中的 JSON 数据
    print("\n=== 查找 script 中的数据 ===")
    scripts = soup.find_all('script')
    for i, script in enumerate(scripts):
        content = script.string
        if content and ('hot' in content.lower() or 'spot' in content.lower()):
            print(f"\nScript {i+1} 包含热点相关内容")
            
            # 查找可能的 JSON 对象
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
                        
                        # 保存到文件
                        with open('hot_spot_data.json', 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        print("已保存到 hot_spot_data.json")
                        break
                    except Exception as e:
                        print(f"解析失败: {e}")
                        continue
