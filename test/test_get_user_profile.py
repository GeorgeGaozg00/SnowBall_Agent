import requests
import base64
import json
import os

def get_xueqiu_profile(cookie_str):
    """
    通过 Cookie 获取雪球用户完整信息
    :param cookie_str: 浏览器中复制的完整 Cookie 字符串
    """
    # 1. 从 Cookie 中提取 xq_a_token 并解析出 UID
    # 雪球的 token 逻辑：xq_a_token 是一个 JWT，里面包含了当前登录用户的 UID
    target_token = ""
    uid = None
    
    # 尝试从xq_id_token中提取UID
    xq_id_token = ""
    for item in cookie_str.split(';'):
        if 'xq_id_token' in item:
            xq_id_token = item.split('=')[1].strip()
            break
    
    if xq_id_token:
        print(f"xq_id_token: {xq_id_token[:50]}...")
        parts = xq_id_token.split('.')
        print(f"Token部分数量: {len(parts)}")
        
        if len(parts) >= 2:
            try:
                payload_b64 = parts[1]
                # 补全 base64 填充
                payload_json = base64.urlsafe_b64decode(payload_b64 + '=' * (4 - len(payload_b64) % 4)).decode('utf-8')
                user_data = json.loads(payload_json)
                uid = user_data.get('uid')
                print(f"成功解析出 UID: {uid}")
            except Exception as e:
                print(f"解析xq_id_token失败: {e}")
    
    # 如果xq_id_token解析失败，尝试从xq_a_token解析
    if not uid:
        for item in cookie_str.split(';'):
            if 'xq_a_token' in item:
                target_token = item.split('=')[1].strip()
                break
        
        if target_token:
            print(f"xq_a_token: {target_token[:50]}...")
            parts = target_token.split('.')
            print(f"xq_a_token部分数量: {len(parts)}")
            
            if len(parts) >= 2:
                try:
                    payload_b64 = parts[1]
                    # 补全 base64 填充
                    payload_json = base64.urlsafe_b64decode(payload_b64 + '=' * (4 - len(payload_b64) % 4)).decode('utf-8')
                    user_data = json.loads(payload_json)
                    uid = user_data.get('u')
                    print(f"成功解析出 UID: {uid}")
                except Exception as e:
                    print(f"解析xq_a_token失败: {e}")
            else:
                print("Token格式不正确，无法解析UID")
        else:
            print("错误：Cookie 中未找到 xq_a_token")
            return None
    
    if not uid:
        print("无法解析出UID")
        return None

    # 2. 直接访问用户主页并从HTML中提取信息
    url = f"https://xueqiu.com/u/{uid}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": cookie_str,
        "Referer": "https://xueqiu.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Sec-GPC": "1"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        print(f"请求URL: {url}")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            html_content = response.text
            print(f"HTML内容长度: {len(html_content)}")
            print(f"HTML前500字符: {html_content[:500]}...")
            
            # 尝试从HTML中提取用户信息
            import re
            
            # 提取用户名称
            name_match = re.search(r'<h1 class="user-name">(.*?)</h1>', html_content)
            name = name_match.group(1) if name_match else f"用户{str(uid)[:4]}"
            print(f"用户名称: {name}")
            
            # 提取用户头像
            avatar_match = re.search(r'<img class="avatar" src="(.*?)"', html_content)
            avatar = avatar_match.group(1) if avatar_match else f"https://ui-avatars.com/api/?name={name}&background=random"
            print(f"用户头像: {avatar}")
            
            # 提取用户简介
            bio_match = re.search(r'专注：(.*?)<', html_content)
            if not bio_match:
                bio_match = re.search(r'<p class="bio">(.*?)</p>', html_content)
            bio = bio_match.group(1) if bio_match else ""
            print(f"用户简介: {bio}")
            
            # 提取粉丝数
            followers_match = re.search(r'粉丝\s*<span class="num">(.*?)</span>', html_content)
            if not followers_match:
                followers_match = re.search(r'(\d+)\s*粉丝', html_content)
            followers = followers_match.group(1) if followers_match else "0"
            print(f"粉丝数: {followers}")
            
            # 提取关注数
            friends_match = re.search(r'关注\s*<span class="num">(.*?)</span>', html_content)
            if not friends_match:
                friends_match = re.search(r'(\d+)\s*关注', html_content)
            friends = friends_match.group(1) if friends_match else "0"
            print(f"关注数: {friends}")
            
            # 提取关键信息
            profile = {
                "昵称": name,
                "UID": uid,
                "头像URL": avatar,
                "简介": bio,
                "粉丝数": followers,
                "关注数": friends,
                "是否认证": "未知"
            }
            
            return profile
        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            print("提示：请检查 Cookie 是否过期或被 WAF 拦截")
            return None
    except Exception as e:
        print(f"请求异常: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_get_user_profile():
    """测试获取用户详细信息"""
    try:
        # 读取用户配置文件
        users_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'users.json')
        if os.path.exists(users_file):
            with open(users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            
            if users_data.get('users'):
                user = users_data['users'][0]
                cookie = user.get('cookie')
                print(f"测试用户cookie: {cookie[:50]}...")
                
                # 测试获取用户信息
                print("\n正在获取用户详细信息...")
                info = get_xueqiu_profile(cookie)
                
                if info:
                    print("\n--- 获取到的用户信息 ---")
                    for k, v in info.items():
                        print(f"{k}: {v}")
                else:
                    print("获取用户信息失败")
            else:
                print("用户列表为空")
        else:
            print("用户配置文件不存在")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    print("测试获取雪球用户详细信息")
    print("=" * 50)
    test_get_user_profile()
    print("\n测试完成")