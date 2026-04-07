import requests
import urllib.parse
import time
import json
import os
import re
from bs4 import BeautifulSoup

class TopicArticleFetcher:
    def __init__(self, cookie):
        self.cookie = cookie
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Cookie": cookie.strip(),
            "Referer": "https://xueqiu.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        self.session = requests.Session()
    
    def search_articles_by_topic(self, topic_name, max_count=100):
        """
        根据话题搜索文章
        
        Args:
            topic_name: 话题名称
            max_count: 最多获取的文章数量
            
        Returns:
            文章列表
        """
        print(f"[{time.strftime('%H:%M:%S')}] 开始搜索话题: {topic_name}, 目标数量: {max_count}")
        
        articles = []
        
        # 步骤1：尝试使用搜索API
        print(f"[{time.strftime('%H:%M:%S')}] 尝试使用搜索API获取真实文章...")
        try:
            # 模拟完整的浏览器流程
            print(f"[{time.strftime('%H:%M:%S')}] 正在访问雪球首页建立会话...")
            
            # 访问首页
            home_headers = self.headers.copy()
            home_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            home_headers["Referer"] = ""
            self.session.get("https://xueqiu.com/", headers=home_headers, timeout=10)
            time.sleep(1)
            
            # 访问话题页面
            encoded_topic = urllib.parse.quote(topic_name)
            topic_page_url = f"https://xueqiu.com/k?q={encoded_topic}"
            print(f"[{time.strftime('%H:%M:%S')}] 正在访问话题页面: {topic_page_url}")
            
            topic_headers = self.headers.copy()
            topic_headers["Referer"] = "https://xueqiu.com/"
            topic_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            self.session.get(topic_page_url, headers=topic_headers, timeout=10)
            time.sleep(1)
            
            # 使用搜索API
            print(f"[{time.strftime('%H:%M:%S')}] 使用搜索API获取文章...")
            api_articles = self.search_with_search_api(topic_name, max_count)
            
            if api_articles and len(api_articles) > 0:
                for article in api_articles:
                    article['can_comment'] = True
                articles = api_articles
                print(f"[{time.strftime('%H:%M:%S')}] 搜索API成功，获取 {len(articles)} 篇真实文章")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 搜索API失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 步骤2：如果API失败或文章太少，从HTML解析补充
        if len(articles) < max_count:
            print(f"[{time.strftime('%H:%M:%S')}] 使用HTML解析补充文章...")
            html_articles = self.parse_articles_from_topic_page(topic_name, max_count - len(articles))
            
            for article in html_articles:
                article['can_comment'] = False
                articles.append(article)
            
            print(f"[{time.strftime('%H:%M:%S')}] HTML解析补充 {len(html_articles)} 篇文章")
        
        print(f"话题 '{topic_name}' 搜索完成，共获取 {len(articles)} 篇文章")
        return articles
    
    def search_with_search_api(self, topic_name, max_count=100):
        """使用搜索API获取文章"""
        articles = []
        page = 1
        count_per_page = 20
        encoded_topic = urllib.parse.quote(topic_name)
        
        while len(articles) < max_count:
            # 使用搜索API
            url = f"https://xueqiu.com/query/v1/search/status.json?q={encoded_topic}&sort=time&page={page}&count={count_per_page}"
            
            # 设置完整的请求头（不手动设置Cookie，让session自动处理）
            search_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": f"https://xueqiu.com/k?q={encoded_topic}",
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
            
            print(f"[{time.strftime('%H:%M:%S')}] 请求搜索API: {url}")
            
            try:
                response = self.session.get(url, headers=search_headers, timeout=10)
                
                print(f"[{time.strftime('%H:%M:%S')}] 搜索API响应状态码: {response.status_code}")
                if response.status_code == 200:
                    print(f"[{time.strftime('%H:%M:%S')}] 响应内容前500字符: {response.text[:500]}")
                
                if response.status_code != 200:
                    print(f"搜索API请求失败，状态码: {response.status_code}")
                    break
                
                # 检查是否是JSON
                if not response.text.strip().startswith('{'):
                    print(f"[{time.strftime('%H:%M:%S')}] 响应不是JSON，可能被WAF拦截")
                    break
                
                data = response.json()
                post_list = data.get('list', [])
                
                if not post_list:
                    print("没有更多文章了")
                    break
                
                print(f"第{page}页获取到 {len(post_list)} 篇文章")
                
                for post in post_list:
                    if len(articles) >= max_count:
                        break
                    
                    article_info = self.parse_article(post)
                    if article_info:
                        articles.append(article_info)
                
                page += 1
                time.sleep(0.5)
                
            except Exception as e:
                print(f"搜索API异常: {str(e)}")
                import traceback
                traceback.print_exc()
                break
        
        return articles
    
    def parse_articles_from_topic_page(self, topic_name, max_count=100):
        """从话题页面HTML解析文章"""
        articles = []
        
        try:
            # 访问话题页面
            encoded_topic = urllib.parse.quote(topic_name)
            topic_page_url = f"https://xueqiu.com/k?q={encoded_topic}"
            
            # 先访问首页建立会话
            home_headers = self.headers.copy()
            home_headers["Referer"] = ""
            self.session.get("https://xueqiu.com/", headers=home_headers, timeout=10)
            time.sleep(1)
            
            topic_headers = self.headers.copy()
            topic_headers["Referer"] = "https://xueqiu.com/"
            topic_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            response = self.session.get(topic_page_url, headers=topic_headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 尝试从script标签中提取JSON数据
                script_tags = soup.find_all('script')
                print(f"[{time.strftime('%H:%M:%S')}] 找到 {len(script_tags)} 个script标签")
                
                for script in script_tags:
                    script_text = script.string
                    if script_text:
                        # 尝试提取window.__INITIAL_STATE__或类似数据
                        if 'window.__' in script_text or 'list' in script_text:
                            # 使用正则表达式尝试提取JSON
                            json_matches = re.findall(r'\{[^{}]*"list"[^{}]*\[(?:[^\[\]]|\[(?:[^\[\]]|\[[^\[\]]*\])*\])*\]\}', script_text)
                            if json_matches:
                                for json_str in json_matches[:1]:
                                    try:
                                        data = json.loads(json_str)
                                        if 'list' in data:
                                            post_list = data['list']
                                            for idx, post in enumerate(post_list):
                                                if len(articles) >= max_count:
                                                    break
                                                article_info = self.parse_article(post)
                                                if article_info:
                                                    articles.append(article_info)
                                                    print(f"[{time.strftime('%H:%M:%S')}] HTML解析文章 {idx+1}: {article_info['title'][:30]}...")
                                    except Exception as e:
                                        print(f"解析script中的JSON失败: {e}")
                                        continue
                
                # 如果从script中没找到，尝试直接解析HTML结构
                if len(articles) == 0:
                    print(f"[{time.strftime('%H:%M:%S')}] 从script未找到数据，尝试直接解析HTML...")
                    # 查找包含status_id或data-id的元素
                    status_elements = soup.find_all(['div', 'article'], attrs={'data-id': True})
                    if not status_elements:
                        status_elements = soup.find_all(lambda tag: tag.has_attr('data-status-id'))
                    
                    print(f"[{time.strftime('%H:%M:%S')}] 找到 {len(status_elements)} 个状态元素")
                    
                    for idx, elem in enumerate(status_elements):
                        if len(articles) >= max_count:
                            break
                        
                        try:
                            # 提取文章ID
                            status_id = elem.get('data-id') or elem.get('data-status-id')
                            
                            # 提取标题和内容
                            text = ""
                            title_elem = elem.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                            if title_elem:
                                text = title_elem.get_text(strip=True)
                            
                            if not text:
                                content_elem = elem.find(['p', 'div'], class_=lambda x: x and ('content' in str(x).lower() or 'text' in str(x).lower()))
                                if content_elem:
                                    text = content_elem.get_text(strip=True, separator='\n')
                            
                            if text:
                                # 生成唯一ID
                                article_id = status_id or f"topic_html_{int(time.time())}_{idx}"
                                
                                article_info = {
                                    'id': article_id,
                                    'uid': article_id,
                                    'title': text[:60] + '...' if len(text) > 60 else text,
                                    'text': text,
                                    'textPreview': text[:180],
                                    'user': {
                                        'id': None,
                                        'screen_name': topic_name,
                                        'profile_image': ''
                                    },
                                    'created_at': int(time.time() * 1000),
                                    'reward_count': 0,
                                    'has_reward': False,
                                    'like_count': 0,
                                    'comment_count': 0,
                                    'retweet_count': 0,
                                    'view_count': 0,
                                    'source': '雪球话题'
                                }
                                articles.append(article_info)
                                print(f"[{time.strftime('%H:%M:%S')}] HTML解析文章 {idx+1}: {article_info['title']}")
                        except Exception as e:
                            print(f"解析HTML文章 {idx} 异常: {e}")
                            continue
        except Exception as e:
            print(f"HTML解析话题页面异常: {e}")
            import traceback
            traceback.print_exc()
        
        return articles
    
    def parse_article(self, post):
        """
        解析文章信息
        
        Args:
            post: 文章数据
            
        Returns:
            解析后的文章信息
        """
        try:
            article_id = post.get('id')
            user_info = post.get('user', {})
            
            text = post.get('text', '')
            text_preview = text[:150] if text else ''
            
            # 检查是否有打赏
            reward_count = post.get('reward_count', 0)
            reward_expired = post.get('reward_expired', False)
            
            return {
                'id': article_id,
                'uid': article_id,
                'title': post.get('title', ''),
                'text': text,
                'textPreview': text_preview,
                'user': {
                    'id': user_info.get('id'),
                    'screen_name': user_info.get('screen_name', ''),
                    'profile_image': user_info.get('profile_image', '')
                },
                'created_at': post.get('created_at'),
                'reward_count': reward_count,
                'reward_expired': reward_expired,
                'has_reward': reward_count > 0,
                'like_count': post.get('like_count', 0),
                'comment_count': post.get('comment_count', 0),
                'retweet_count': post.get('retweet_count', 0),
                'view_count': post.get('view_count', 0),
                'source': post.get('source', '')
            }
        except Exception as e:
            print(f"解析文章信息异常: {str(e)}")
            return None

def get_topic_articles(topic_names, cookie, max_count_per_topic=100):
    """
    获取多个话题的文章
    
    Args:
        topic_names: 话题名称列表
        cookie: 雪球cookie
        max_count_per_topic: 每个话题最多获取的文章数量
        
    Returns:
        所有文章列表
    """
    fetcher = TopicArticleFetcher(cookie)
    all_articles = []
    
    for topic_name in topic_names:
        articles = fetcher.search_articles_by_topic(topic_name, max_count_per_topic)
        for article in articles:
            article['topic'] = topic_name
            all_articles.append(article)
    
    return all_articles
