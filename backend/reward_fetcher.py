import requests
import json
import time
import urllib.parse
from bs4 import BeautifulSoup
import re


class RewardArticleFetcher:
    """悬赏问答文章获取器"""
    
    def __init__(self, cookie):
        self.cookie = cookie.strip()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        self.session = requests.Session()
    
    def fetch_reward_articles(self, max_count=50):
        """获取悬赏问答文章"""
        print(f"[{time.strftime('%H:%M:%S')}] 开始获取悬赏问答文章，目标数量: {max_count}")
        
        articles = []
        
        # 步骤1：尝试使用话题搜索
        print(f"[{time.strftime('%H:%M:%S')}] 尝试使用话题搜索获取真实文章...")
        try:
            from topic_fetcher import get_topic_articles
            api_articles = get_topic_articles(["悬赏问答"], self.cookie, max_count)
            
            if api_articles and len(api_articles) > 0:
                # 为每篇文章添加悬赏标记
                for article in api_articles:
                    article['has_reward'] = True
                    article['is_reward_article'] = True
                    article['can_comment'] = True
                
                articles = api_articles
                print(f"[{time.strftime('%H:%M:%S')}] 话题搜索成功，获取 {len(articles)} 篇真实文章")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 话题搜索失败: {e}")
        
        # 步骤2：如果话题搜索失败或文章太少，使用HTML解析补充
        if len(articles) < max_count:
            print(f"[{time.strftime('%H:%M:%S')}] 使用HTML解析补充文章...")
            
            try:
                # 访问悬赏问答页面
                reward_url = "https://xueqiu.com/hybrid/ask/offer"
                
                # 先访问首页建立会话
                home_headers = self.headers.copy()
                home_headers["Referer"] = ""
                self.session.get("https://xueqiu.com/", headers=home_headers, timeout=10)
                time.sleep(1)
                
                reward_headers = self.headers.copy()
                reward_headers["Referer"] = "https://xueqiu.com/"
                response = self.session.get(reward_url, headers=reward_headers, timeout=10)
                
                if response.status_code == 200:
                    # 保存页面内容用于调试
                    with open('/tmp/reward_page.html', 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    
                    # 直接从整个响应文本中提取所有 id:数字 模式
                    print(f"[{time.strftime('%H:%M:%S')}] 正在从响应中提取文章ID...")
                    
                    # 直接在整个响应中查找所有 id:数字 的模式
                    id_matches = re.findall(r'id:\s*(\d+)', response.text)
                    
                    # 去重并过滤掉太小的数字（可能是其他数据）
                    unique_ids = []
                    seen = set()
                    for aid in id_matches:
                        if aid not in seen and len(aid) > 5:  # 文章ID通常比较长
                            seen.add(aid)
                            unique_ids.append(aid)
                    
                    id_matches = unique_ids
                    print(f"[{time.strftime('%H:%M:%S')}] 提取到 {len(id_matches)} 个文章ID: {id_matches[:5]}...")
                    
                    # 同时从HTML中提取问题内容和悬赏金额
                    soup = BeautifulSoup(response.text, 'html.parser')
                    offer_items = soup.find_all('div', class_='offer__item')
                    
                    print(f"[{time.strftime('%H:%M:%S')}] HTML解析找到 {len(offer_items)} 个悬赏文章条目")
                    
                    for idx, item in enumerate(offer_items):
                        if len(articles) >= max_count:
                            break
                        
                        try:
                            # 获取文章ID
                            article_id = id_matches[idx] if idx < len(id_matches) else None
                            
                            # 获取悬赏金额
                            tag_elem = item.find('span', class_='offer__tag')
                            reward_amount = 0.0
                            if tag_elem:
                                tag_text = tag_elem.get_text(strip=True)
                                amount_match = re.search(r'¥([\d.]+)', tag_text)
                                if amount_match:
                                    reward_amount = float(amount_match.group(1))
                            
                            # 获取问题内容
                            question_div = item.find('div', class_='offer__question')
                            text = ""
                            if question_div:
                                question_divs = question_div.find_all('div')
                                if question_divs:
                                    text = question_divs[0].get_text(strip=True, separator='\n')
                                else:
                                    text = question_div.get_text(strip=True, separator='\n')
                            
                            # 如果没有找到真实ID，才使用生成的ID
                            if not article_id:
                                article_id = f"reward_html_{int(time.time())}_{idx}"
                                can_comment = False
                            else:
                                can_comment = True
                            
                            article_info = {
                                'id': article_id,
                                'uid': article_id,
                                'title': text[:60] + '...' if len(text) > 60 else text,
                                'text': text,
                                'textPreview': text[:180],
                                'user': {
                                    'id': None,
                                    'screen_name': '悬赏问答',
                                    'profile_image': ''
                                },
                                'created_at': int(time.time() * 1000),
                                'reward_amount': reward_amount,
                                'reward_count': 1,
                                'has_reward': True,
                                'is_reward_article': True,
                                'can_comment': can_comment,
                                'like_count': 0,
                                'comment_count': 0,
                                'retweet_count': 0,
                                'view_count': 0,
                                'source': '雪球悬赏'
                            }
                            
                            articles.append(article_info)
                            status = "可评论" if can_comment else "不可评论"
                            print(f"[{time.strftime('%H:%M:%S')}] 文章 {idx+1}: ID={article_id}, 悬赏 ¥{reward_amount}, {status}")
                            
                        except Exception as e:
                            print(f"解析文章 {idx} 异常: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                    
            except Exception as e:
                print(f"HTML解析异常: {str(e)}")
                import traceback
                traceback.print_exc()
        
        print(f"[{time.strftime('%H:%M:%S')}] 悬赏问答文章获取完成，共获取 {len(articles)} 篇文章")
        return articles
    
    def search_reward_articles_with_api(self, max_count=50):
        """使用搜索API搜索悬赏相关文章"""
        articles = []
        
        try:
            # 首先访问更多页面建立会话
            print(f"[{time.strftime('%H:%M:%S')}] 访问更多页面建立会话...")
            
            # 访问悬赏问答页面后再访问其他页面
            pages = [
                "https://xueqiu.com/",
                "https://xueqiu.com/hybrid/ask",
                "https://xueqiu.com/hybrid/ask/offer"
            ]
            
            for page_url in pages:
                headers = self.headers.copy()
                headers["Referer"] = "https://xueqiu.com/"
                headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                self.session.get(page_url, headers=headers, timeout=10)
                time.sleep(1)
            
            # 使用搜索API - 搜索"悬赏问答"相关文章
            search_url = "https://xueqiu.com/query/v1/search/status.json?q=悬赏问答&sort=time&page=1&count=50"
            
            print(f"[{time.strftime('%H:%M:%S')}] 请求搜索API: {search_url}")
            
            search_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://xueqiu.com/hybrid/ask/offer",
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
            
            # 如果有cookie，添加到请求头
            if self.cookie:
                search_headers["Cookie"] = self.cookie
            
            response = self.session.get(search_url, headers=search_headers, timeout=10)
            
            print(f"[{time.strftime('%H:%M:%S')}] 搜索API响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                print(f"[{time.strftime('%H:%M:%S')}] 响应内容前500字符: {response.text[:500]}...")
                
                if response.text.strip().startswith('{'):
                    data = response.json()
                    
                    if 'list' in data:
                        for post in data['list']:
                            if len(articles) >= max_count:
                                break
                            
                            article_info = self.parse_article(post)
                            if article_info:
                                articles.append(article_info)
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 响应不是JSON，尝试从话题搜索...")
                    # 如果搜索API失败，尝试用话题搜索
                    from topic_fetcher import get_topic_articles
                    articles = get_topic_articles(["悬赏问答"], self.cookie, max_count)
            else:
                print(f"搜索API请求失败，状态码: {response.status_code}")
                # 如果搜索API失败，尝试用话题搜索
                from topic_fetcher import get_topic_articles
                articles = get_topic_articles(["悬赏问答"], self.cookie, max_count)
                
        except Exception as e:
            print(f"搜索API异常: {str(e)}")
            import traceback
            traceback.print_exc()
            # 异常时也尝试用话题搜索
            try:
                from topic_fetcher import get_topic_articles
                articles = get_topic_articles(["悬赏问答"], self.cookie, max_count)
            except:
                pass
        
        return articles
    
    def parse_reward_article(self, post):
        """解析悬赏文章信息"""
        try:
            article_id = post.get('id') or post.get('status_id')
            user_info = post.get('user', {})
            
            text = post.get('text', '') or post.get('description', '')
            text_preview = text[:150] if text else ''
            
            reward_amount = post.get('reward_amount') or post.get('bonus_amount') or 0
            
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
                'reward_amount': reward_amount,
                'reward_count': post.get('reward_count', 0),
                'has_reward': reward_amount > 0,
                'like_count': post.get('like_count', 0),
                'comment_count': post.get('comment_count', 0) or post.get('reply_count', 0),
                'retweet_count': post.get('retweet_count', 0),
                'view_count': post.get('view_count', 0),
                'source': post.get('source', '')
            }
        except Exception as e:
            print(f"解析悬赏文章信息异常: {str(e)}")
            return None
    
    def parse_article(self, post):
        """解析普通文章信息"""
        try:
            article_id = post.get('id')
            user_info = post.get('user', {})
            
            text = post.get('text', '')
            text_preview = text[:150] if text else ''
            
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


def get_reward_articles(cookie, max_count=50):
    """获取悬赏问答文章"""
    fetcher = RewardArticleFetcher(cookie)
    return fetcher.fetch_reward_articles(max_count)
