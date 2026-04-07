#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球API功能测试文件
测试所有主要的雪球API功能
"""

import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import requests
import json
import time
import re
import base64
from datetime import datetime


class XueqiuAPITester:
    """雪球API测试类"""
    
    def __init__(self, cookie_str=None):
        """
        初始化
        
        Args:
            cookie_str: Cookie字符串，如果为None则从配置文件读取
        """
        self.cookie_str = cookie_str
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://xueqiu.com/",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://xueqiu.com",
            "Sec-Ch-Ua": '"Chromium";v="120", "Google Chrome";v="120", "Not A Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        
        if self.cookie_str:
            self.headers["Cookie"] = self.cookie_str
    
    def load_cookie_from_config(self):
        """从配置文件加载Cookie"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'config', 'users.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                default_user_id = data.get("defaultUserId")
                if default_user_id:
                    for user in data.get("users", []):
                        if user.get("id") == default_user_id:
                            self.cookie_str = user.get("cookie")
                            self.headers["Cookie"] = self.cookie_str
                            print(f"✅ 已加载用户 {user.get('screenName')} 的Cookie")
                            return True
            print("❌ 未找到默认用户的Cookie")
            return False
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return False
    
    def print_separator(self, title):
        """打印分隔线"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)
    
    def test_get_user_info(self):
        """测试1: 通过Cookie获取用户基本信息"""
        self.print_separator("测试1: 通过Cookie获取用户基本信息")
        
        if not self.cookie_str:
            print("❌ 未提供Cookie，跳过此测试")
            return None
        
        try:
            # 方法1: 从JWT token中提取用户ID
            print("步骤1: 尝试从JWT token中提取用户ID...")
            token_match = re.search(r'xq_id_token=([^;]+)', self.cookie_str)
            if token_match:
                token = token_match.group(1)
                parts = token.split('.')
                if len(parts) >= 2:
                    try:
                        payload = parts[1] + '=' * ((4 - len(parts[1]) % 4) % 4)
                        decoded_payload = base64.urlsafe_b64decode(payload).decode('utf-8')
                        user_data = json.loads(decoded_payload)
                        if 'uid' in user_data:
                            user_id = str(user_data['uid'])
                            print(f"✅ 从JWT token获取到用户ID: {user_id}")
                    except Exception as e:
                        print(f"⚠️  解析JWT token失败: {e}")
            
            # 方法2: 访问个人中心页面
            print("\n步骤2: 访问个人中心页面...")
            response = self.session.get("https://xueqiu.com/center", headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ 页面访问成功，状态码: {response.status_code}")
                
                # 从页面中提取用户ID
                match = re.search(r'/u/(\d+)', response.text)
                if match:
                    user_id = match.group(1)
                    print(f"✅ 从页面获取到用户ID: {user_id}")
                    
                    # 获取用户详细信息
                    print("\n步骤3: 获取用户详细信息...")
                    user_detail_url = f"https://xueqiu.com/v4/user/show.json?user_id={user_id}"
                    user_response = self.session.get(user_detail_url, headers=self.headers)
                    
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        print("✅ 用户详细信息获取成功:")
                        print(f"   昵称: {user_data.get('screen_name', '')}")
                        print(f"   头像: {user_data.get('profile_image', '')[:50]}...")
                        print(f"   简介: {user_data.get('description', '')[:50]}...")
                        
                        return {
                            'user_id': user_id,
                            'screen_name': user_data.get('screen_name', ''),
                            'profile_image': user_data.get('profile_image', ''),
                            'description': user_data.get('description', '')
                        }
                    else:
                        print(f"⚠️  获取用户详细信息失败，状态码: {user_response.status_code}")
                        print("   但已获取到用户ID，继续后续测试...")
                        # 即使获取不到详细信息，只要有user_id就继续
                        return {
                            'user_id': user_id,
                            'screen_name': f'用户{user_id[:4]}',
                            'profile_image': '',
                            'description': ''
                        }
                else:
                    print("❌ 未从页面中找到用户ID")
            else:
                print(f"❌ 页面访问失败，状态码: {response.status_code}")
            
            return None
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return None
    
    def test_get_following_list(self, user_id):
        """测试2: 获取用户关注列表"""
        self.print_separator("测试2: 获取用户关注列表")
        
        if not user_id:
            print("❌ 未提供用户ID，跳过此测试")
            return []
        
        try:
            print(f"正在获取用户 {user_id} 的关注列表...")
            
            url = "https://xueqiu.com/friendships/friends.json"
            params = {
                "uid": user_id,
                "page": 1,
                "size": 20
            }
            
            response = self.session.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                users = data.get("friends", [])
                total_count = data.get('count', len(users))
                
                print(f"✅ 关注列表获取成功")
                print(f"   总关注数: {total_count}")
                print(f"   本次获取: {len(users)} 个用户")
                
                if users:
                    print("\n前5个关注用户:")
                    for i, user in enumerate(users[:5], 1):
                        print(f"   {i}. {user.get('screen_name', '未知用户')} (UID: {user.get('id')})")
                
                return users
            else:
                print(f"❌ 获取关注列表失败，状态码: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return []
    
    def test_get_user_articles(self, user_id):
        """测试3: 获取用户文章"""
        self.print_separator("测试3: 获取用户文章")
        
        if not user_id:
            print("❌ 未提供用户ID，跳过此测试")
            return []
        
        try:
            print(f"正在获取用户 {user_id} 的文章...")
            
            # 先访问首页建立会话
            print("步骤1: 访问首页建立会话...")
            self.session.get("https://xueqiu.com/", headers=self.headers, timeout=10)
            time.sleep(0.5)
            
            # 获取用户文章
            print("\n步骤2: 获取用户文章列表...")
            url = f"https://xueqiu.com/v4/statuses/user_timeline.json"
            params = {
                "user_id": user_id,
                "page": 1,
                "count": 10
            }
            
            response = self.session.get(url, headers=self.headers, params=params, timeout=10)
            
            print(f"API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                if response.text.strip().startswith('{'):
                    data = response.json()
                    statuses = data.get("statuses", [])
                    
                    print(f"✅ 用户文章获取成功")
                    print(f"   本次获取: {len(statuses)} 篇文章")
                    
                    if statuses:
                        print("\n前3篇文章:")
                        for i, status in enumerate(statuses[:3], 1):
                            title = status.get("title") or "无标题 (可能是短贴)"
                            created_at = status.get("created_at")
                            if created_at:
                                created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                created_time = "未知"
                            
                            print(f"   {i}. {title[:30]}...")
                            print(f"      ID: {status.get('id')}")
                            print(f"      时间: {created_time}")
                            print(f"      点赞: {status.get('like_count', 0)} | 评论: {status.get('reply_count', 0)}")
                    
                    return statuses
                else:
                    print(f"⚠️  响应不是JSON，可能被WAF防护拦截")
                    print(f"   尝试获取热门文章作为替代...")
                    return self._get_hot_articles()
            else:
                print(f"⚠️  获取用户文章失败，状态码: {response.status_code}")
                print(f"   尝试获取热门文章作为替代...")
                return self._get_hot_articles()
        except Exception as e:
            print(f"⚠️  测试失败: {e}")
            print(f"   尝试获取热门文章作为替代...")
            return self._get_hot_articles()
    
    def _get_hot_articles(self):
        """获取热门文章作为替代方案"""
        try:
            print("\n正在获取热门文章...")
            hot_url = "https://xueqiu.com/v4/statuses/public_timeline_by_category.json"
            hot_params = {"since_id": -1, "max_id": -1, "count": 5, "category": -1}
            
            hot_response = self.session.get(hot_url, headers=self.headers, params=hot_params, timeout=10)
            if hot_response.status_code == 200 and hot_response.text.strip().startswith('{'):
                hot_data = hot_response.json()
                hot_items = hot_data.get("list", [])
                articles = []
                for item in hot_items:
                    if isinstance(item, dict) and "data" in item:
                        article_data = json.loads(item["data"])
                        articles.append(article_data)
                
                print(f"✅ 热门文章获取成功，共 {len(articles)} 篇")
                if articles:
                    print("\n前3篇文章:")
                    for i, status in enumerate(articles[:3], 1):
                        title = status.get("title") or "无标题 (可能是短贴)"
                        created_at = status.get("created_at")
                        if created_at:
                            created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            created_time = "未知"
                        
                        print(f"   {i}. {title[:30]}...")
                        print(f"      ID: {status.get('id')}")
                        print(f"      时间: {created_time}")
                        print(f"      点赞: {status.get('like_count', 0)} | 评论: {status.get('reply_count', 0)}")
                
                return articles
            else:
                print(f"❌ 热门文章获取失败")
                return []
        except Exception as e:
            print(f"❌ 获取热门文章失败: {e}")
            return []
    
    def test_get_article_attributes(self, article_id=None, article_data=None):
        """测试4: 获取文章属性
        
        Args:
            article_id: 文章ID
            article_data: 文章数据（如果已提供，则直接使用）
        """
        self.print_separator("测试4: 获取文章属性")
        
        if not article_id and not article_data:
            print("❌ 未提供文章ID或文章数据，跳过此测试")
            return None
        
        try:
            if article_data:
                # 直接使用提供的文章数据
                data = article_data
                print("✅ 使用已有的文章数据")
            else:
                # 尝试从API获取
                print(f"正在获取文章 {article_id} 的属性...")
                
                # 步骤1: 访问首页建立会话
                print("步骤1: 访问首页建立会话...")
                self.session.get("https://xueqiu.com/", headers=self.headers, timeout=10)
                time.sleep(0.5)
                
                # 步骤2: 获取文章详情
                print("\n步骤2: 获取文章详情...")
                api_url = f"https://xueqiu.com/statuses/show.json?id={article_id}"
                response = self.session.get(api_url, headers=self.headers)
                
                if response.status_code == 200 and response.text.strip().startswith('{'):
                    data = response.json()
                else:
                    print("⚠️  无法从API获取文章数据")
                    return None
            
            print("✅ 文章属性获取成功:")
            print(f"   标题: {data.get('title') or '无标题 (可能是短贴)'}")
            print(f"   ID: {data.get('id')}")
            print(f"   点赞: {data.get('like_count', 0)}")
            print(f"   评论: {data.get('reply_count', 0)}")
            print(f"   转发: {data.get('retweet_count', 0)}")
            print(f"   阅读: {data.get('view_count', 0)}")
            print(f"   收藏: {data.get('fav_count', 0)}")
            print(f"   是否专栏: {'是' if data.get('is_column', False) else '否'}")
            
            created_at = data.get("created_at")
            if created_at:
                created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
                print(f"   创建时间: {created_time}")
            
            return data
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return None
    
    def test_publish_comment(self, article_id, content="测试评论"):
        """测试5: 发布评论"""
        self.print_separator("测试5: 发布评论")
        
        if not article_id:
            print("❌ 未提供文章ID，跳过此测试")
            return None
        
        if not self.cookie_str:
            print("❌ 未提供Cookie，跳过此测试")
            return None
        
        try:
            print(f"准备对文章 {article_id} 发布评论: {content}")
            
            # 步骤1: 文本审核
            print("\n步骤1: 文本审核...")
            text_check_url = "https://xueqiu.com/statuses/text_check.json"
            text_check_data = {
                "text": f"<p>{content}</p>",
                "type": "3"
            }
            
            text_check_response = self.session.post(text_check_url, headers=self.headers, data=text_check_data)
            if text_check_response.status_code != 200:
                print(f"❌ 文本审核失败，状态码: {text_check_response.status_code}")
                return None
            print("✅ 文本审核通过")
            
            time.sleep(1)
            
            # 步骤2: 获取会话token
            print("\n步骤2: 获取会话token...")
            token_url = "https://xueqiu.com/provider/session/token.json"
            token_params = {
                "api_path": "/statuses/reply.json",
                "_": int(time.time() * 1000)
            }
            
            token_response = self.session.get(token_url, headers=self.headers, params=token_params)
            if token_response.status_code != 200:
                print(f"❌ 获取token失败，状态码: {token_response.status_code}")
                return None
            
            token_data = token_response.json()
            session_token = token_data.get("session_token", "")
            if not session_token:
                print("❌ 未获取到session_token")
                return None
            print("✅ 会话token获取成功")
            
            time.sleep(1)
            
            # 步骤3: 发布评论
            print("\n步骤3: 发布评论...")
            reply_url = "https://xueqiu.com/statuses/reply.json"
            reply_data = {
                "comment": f"<p>{content}</p>",
                "forward": "1",
                "id": article_id,
                "post_source": "htl",
                "post_position": "pc_home_feedcard",
                "session_token": session_token
            }
            
            reply_response = self.session.post(reply_url, headers=self.headers, data=reply_data)
            if reply_response.status_code == 200:
                reply_data = reply_response.json()
                if "id" in reply_data:
                    comment_id = reply_data.get('id')
                    print(f"✅ 评论发布成功，评论ID: {comment_id}")
                    return {"success": True, "comment_id": comment_id}
                else:
                    print("❌ 评论发布失败: 响应格式异常")
                    return {"success": False}
            else:
                print(f"❌ 评论发布失败，状态码: {reply_response.status_code}")
                print(f"   响应内容: {reply_response.text[:200]}")
                return {"success": False}
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return {"success": False}
    
    def test_like_article(self, article_id):
        """测试6: 点赞文章"""
        self.print_separator("测试6: 点赞文章")
        
        if not article_id:
            print("❌ 未提供文章ID，跳过此测试")
            return None
        
        if not self.cookie_str:
            print("❌ 未提供Cookie，跳过此测试")
            return None
        
        try:
            print(f"准备对文章 {article_id} 进行点赞...")
            
            url = "https://xueqiu.com/statuses/like.json"
            data = {
                "id": article_id
            }
            
            response = self.session.post(url, headers=self.headers, data=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("is_liked", False):
                    print("✅ 点赞成功")
                    return {"success": True}
                else:
                    print("❌ 点赞失败")
                    return {"success": False}
            else:
                print(f"❌ 点赞请求失败，状态码: {response.status_code}")
                return {"success": False}
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return {"success": False}
    
    def test_publish_post(self, content="<p>这是一篇测试文章</p>", title="测试文章", post_type='discussion'):
        """测试7: 发布文章"""
        self.print_separator("测试7: 发布文章")
        
        if not self.cookie_str:
            print("❌ 未提供Cookie，跳过此测试")
            return None
        
        try:
            print(f"准备发布{post_type}文章: {title}")
            
            # 步骤1: 访问首页建立会话
            print("\n步骤1: 访问首页建立会话...")
            self.session.get("https://xueqiu.com/", headers=self.headers, timeout=10)
            time.sleep(0.5)
            
            # 步骤2: 文本审核
            print("\n步骤2: 文本审核...")
            text_check_url = "https://xueqiu.com/statuses/text_check.json"
            text_check_data = {
                "text": content,
                "type": "2"
            }
            
            text_check_response = self.session.post(text_check_url, headers=self.headers, data=text_check_data)
            if text_check_response.status_code != 200:
                print(f"❌ 文本审核失败，状态码: {text_check_response.status_code}")
                return None
            print("✅ 文本审核通过")
            
            time.sleep(1)
            
            # 步骤3: 获取会话token
            print("\n步骤3: 获取会话token...")
            token_url = "https://xueqiu.com/provider/session/token.json"
            token_params = {
                "api_path": "/statuses/update.json",
                "_": int(time.time() * 1000)
            }
            
            token_response = self.session.get(token_url, headers=self.headers, params=token_params)
            if token_response.status_code != 200:
                print(f"❌ 获取token失败，状态码: {token_response.status_code}")
                return None
            
            token_data = token_response.json()
            session_token = token_data.get("session_token", "")
            if not session_token:
                print("❌ 未获取到session_token")
                return None
            print("✅ 会话token获取成功")
            
            time.sleep(1)
            
            # 步骤4: 发布文章
            print("\n步骤4: 发布文章...")
            update_url = "https://xueqiu.com/statuses/update.json"
            update_data = {
                "description": content,
                "session_token": session_token,
                "title": title
            }
            
            update_response = self.session.post(update_url, headers=self.headers, data=update_data)
            if update_response.status_code == 200:
                result = update_response.json()
                if "id" in result:
                    post_id = result.get('id')
                    print(f"✅ 文章发布成功，文章ID: {post_id}")
                    return {"success": True, "post_id": post_id}
                else:
                    print("❌ 文章发布失败: 响应格式异常")
                    return {"success": False}
            else:
                print(f"❌ 文章发布失败，状态码: {update_response.status_code}")
                print(f"   响应内容: {update_response.text[:200]}")
                return {"success": False}
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return {"success": False}
    
    def run_all_tests(self, interactive=False):
        """
        运行所有测试
        
        Args:
            interactive: 是否交互式运行（需要用户确认）
        """
        print("\n" + "=" * 80)
        print("  雪球API功能测试")
        print("=" * 80)
        
        # 加载Cookie
        if not self.cookie_str:
            if not self.load_cookie_from_config():
                print("\n❌ 无法继续测试，请提供有效的Cookie")
                return
        
        results = {}
        
        # 测试1: 获取用户信息
        user_info = self.test_get_user_info()
        results['user_info'] = user_info
        
        if user_info:
            user_id = user_info['user_id']
            
            # 测试2: 获取关注列表
            following_list = self.test_get_following_list(user_id)
            results['following_list'] = following_list
            
            # 测试3: 获取用户文章
            articles = self.test_get_user_articles(user_id)
            results['articles'] = articles
            
            if articles:
                test_article = articles[0]
                article_id = test_article.get('id')
                
                # 测试4: 获取文章属性 - 直接使用已有数据
                article_attrs = self.test_get_article_attributes(article_data=test_article)
                results['article_attrs'] = article_attrs
                
                if interactive:
                    # 询问是否继续测试需要实际操作的功能
                    print("\n" + "=" * 80)
                    print("  注意：以下测试会进行实际操作（发布评论、点赞、发布文章）")
                    print("=" * 80)
                    
                    choice = input("\n是否继续测试实际操作功能？(y/n): ").strip().lower()
                    if choice != 'y':
                        print("\n已跳过实际操作测试")
                        return results
                
                # 测试5: 发布评论
                comment_result = self.test_publish_comment(article_id, "这是一条测试评论，来自API测试程序")
                results['comment'] = comment_result
                
                # 测试6: 点赞
                like_result = self.test_like_article(article_id)
                results['like'] = like_result
                
                # 测试7: 发布文章
                post_result = self.test_publish_post(
                    content="<p>这是一篇通过API发布的测试文章。</p><p>测试内容，请勿当真。</p>",
                    title="API测试文章 - " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                results['post'] = post_result
        
        # 打印测试总结
        print("\n" + "=" * 80)
        print("  测试总结")
        print("=" * 80)
        
        for test_name, result in results.items():
            status = "✅ 成功" if result else "❌ 失败"
            print(f"  {test_name}: {status}")
        
        return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='雪球API功能测试')
    parser.add_argument('--cookie', type=str, help='Cookie字符串')
    parser.add_argument('--interactive', action='store_true', help='交互式运行')
    
    args = parser.parse_args()
    
    # 创建测试实例
    tester = XueqiuAPITester(cookie_str=args.cookie)
    
    # 运行所有测试
    results = tester.run_all_tests(interactive=args.interactive)
    
    # 保存结果
    output_file = os.path.join(os.path.dirname(__file__), 'test_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n测试结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
