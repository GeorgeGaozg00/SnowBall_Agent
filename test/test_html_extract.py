import requests
import re

# 测试第二个用户的主页
cookie = "xq_a_token=1a78672341b8936f5385e7cba00c9bb47b44a105;xq_r_token=48c9ca05a95a207767083e5c40285cc758856f5c;xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOjExMDEzNzg2ODMsImlzcyI6InVjIiwiZXhwIjoxNzc3OTg1MzgzLCJjdG0iOjE3NzUzOTMzODMxNTYsImNpZCI6ImQ5ZDBuNEFadXAifQ.QbUxNB3VJwoj2lO0oD0HSKgk_NfZBQ9IcOaEs0AF7griirc78-CY1N-IMDclHE_1f-b02Nsxd6lnCTSeCsUs7GypWPQg0l0LPVLZBmzdGKgx_g7dG9JrVdFaDZxv782s8qlq1jYut5PYz0bD2S3eVZikh8SNbanQ_llRFyw-Iiupe0ePE7UQSb136OkUkTUdoXoOG0g-ehBit7e2IBrO2aDmWW6-l1HLwEtiNIrTORXHFatxM0OEkSM1GPDTHKdiS0PJXPpDOAhGxKJ84es4quVY6c3x69D3kzJJYzInI46MDjJ-aS9xlJK9GMFBHIH94nyK-kc3oHOYvJNSs6prMg"
uid = "1101378683"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Cookie': cookie
}

# 访问用户主页
url = f"https://xueqiu.com/u/{uid}"
print(f"访问: {url}")
response = requests.get(url, headers=headers, timeout=10)
print(f"状态码: {response.status_code}")
print(f"内容长度: {len(response.text)}")

# 保存HTML文件查看
with open('/Users/zhigao/Desktop/Python/Xueqiu_report/xueqiu-hot-stocks/test/user_page.html', 'w', encoding='utf-8') as f:
    f.write(response.text[:10000])  # 只保存前10000字符
print("HTML已保存到 user_page.html")

# 尝试一些常见的模式
html_content = response.text
print("\n=== 尝试不同的正则表达式 ===")

# 1. 查找包含 user-name 的地方
name_patterns = [
    r'<h1[^>]*user-name[^>]*>(.*?)</h1>',
    r'<h1[^>]*class="[^"]*name[^"]*"[^>]*>(.*?)</h1>',
    r'<span[^>]*user-name[^>]*>(.*?)</span>',
    r'<a[^>]*username[^>]*>(.*?)</a>',
    r'userName":"([^"]+)"',
    r'"screen_name":"([^"]+)"',
    r'"name":"([^"]+)"'
]

for pattern in name_patterns:
    match = re.search(pattern, html_content)
    if match:
        print(f"✓ 找到匹配 (模式: {pattern[:40]}...): {match.group(1)[:50]}")
    else:
        print(f"✗ 未找到匹配 (模式: {pattern[:40]}...)")

# 2. 查找头像
avatar_patterns = [
    r'<img[^>]*avatar[^>]*src="([^"]+)"',
    r'avatar":"([^"]+)"',
    r'profile_image_url":"([^"]+)"',
    r'photo":"([^"]+)"'
]

print("\n=== 查找头像 ===")
for pattern in avatar_patterns:
    match = re.search(pattern, html_content)
    if match:
        print(f"✓ 找到匹配 (模式: {pattern[:40]}...): {match.group(1)[:100]}")
    else:
        print(f"✗ 未找到匹配 (模式: {pattern[:40]}...)")

# 3. 查找简介
bio_patterns = [
    r'<p[^>]*bio[^>]*>(.*?)</p>',
    r'<div[^>]*bio[^>]*>(.*?)</div>',
    r'description":"([^"]+)"',
    r'bio":"([^"]+)"'
]

print("\n=== 查找简介 ===")
for pattern in bio_patterns:
    match = re.search(pattern, html_content)
    if match:
        print(f"✓ 找到匹配 (模式: {pattern[:40]}...): {match.group(1)[:100]}")
    else:
        print(f"✗ 未找到匹配 (模式: {pattern[:40]}...)")
