import requests
import json

# 第二个用户的 cookie
cookie = "xq_a_token=1a78672341b8936f5385e7cba00c9bb47b44a105;xq_r_token=48c9ca05a95a207767083e5c40285cc758856f5c;xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOjExMDEzNzg2ODMsImlzcyI6InVjIiwiZXhwIjoxNzc3OTg1MzgzLCJjdG0iOjE3NzUzOTMzODMxNTYsImNpZCI6ImQ5ZDBuNEFadXAifQ.QbUxNB3VJwoj2lO0oD0HSKgk_NfZBQ9IcOaEs0AF7griirc78-CY1N-IMDclHE_1f-b02Nsxd6lnCTSeCsUs7GypWPQg0l0LPVLZBmzdGKgx_g7dG9JrVdFaDZxv782s8qlq1jYut5PYz0bD2S3eVZikh8SNbanQ_llRFyw-Iiupe0ePE7UQSb136OkUkTUdoXoOG0g-ehBit7e2IBrO2aDmWW6-l1HLwEtiNIrTORXHFatxM0OEkSM1GPDTHKdiS0PJXPpDOAhGxKJ84es4quVY6c3x69D3kzJJYzInI46MDjJ-aS9xlJK9GMFBHIH94nyK-kc3oHOYvJNSs6prMg"
uid = "1101378683"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Cookie': cookie
}

# 尝试多个 API 端点
api_endpoints = [
    "https://xueqiu.com/v4/user/show.json",
    "https://xueqiu.com/api/v4/users/me",
    "https://xueqiu.com/v5/user/detail.json",
    "https://xueqiu.com/v4/user/info.json",
    "https://xueqiu.com/api/v5/user/info",
    "https://xueqiu.com/v4/setting/config.json",
    "https://xueqiu.com/api/v4/user/profile",
    "https://xueqiu.com/v5/user/show.json",
    "https://xueqiu.com/statuses/myself_timeline.json",
    "https://xueqiu.com/v4/relationships/friends.json",
    "https://xueqiu.com/v4/relationships/followers.json",
    "https://xueqiu.com/notify/count.json",
    "https://xueqiu.com/v5/feed/timeline.json",
    "https://xueqiu.com/v1/feed/homepage_timeline.json",
    "https://xueqiu.com/v4/query/profile.json",
    "https://xueqiu.com/api/v4/query/user",
    "https://xueqiu.com/v5/user/config.json",
]

for url in api_endpoints:
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"\n=== {url} ===")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"响应数据: {json.dumps(data, ensure_ascii=False)[:800]}")
            except Exception as e:
                print(f"解析JSON失败: {e}")
                print(f"响应内容: {response.text[:500]}")
    except Exception as e:
        print(f"\n=== {url} ===")
        print(f"请求失败: {e}")
