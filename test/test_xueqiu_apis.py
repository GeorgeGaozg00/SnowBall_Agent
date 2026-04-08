#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪球API功能测试程序
参考backend中的实际代码实现
"""

import os
import sys
# 全局禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

# 添加backend目录到路径，以便导入article_utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import requests
import json
import time
import re
import base64
from datetime import datetime
from article_utils import get_article_full_attributes
from app import get_article_stats
from topic_fetcher import get_topic_articles


def print_separator(title):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


class XueQiuAPITester:
    """雪球API测试类"""
    
    def __init__(self, cookie_str):
        """
        初始化
        
        Args:
            cookie_str: 雪球Cookie字符串
        """
        self.cookie_str = cookie_str
        self.session = requests.Session()
        # 禁用代理
        self.session.trust_env = False
        self.session.proxies = {'http': None, 'https': None}
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cookie": cookie_str
        }
    
    def get_user_info(self):
        """
        测试1: 通过Cookie获取用户基本信息
        
        Returns:
            用户信息字典
        """
        print_separator("测试1: 通过Cookie获取用户基本信息")
        
        user_id = None
        
        try:
            print("步骤1: 尝试从JWT token中提取用户ID...")
            
            token_match = re.search(r'xq_id_token=([^;]+)', self.cookie_str)
            if token_match:
                token = token_match.group(1)
                parts = token.split('.')
                if len(parts) >= 2:
                    try:
                        payload = parts[1]
                        payload += '=' * ((4 - len(payload) % 4) % 4)
                        decoded_payload = base64.urlsafe_b64decode(payload).decode('utf-8')
                        user_data = json.loads(decoded_payload)
                        
                        if 'uid' in user_data:
                            user_id = str(user_data['uid'])
                            print(f"✅ 从JWT token获取到用户ID: {user_id}")
                    except Exception as e:
                        print(f"解析JWT token失败: {str(e)}")
            
            if not user_id:
                print("\n步骤2: 访问个人中心页面...")
                url = "https://xueqiu.com/center"
                headers = self.base_headers.copy()
                headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                
                response = self.session.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    print("✅ 页面访问成功，状态码: 200")
                    match = re.search(r'/u/(\d+)', response.text)
                    if match:
                        user_id = match.group(1)
                        print(f"✅ 从页面获取到用户ID: {user_id}")
            
            if not user_id:
                print("❌ 无法获取用户ID")
                return None
            
            user_info = {
                'user_id': user_id,
                'screen_name': '未知用户',
                'description': ''
            }
            
            print(f"\n✅ 用户基本信息获取成功:")
            print(f"   用户ID: {user_info['user_id']}")
            
            return user_info
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return None
    
    def get_following_list(self, user_id, size=100):
        """
        测试2: 获取用户关注列表
        
        Args:
            user_id: 用户ID
            size: 每次获取的用户数量
            
        Returns:
            关注用户列表
        """
        print_separator("测试2: 获取用户关注列表")
        
        if not user_id:
            print("❌ 未提供用户ID，跳过此测试")
            return []
        
        try:
            print(f"正在获取用户 {user_id} 的关注列表...")
            
            headers = self.base_headers.copy()
            headers.update({
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": f"https://xueqiu.com/u/{user_id}",
                "X-Requested-With": "XMLHttpRequest"
            })
            
            url = "https://xueqiu.com/friendships/friends.json"
            params = {
                "uid": user_id,
                "page": 1,
                "size": size
            }
            
            response = self.session.get(url, headers=headers, params=params, timeout=10)
            
            print(f"API响应状态码: {response.status_code}")
            
            if response.status_code == 200 and response.text.strip().startswith('{'):
                data = response.json()
                users = data.get("friends", [])
                total_count = data.get('count', len(users))
                
                print(f"✅ 关注列表获取成功")
                print(f"   总关注数: {total_count}")
                print(f"   本次获取: {len(users)} 个用户")
                
                if users:
                    print("\n前5个关注用户:")
                    for i, user in enumerate(users[:5], 1):
                        print(f"   {i}. {user.get('screen_name', '未知')} (UID: {user.get('id')})")
                
                return users
            else:
                print(f"⚠️  获取关注列表失败")
                return []
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return []
    
    def get_hot_articles(self):
        """
        获取热门文章（简化版）
        
        Returns:
            热门文章列表
        """
        try:
            print("正在获取热门文章...")
            
            # 使用更简单的方式获取热门文章
            headers = self.base_headers.copy()
            headers.update({
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://xueqiu.com/",
                "X-Requested-With": "XMLHttpRequest"
            })
            
            api_url = "https://xueqiu.com/v4/statuses/public_timeline_by_category.json"
            params = {
                "since_id": -1,
                "max_id": -1,
                "count": 5,
                "category": -1
            }
            
            response = self.session.get(api_url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200 and response.text.strip().startswith('{'):
                data = response.json()
                items = data.get("list", [])
                
                articles = []
                for item in items:
                    if "data" in item:
                        article_data = json.loads(item["data"])
                        articles.append(article_data)
                
                print(f"✅ 热门文章获取成功，共 {len(articles)} 篇")
                return articles
            else:
                print(f"⚠️  获取热门文章失败，返回空列表")
                return []
        except Exception as e:
            print(f"❌ 获取热门文章失败: {e}")
            return []
    
    def get_user_articles(self, user_id, count=10):
        """
        测试3: 获取用户文章
        
        Args:
            user_id: 用户ID
            count: 获取文章数量
            
        Returns:
            用户文章列表
        """
        print_separator("测试3: 获取用户文章")
        
        if not user_id:
            print("❌ 未提供用户ID，跳过此测试")
            return []
        
        try:
            print(f"正在获取用户 {user_id} 的文章...")
            
            # 步骤1: 访问首页建立会话
            home_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://xueqiu.com/",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Cookie": self.cookie_str
            }
            
            self.session.get("https://xueqiu.com/", headers=home_headers, timeout=10)
            time.sleep(0.5)
            
            # 步骤2: 获取用户文章 - 使用与撰写投资笔记相同的API
            api_headers = home_headers.copy()
            api_url = f"https://xueqiu.com/statuses/user_timeline.json?user_id={user_id}&page=1&type=edit"
            
            print(f"请求API: {api_url}")
            
            response = self.session.get(api_url, headers=api_headers, timeout=10)
            
            print(f"API响应状态码: {response.status_code}")
            
            if response.status_code == 200 and response.text.strip().startswith('{'):
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
                print(f"⚠️  用户文章API获取失败，尝试获取热门文章作为替代...")
                return self.get_hot_articles()
        except Exception as e:
            print(f"⚠️  测试失败: {e}")
            import traceback
            traceback.print_exc()
            print(f"   尝试获取热门文章作为替代...")
            return self.get_hot_articles()
    
    def get_article_by_id(self, article_id):
        """
        通过文章ID获取文章详情
        
        Args:
            article_id: 文章ID
            
        Returns:
            文章数据
        """
        print_separator(f"通过文章ID获取详情: {article_id}")
        
        try:
            print(f"正在获取文章ID {article_id} 的详细信息...")
            
            # 步骤1：访问首页建立会话
            home_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
            if self.cookie_str:
                home_headers["Cookie"] = self.cookie_str
            
            self.session.get("https://xueqiu.com/", headers=home_headers, timeout=10)
            time.sleep(0.5)
            
            # 步骤2：访问文章页面
            article_page_headers = home_headers.copy()
            article_page_headers["Referer"] = "https://xueqiu.com/"
            article_page_url = f"https://xueqiu.com/1/{article_id}"
            self.session.get(article_page_url, headers=article_page_headers, timeout=10)
            time.sleep(0.5)
            
            # 步骤3：获取文章详情API
            api_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": article_page_url,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
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
                api_headers["Cookie"] = self.cookie_str
            
            api_url = f"https://xueqiu.com/statuses/show.json?id={article_id}"
            print(f"请求API: {api_url}")
            
            response = self.session.get(api_url, headers=api_headers, timeout=10)
            
            print(f"API响应状态码: {response.status_code}")
            print(f"API响应内容: {repr(response.text[:500])}")
            
            if response.status_code == 200:
                if response.text.strip().startswith('{'):
                    data = response.json()
                    
                    if 'id' in data:
                        print("✅ 文章详情获取成功")
                        return data
                    else:
                        print("⚠️  响应中未找到文章数据")
                        return None
                else:
                    print("❌ 响应不是JSON格式")
                    print(f"响应内容: {response.text[:200]}")
                    return None
            else:
                print(f"❌ 获取文章详情失败")
                return None
                
        except Exception as e:
            print(f"❌ 通过文章ID获取详情失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_article_attributes(self, article_data):
        """
        测试4: 获取文章属性
        
        Args:
            article_data: 文章数据
            
        Returns:
            文章属性
        """
        print_separator("测试4: 获取文章属性")
        
        if not article_data:
            print("❌ 未提供文章数据，跳过此测试")
            return None
        
        try:
            print("✅ 使用已有的文章数据")
            
            print("✅ 文章属性获取成功:")
            print(f"   标题: {article_data.get('title') or '无标题 (可能是短贴)'}")
            print(f"   ID: {article_data.get('id')}")
            print(f"   点赞: {article_data.get('like_count', 0)}")
            print(f"   评论: {article_data.get('reply_count', 0)}")
            print(f"   转发: {article_data.get('retweet_count', 0)}")
            print(f"   阅读: {article_data.get('view_count', 0)}")
            print(f"   收藏: {article_data.get('fav_count', 0)}")
            print(f"   是否专栏: {'是' if article_data.get('is_column', False) else '否'}")
            
            created_at = article_data.get("created_at")
            if created_at:
                created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
                print(f"   创建时间: {created_time}")
            
            return article_data
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return None
    
    def test_article_full_attributes(self, article_data, article_id):
        """
        测试get_article_full_attributes函数
        
        Args:
            article_data: 文章数据
            article_id: 文章ID
            
        Returns:
            文章完整属性
        """
        print_separator("测试5: get_article_full_attributes函数")
        
        if not article_data:
            print("❌ 未提供文章数据，跳过此测试")
            return None
        
        try:
            print(f"正在调用 get_article_full_attributes 函数...")
            
            article_info = get_article_full_attributes(article_data)
            
            print("✅ get_article_full_attributes 调用成功")
            print(f"\n   文章ID: {article_info.get('ID')}")
            print(f"   文章标题: {article_info.get('标题')}")
            
            article_attrs = article_info.get("属性", {})
            reward_info = article_info.get("打赏/悬赏信息", {})
            
            attrs_str = f"点赞: {article_attrs.get('点赞数', 0)} | 评论: {article_attrs.get('评论数', 0)} | 转发: {article_attrs.get('转发数', 0)} | 阅读: {article_attrs.get('阅读数', 0)} | 收藏: {article_attrs.get('收藏数', 0)} | 专栏: {article_attrs.get('是否专栏', '否')} | 原创: {article_attrs.get('是否原创声明', '否')} | 时间: {article_attrs.get('创建时间', '未知')} | 打赏: {reward_info.get('类型', '无')}"
            
            print(f"\n   📊 文章属性: {attrs_str}")
            
            return article_info
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 80)
        print("  雪球API功能测试 (参考backend实现)")
        print("=" * 80)
        
        results = {}
        
        # 测试1: 获取用户信息
        user_info = self.get_user_info()
        results['user_info'] = user_info
        
        if user_info:
            user_id = user_info['user_id']
            
            # 测试2: 获取关注列表
            following_list = self.get_following_list(user_id)
            results['following_list'] = following_list
            
            # 测试3: 获取用户文章
            articles = self.get_user_articles(user_id)
            results['articles'] = articles
            
            if articles:
                test_article = articles[0]
                
                # 测试4: 获取文章属性
                article_attrs = self.get_article_attributes(test_article)
                results['article_attrs'] = article_attrs
        
        print("\n" + "=" * 80)
        print("  测试总结")
        print("=" * 80)
        
        for key, value in results.items():
            status = "✅ 成功" if value else "❌ 失败"
            print(f"  {key}: {status}")
        
        return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='雪球API功能测试')
    parser.add_argument('--cookie', type=str, help='雪球Cookie字符串')
    parser.add_argument('--article-id', type=str, help='要测试的文章ID')
    parser.add_argument('--test-user-articles', action='store_true', help='测试获取用户文章并测试get_article_full_attributes函数')
    parser.add_argument('--test-topic-articles', action='store_true', help='测试获取话题文章并测试get_article_full_attributes函数')
    
    args = parser.parse_args()
    
    # 如果没有提供cookie，尝试从配置文件加载
    cookie = args.cookie
    default_user = None
    if not cookie:
        print("未提供--cookie参数，尝试从配置文件加载...")
        config_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'config', 'users.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                default_user_id = users_data.get('defaultUserId')
                users = users_data.get('users', [])
                default_user = next((u for u in users if u.get('id') == default_user_id), None)
                if default_user and default_user.get('cookie'):
                    cookie = default_user.get('cookie')
                    print(f"✅ 从配置文件加载Cookie成功")
            except Exception as e:
                print(f"从配置文件加载Cookie失败: {e}")
    
    if not cookie:
        print("❌ 错误: 请提供--cookie参数或配置默认用户")
        return
    
    # 创建测试实例
    tester = XueQiuAPITester(cookie)
    
    # 测试获取用户文章
    if args.test_user_articles:
        print(f"\n" + "=" * 80)
        print(f"  测试获取用户文章并测试get_article_full_attributes函数")
        print("=" * 80)
        
        # 获取用户信息
        user_info = tester.get_user_info()
        if user_info:
            user_id = user_info['user_id']
            
            # 获取用户文章
            articles = tester.get_user_articles(user_id, count=10)
            
            if articles:
                # 测试第一篇文章
                test_article = articles[0]
                test_article_id = str(test_article.get('id'))
                
                print(f"\n" + "=" * 80)
                print(f"  测试文章ID: {test_article_id}")
                print("=" * 80)
                
                # 显示文章属性
                tester.get_article_attributes(test_article)
                
                # 测试get_article_full_attributes函数
                tester.test_article_full_attributes(test_article, test_article_id)
    # 测试获取话题文章
    elif args.test_topic_articles:
        print(f"\n" + "=" * 80)
        print(f"  测试获取话题文章并测试get_article_full_attributes函数")
        print("=" * 80)
        
        # 获取话题文章
        print("正在获取话题文章...")
        articles = get_topic_articles(["悬赏问答"], cookie, max_count_per_topic=10)
        
        if articles:
            print(f"✅ 成功获取 {len(articles)} 篇话题文章")
            
            # 测试第一篇文章
            test_article = articles[0]
            test_article_id = str(test_article.get('id'))
            
            print(f"\n" + "=" * 80)
            print(f"  测试文章ID: {test_article_id}")
            print("=" * 80)
            
            # 显示文章属性
            tester.get_article_attributes(test_article)
            
            # 测试get_article_full_attributes函数
            tester.test_article_full_attributes(test_article, test_article_id)
            
            # 检查是否有fullArticleData
            if 'fullArticleData' in test_article and test_article['fullArticleData']:
                print(f"\n✅ 文章包含fullArticleData，使用完整数据再次测试...")
                tester.test_article_full_attributes(test_article['fullArticleData'], test_article_id)
    # 如果提供了文章ID，只测试该文章
    elif args.article_id:
        print(f"\n" + "=" * 80)
        print(f"  测试文章ID: {args.article_id}")
        print("=" * 80)
        
        # 首先尝试通过话题搜索获取文章
        print("尝试通过话题搜索获取文章...")
        topic_articles = get_topic_articles(["悬赏问答"], cookie, max_count_per_topic=20)
        
        # 查找目标文章
        target_article = None
        for art in topic_articles:
            if str(art.get('id')) == str(args.article_id):
                target_article = art
                break
        
        if target_article:
            print(f"✅ 在话题搜索结果中找到文章ID {args.article_id}")
            
            # 显示文章属性
            tester.get_article_attributes(target_article)
            
            # 测试get_article_full_attributes函数
            tester.test_article_full_attributes(target_article, args.article_id)
            
            # 检查是否有fullArticleData
            if 'fullArticleData' in target_article and target_article['fullArticleData']:
                print(f"\n✅ 文章包含fullArticleData，使用完整数据再次测试...")
                tester.test_article_full_attributes(target_article['fullArticleData'], args.article_id)
        else:
            print(f"❌ 在话题搜索中未找到文章ID {args.article_id}")
            print(f"话题搜索返回的文章ID: {[art.get('id') for art in topic_articles[:5]]}")
            
            # 尝试另一种方法：通过用户时间线查找文章
            if default_user:
                print(f"\n尝试通过用户时间线查找文章...")
                user_id = default_user.get('uid')
                if user_id:
                    articles = tester.get_user_articles(user_id, count=20)
                    
                    # 查找目标文章
                    target_article = None
                    for art in articles:
                        if str(art.get('id')) == str(args.article_id):
                            target_article = art
                            break
                    
                    if target_article:
                        print(f"✅ 在用户时间线中找到文章ID {args.article_id}")
                        
                        # 显示文章属性
                        tester.get_article_attributes(target_article)
                        
                        # 测试get_article_full_attributes函数
                        tester.test_article_full_attributes(target_article, args.article_id)
                    else:
                        print(f"❌ 在用户时间线中未找到文章ID {args.article_id}")
                        if articles:
                            print(f"用户最新的文章ID: {[art.get('id') for art in articles[:5]]}")
    else:
        # 运行所有测试
        tester.run_all_tests()


if __name__ == "__main__":
    main()
