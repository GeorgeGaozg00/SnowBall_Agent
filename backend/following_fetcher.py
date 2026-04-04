#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球用户关注列表获取模块
用于获取当前登录用户的关注列表
"""

import requests
import json
import time
import re


class FollowingListFetcher:
    """获取雪球用户关注列表的类"""
    
    def __init__(self, xueqiu_cookie):
        """
        初始化
        
        Args:
            xueqiu_cookie: 雪球Cookie字符串
        """
        self.xueqiu_cookie = xueqiu_cookie
        self.headers = {
            "Cookie": xueqiu_cookie,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://xueqiu.com",
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
    
    def get_current_user_id(self):
        """
        获取当前登录用户的ID
        
        Returns:
            str: 用户ID，如果失败返回None
        """
        try:
            # 首先尝试从JWT token中提取用户ID
            import base64
            
            # 从cookie中提取xq_id_token
            token_match = re.search(r'xq_id_token=([^;]+)', self.xueqiu_cookie)
            if token_match:
                token = token_match.group(1)
                # JWT token格式：header.payload.signature
                parts = token.split('.')
                if len(parts) >= 2:
                    try:
                        # 解码payload部分
                        payload = parts[1]
                        # JWT base64编码可能缺少padding，需要补充
                        payload += '=' * ((4 - len(payload) % 4) % 4)
                        decoded_payload = base64.urlsafe_b64decode(payload).decode('utf-8')
                        user_data = json.loads(decoded_payload)
                        
                        if 'uid' in user_data:
                            # 从JWT中获取用户ID
                            return str(user_data['uid'])
                    except Exception as e:
                        print(f"解析JWT token失败: {str(e)}")
            
            # 如果从JWT中提取失败，尝试访问个人中心页面
            url = "https://xueqiu.com/center"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                # 从页面中提取用户ID
                match = re.search(r'/u/(\d+)', response.text)
                if match:
                    user_id = match.group(1)
                    return user_id
            
            return None
        except Exception as e:
            print(f"获取用户ID失败: {str(e)}")
            return None
    
    def get_following_list(self, user_id=None, size=200):
        """
        获取用户的关注列表
        
        Args:
            user_id: 用户ID，如果为None则获取当前登录用户的关注列表
            size: 每次请求获取的用户数量，默认200
        
        Returns:
            list: 关注用户列表，每个元素是一个字典包含用户信息
        """
        try:
            # 如果没有提供user_id，则获取当前登录用户的ID
            if user_id is None:
                user_id = self.get_current_user_id()
                if user_id is None:
                    print("无法获取用户ID")
                    return []
            
            print(f"正在获取用户 {user_id} 的关注列表...")
            
            # 使用更完整的请求头，模拟真实浏览器
            full_headers = {
                "Cookie": self.xueqiu_cookie,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": f"https://xueqiu.com/u/{user_id}",
                "X-Requested-With": "XMLHttpRequest",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }
            
            # 使用API获取关注列表
            url = "https://xueqiu.com/friendships/friends.json"
            
            # 尝试不同的size值，确保获取所有用户
            size_values = [90, 100, 150, 200]
            
            for size in size_values:
                params = {
                    "uid": user_id,
                    "page": 1,
                    "size": size
                }
                
                response = requests.get(url, headers=full_headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 提取关注列表
                    users = data.get("friends", [])
                    total_count = data.get('count', len(users))
                    
                    print(f"尝试size={size}，获取到 {len(users)} 个关注的人，总共 {total_count} 个")
                    
                    # 如果获取的用户数量等于总关注数，说明成功了
                    if len(users) >= total_count:
                        print(f"成功！使用size={size}获取了所有 {len(users)} 个关注的人")
                        return users
                else:
                    print(f"API请求失败: {response.status_code}")
            
            # 如果所有size值都试过了还是没有获取完整数据，返回最后一次的结果
            print(f"警告：可能没有获取到所有关注用户")
            return users if response.status_code == 200 else []
                
        except Exception as e:
            print(f"获取关注列表失败: {str(e)}")
            return []
    
    def get_following_list_formatted(self, user_id=None):
        """
        获取格式化的关注列表（包含UID、昵称和头像）
        
        Args:
            user_id: 用户ID，如果为None则获取当前登录用户的关注列表
        
        Returns:
            list: 关注用户列表，每个元素是一个字典包含uid、screen_name和profile_image
        """
        users = self.get_following_list(user_id)
        
        formatted_list = []
        for user in users:
            # 获取头像URL
            profile_image_url = user.get('profile_image_url', '')
            photo_domain = user.get('photo_domain', 'http://xavatar.imedao.com/')
            
            # 拼接完整头像URL
            if profile_image_url:
                # 取第一个头像URL（通常是最大的那个）
                first_image = profile_image_url.split(',')[0] if ',' in profile_image_url else profile_image_url
                if first_image.startswith('http'):
                    full_image_url = first_image
                else:
                    full_image_url = f"{photo_domain}{first_image}"
            else:
                full_image_url = ''
            
            formatted_list.append({
                'uid': user.get('id'),
                'screen_name': user.get('screen_name', '未知用户'),
                'profile_image': full_image_url,
                'description': user.get('description', '') or ''
            })
        
        return formatted_list
    
    def get_following_list_text(self, user_id=None):
        """
        获取文本格式的关注列表
        
        Args:
            user_id: 用户ID，如果为None则获取当前登录用户的关注列表
        
        Returns:
            str: 格式化的文本，包含所有关注用户的UID和昵称
        """
        users = self.get_following_list_formatted(user_id)
        
        if not users:
            return "未获取到关注列表"
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"关注列表（共 {len(users)} 人）")
        lines.append("=" * 60)
        lines.append("")
        
        for i, user in enumerate(users, 1):
            uid = user.get('uid', 'N/A')
            screen_name = user.get('screen_name', '未知用户')
            lines.append(f"{i:3d}. UID: {uid:15d}  昵称: {screen_name}")
        
        lines.append("")
        lines.append("=" * 60)
        lines.append(f"总计: {len(users)} 个关注的人")
        lines.append("=" * 60)
        
        return "\n".join(lines)


# 测试代码
if __name__ == "__main__":
    # 测试用的Cookie（需要替换为实际的Cookie）
    test_cookie = "your_cookie_here"
    
    fetcher = FollowingListFetcher(test_cookie)
    
    # 获取当前用户ID
    user_id = fetcher.get_current_user_id()
    print(f"当前用户ID: {user_id}")
    
    # 获取关注列表
    following_text = fetcher.get_following_list_text()
    print(following_text)
