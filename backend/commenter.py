import requests
import time
import random
import threading
import json
from datetime import datetime

class XueQiuCommenter:
    def __init__(self, ark_api_key, xueqiu_cookie, log_callback=None):
        self.ark_api_key = ark_api_key
        self.xueqiu_cookie = xueqiu_cookie
        self.processed_articles = set()
        self.current_max_id = None
        self.current_page = 1
        self.logs = []
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.is_running = False
        self.stats = {
            'processedArticles': 0,
            'successComments': 0,
            'failedAttempts': 0
        }
        self.log_callback = log_callback  # 日志回调函数
    
    def add_log(self, log_type, message, details=None):
        """添加日志"""
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'type': log_type,
            'message': message,
            'details': details
        }
        # 不使用锁，直接添加日志
        self.logs.append(log_entry)
        # 保持最近100条日志
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]
        # 打印日志到控制台，便于调试
        print(f"[{log_entry['timestamp']}] [{log_entry['type'].upper()}] {log_entry['message']}")
        
        # 调用回调函数，实时发送日志到前端
        if self.log_callback:
            self.log_callback(log_entry)

    def get_logs(self):
        """获取日志"""
        # 不使用锁，直接返回日志
        return self.logs.copy()

    def get_stats(self):
        """获取统计信息"""
        # 不使用锁，直接返回统计信息
        return self.stats.copy()
    
    def generate_comment(self, title, text):
        """使用火山引擎API生成评论"""
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.ark_api_key}"
        }
        prompt = f"你是资深投资者，写1-2句理性雪球评论，专业简洁。文章：{title} 内容：{text[:500]} 评论："
        payload = {
            "model": "doubao-seed-2-0-pro-260215",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            self.add_log('error', f'生成评论失败: {str(e)}')
            return "分析到位，学习了"
    
    def check_cookie_validity(self):
        """检查雪球Cookie是否有效"""
        self.add_log('info', '检查Cookie有效性...')
        headers = {
            "Cookie": self.xueqiu_cookie,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"
        }
        try:
            response = requests.get("https://xueqiu.com", headers=headers, timeout=10)
            if response.status_code == 200:
                if "登录" in response.text or "login" in response.text.lower():
                    self.add_log('error', 'Cookie无效，需要重新登录')
                    return False
                else:
                    self.add_log('success', 'Cookie有效')
                    return True
            else:
                self.add_log('error', f'访问失败，状态码: {response.status_code}')
                return False
        except Exception as e:
            self.add_log('error', f'检查失败: {str(e)}')
            return False
    
    def fetch_hot_articles(self):
        """抓取雪球热门文章，使用多个API端点"""
        headers = {
            "Cookie": self.xueqiu_cookie,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
            "Accept": "application/json",
            "Referer": "https://xueqiu.com",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # 使用多个API端点来获取更多文章
        apis = [
            {
                "url": "https://xueqiu.com/statuses/hot/list.json",
                "params": {"count": 20, "page": self.current_page},
                "name": "热门列表"
            },
            {
                "url": "https://xueqiu.com/v4/statuses/public_timeline_by_category.json",
                "params": {"since_id": -1, "max_id": -1, "count": 20, "category": 105},
                "name": "专栏文章"
            },
            {
                "url": "https://xueqiu.com/v4/statuses/public_timeline_by_category.json",
                "params": {"since_id": -1, "max_id": -1, "count": 20, "category": -1},
                "name": "全部文章"
            }
        ]
        
        all_articles = []
        
        for api in apis:
            self.add_log('info', f'使用API: {api["name"]}')
            url = api['url']
            params = api['params']
            
            # 对于热门列表API，添加分页参数
            if api['name'] == "热门列表" and self.current_max_id:
                params["max_id"] = self.current_max_id
            
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=10.0)
                resp.raise_for_status()
                
                # 打印响应内容以便调试
                self.add_log('info', f'API响应状态码: {resp.status_code}')
                
                data = resp.json()
                
                # 保存响应到文件
                with open(f"{api['name'].replace(' ', '_')}_articles.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # 检查响应结构
                if "items" in data:
                    # 热门列表API格式
                    items = data.get("items", [])
                    self.add_log('info', f'获取到 {len(items)} 个项目')
                    
                    # 更新分页信息
                    if "next_max_id" in data:
                        self.current_max_id = data["next_max_id"]
                        self.add_log('info', f'下一页max_id: {self.current_max_id}')
                    else:
                        # 如果没有next_max_id，增加页码
                        self.current_page += 1
                        self.add_log('info', f'没有next_max_id，页码增加到: {self.current_page}')
                    
                    # 转换items格式为我们需要的结构，并去重
                    for item in items:
                        if "original_status" in item:
                            article = item["original_status"]
                            article_id = article.get("id")
                            
                            # 跳过已处理的文章
                            if article_id in self.processed_articles:
                                continue
                            
                            # 提取作者UID
                            user = article.get("user", {})
                            user_id = str(user.get("id", ""))
                            
                            all_articles.append({
                                "id": article_id,
                                "title": article.get("title"),
                                "text": article.get("description", ""),
                                "user_id": user_id
                            })
                elif "list" in data:
                    # 公共时间线API格式
                    items = data.get("list", [])
                    self.add_log('info', f'获取到 {len(items)} 个项目')
                    
                    for item in items:
                        if "data" in item:
                            try:
                                data_str = item["data"]
                                article_data = json.loads(data_str)
                                article_id = article_data.get("id")
                                
                                # 跳过已处理的文章
                                if article_id in self.processed_articles:
                                    continue
                                
                                # 提取作者UID
                                user_id = str(article_data.get("user_id", ""))
                                
                                all_articles.append({
                                    "id": article_id,
                                    "title": article_data.get("title", article_data.get("text", "无标题")),
                                    "text": article_data.get("description", article_data.get("text", "")),
                                    "user_id": user_id
                                })
                            except Exception as e:
                                self.add_log('error', f'解析文章数据失败: {str(e)}')
                                pass
                else:
                    self.add_log('warning', f'未知的响应结构: {list(data.keys())}')
            except Exception as e:
                self.add_log('error', f'抓取文章失败: {str(e)}')
        
        # 去重
        unique_articles = []
        seen_ids = set()
        for article in all_articles:
            article_id = article.get("id")
            if article_id and article_id not in seen_ids and article_id not in self.processed_articles:
                seen_ids.add(article_id)
                unique_articles.append(article)
        
        self.add_log('info', f'总共获取到 {len(unique_articles)} 篇新文章')
        return unique_articles
    
    def post_comment(self, article_id, content):
        """使用雪球API发布评论"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
            "Referer": "https://xueqiu.com/",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Cookie": self.xueqiu_cookie
        }
        
        # 1. 文本审核
        self.add_log('info', '进行文本审核...')
        text_check_url = "https://xueqiu.com/statuses/text_check.json"
        text_check_data = {
            "text": f"<p>{content}</p>",
            "type": "3"
        }
        
        try:
            text_check_response = requests.post(text_check_url, headers=headers, data=text_check_data)
            if text_check_response.status_code != 200:
                return {"success": False, "message": "文本审核失败"}
        except Exception as e:
            return {"success": False, "message": f"文本审核请求失败: {str(e)}"}
        
        time.sleep(1)
        
        # 2. 获取会话token
        self.add_log('info', '获取会话token...')
        token_url = "https://xueqiu.com/provider/session/token.json"
        token_params = {
            "api_path": "/statuses/reply.json",
            "_": int(time.time() * 1000)
        }
        
        try:
            token_response = requests.get(token_url, headers=headers, params=token_params)
            if token_response.status_code != 200:
                return {"success": False, "message": "获取token失败"}
            
            token_data = token_response.json()
            session_token = token_data.get("session_token", "")
            if not session_token:
                return {"success": False, "message": "未获取到session_token"}
        except Exception as e:
            return {"success": False, "message": f"获取token请求失败: {str(e)}"}
        
        time.sleep(1)
        
        # 3. 发布评论
        self.add_log('info', '发布评论...')
        reply_url = "https://xueqiu.com/statuses/reply.json"
        reply_data = {
            "comment": f"<p>{content}</p>",
            "forward": "1",
            "id": article_id,
            "post_source": "htl",
            "post_position": "pc_home_feedcard",
            "session_token": session_token
        }
        
        try:
            reply_response = requests.post(reply_url, headers=headers, data=reply_data)
            if reply_response.status_code == 200:
                reply_data = reply_response.json()
                if "id" in reply_data:
                    self.processed_articles.add(article_id)
                    return {"success": True, "message": "评论发布成功", "comment_id": reply_data.get('id')}
                else:
                    return {"success": False, "message": "评论发布失败: 响应格式异常"}
            else:
                return {"success": False, "message": f"评论发布请求失败，状态码: {reply_response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"发布评论请求失败: {str(e)}"}
    
    def fetch_recommend_articles(self):
        """抓取雪球推荐文章，使用推荐流API"""
        headers = {
            "Cookie": self.xueqiu_cookie,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
            "Accept": "application/json",
            "Referer": "https://xueqiu.com",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # 使用推荐流API
        apis = [
            {
                "url": "https://xueqiu.com/v4/statuses/home_timeline.json",
                "params": {"since_id": "-1", "max_id": self.current_max_id if self.current_max_id else "-1", "count": 15, "source": "app"},
                "name": "个性化推荐流"
            },
            {
                "url": "https://xueqiu.com/v4/statuses/public_timeline_by_category.json",
                "params": {"since_id": "-1", "max_id": self.current_max_id if self.current_max_id else "-1", "count": 15, "category": "-1"},
                "name": "公开推荐流"
            }
        ]
        
        all_articles = []
        
        for api in apis:
            self.add_log('info', f'使用API: {api["name"]}')
            url = api['url']
            params = api['params']
            
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=10.0)
                self.add_log('info', f'API响应状态码: {resp.status_code}')
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # 保存响应到文件
                    with open(f"{api['name'].replace(' ', '_')}_articles.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    # 检查响应结构
                    if "statuses" in data:
                        items = data.get("statuses", [])
                        self.add_log('info', f'获取到 {len(items)} 个项目')
                        
                        # 更新分页信息
                        if "next_max_id" in data:
                            self.current_max_id = data["next_max_id"]
                            self.add_log('info', f'下一页max_id: {self.current_max_id}')
                        
                        # 提取文章信息
                        for item in items:
                            article_id = str(item.get("id"))
                            
                            # 跳过已处理的文章
                            if article_id in self.processed_articles:
                                continue
                            
                            # 提取作者UID
                            user = item.get("user", {})
                            user_id = str(user.get("id", ""))
                            
                            # 提取文章信息
                            title = item.get("title", item.get("text", "无标题"))[:100]
                            text = item.get("text", item.get("description", ""))
                            
                            all_articles.append({
                                "id": article_id,
                                "title": title,
                                "text": text,
                                "user_id": user_id
                            })
                    elif "list" in data:
                        # 公开推荐流API格式
                        items = data.get("list", [])
                        self.add_log('info', f'获取到 {len(items)} 个项目')
                        
                        # 更新分页信息
                        if "next_max_id" in data:
                            self.current_max_id = data["next_max_id"]
                            self.add_log('info', f'下一页max_id: {self.current_max_id}')
                        
                        # 提取文章信息
                        for item in items:
                            if "data" in item:
                                try:
                                    data_str = item["data"]
                                    article_data = json.loads(data_str)
                                    article_id = str(article_data.get("id"))
                                    
                                    # 跳过已处理的文章
                                    if article_id in self.processed_articles:
                                        continue
                                    
                                    # 提取作者UID
                                    user_id = str(article_data.get("user_id", ""))
                                    
                                    # 提取文章信息
                                    title = article_data.get("title", article_data.get("text", "无标题"))[:100]
                                    text = article_data.get("description", article_data.get("text", ""))
                                    
                                    all_articles.append({
                                        "id": article_id,
                                        "title": title,
                                        "text": text,
                                        "user_id": user_id
                                    })
                                except Exception as e:
                                    self.add_log('error', f'解析文章数据失败: {str(e)}')
                                    pass
                    else:
                        self.add_log('warning', f'未知的响应结构: {list(data.keys())}')
                else:
                    self.add_log('error', f'API请求失败，状态码: {resp.status_code}')
            except Exception as e:
                self.add_log('error', f'抓取文章失败: {str(e)}')
        
        # 去重
        unique_articles = []
        seen_ids = set()
        for article in all_articles:
            article_id = article.get("id")
            if article_id and article_id not in seen_ids and article_id not in self.processed_articles:
                seen_ids.add(article_id)
                unique_articles.append(article)
        
        self.add_log('info', f'总共获取到 {len(unique_articles)} 篇新文章')
        return unique_articles
    
    def follow_user(self, user_id):
        """关注雪球作者"""
        self.add_log('info', f'开始关注作者，UID: {user_id}')
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
            "Referer": f"https://xueqiu.com/{user_id}",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Cookie": self.xueqiu_cookie
        }
        
        # 关注作者的API
        follow_url = "https://xueqiu.com/friendships/create.json"
        follow_data = {
            "id": user_id
        }
        
        try:
            follow_response = requests.post(follow_url, headers=headers, data=follow_data)
            if follow_response.status_code == 200:
                follow_result = follow_response.json()
                # 检查是否关注成功
                if follow_result.get("success") or "success" in str(follow_result).lower():
                    self.add_log('success', f'成功关注作者，UID: {user_id}')
                    return {"success": True, "message": f"成功关注作者，UID: {user_id}"}
                else:
                    self.add_log('error', f'关注作者失败: {follow_result}')
                    return {"success": False, "message": f"关注作者失败: {follow_result}"}
            else:
                self.add_log('error', f'关注作者请求失败，状态码: {follow_response.status_code}')
                return {"success": False, "message": f"关注作者请求失败，状态码: {follow_response.status_code}"}
        except Exception as e:
            self.add_log('error', f'关注作者请求失败: {str(e)}')
            return {"success": False, "message": f"关注作者请求失败: {str(e)}"}
    
    def run_task(self, daily_limit=30, delay_min=30, delay_max=120, test_mode=False, task_type='hot'):
        """运行评论任务"""
        try:
            self.is_running = True
            self.stop_event.clear()
            
            self.add_log('info', f'开始自动评论任务 (热门帖)' if task_type == 'hot' else f'开始自动评论任务 (推荐帖)', {
                'dailyLimit': daily_limit,
                'testMode': test_mode,
                'taskType': task_type
            })
            
            # 检查Cookie有效性
            if not self.check_cookie_validity():
                self.add_log('error', 'Cookie无效，任务停止')
                self.is_running = False
                return
            
            count = 0
            empty_page_count = 0
            
            while count < daily_limit and not self.stop_event.is_set():
                try:
                    # 根据任务类型抓取文章
                    if task_type == 'hot':
                        self.add_log('info', '正在抓取热门文章...')
                        articles = self.fetch_hot_articles()
                    else:
                        self.add_log('info', '正在抓取推荐文章...')
                        articles = self.fetch_recommend_articles()
                except Exception as e:
                    self.add_log('error', f'抓取文章失败: {str(e)}')
                    time.sleep(30)
                    continue
                
                if not articles:
                    empty_page_count += 1
                    self.add_log('warning', f'未抓取到新文章，连续空页次数: {empty_page_count}')
                    
                    if empty_page_count >= 3:
                        self.add_log('info', '连续多次无新文章，重置max_id')
                        self.current_max_id = None
                        empty_page_count = 0
                        time.sleep(60)
                    else:
                        time.sleep(30)
                    continue
                
                empty_page_count = 0
                self.add_log('info', f'成功抓取到 {len(articles)} 篇新文章')
                
                for article in articles:
                    if count >= daily_limit or self.stop_event.is_set():
                        break
                    
                    try:
                        title = article.get("title", "无标题")
                        text = article.get("text", "")
                        article_id = article.get("id", "")
                        
                        if not article_id:
                            self.add_log('warning', f'跳过无ID的文章: {title}')
                            continue
                        
                        self.add_log('info', f'处理文章: {title}', {
                            'articleId': article_id,
                            'articleTitle': title
                        })
                        
                        # 生成评论
                        self.add_log('info', '正在生成评论...')
                        comment = self.generate_comment(title, text)
                        self.add_log('info', f'生成评论: {comment}', {
                            'comment': comment
                        })
                        
                        # 发布评论
                        if not test_mode:
                            result = self.post_comment(article_id, comment)
                            
                            # 直接更新统计信息，不使用锁
                            self.stats['processedArticles'] += 1
                            
                            if result['success']:
                                # 直接更新统计信息，不使用锁
                                self.stats['successComments'] += 1
                                self.add_log('success', '评论发布成功', {
                                    'articleTitle': title,
                                    'comment': comment,
                                    'commentId': result.get('comment_id')
                                })
                            else:
                                # 直接更新统计信息，不使用锁
                                self.stats['failedAttempts'] += 1
                                self.add_log('error', f'评论发布失败: {result["message"]}', {
                                    'articleTitle': title
                                })
                                
                                # 评论失败后关注作者
                                user_id = article.get('user_id')
                                if user_id:
                                    self.add_log('info', f'评论失败，尝试关注作者，UID: {user_id}')
                                    self.follow_user(user_id)
                                    time.sleep(2)
                        else:
                            # 测试模式
                            # 直接更新统计信息，不使用锁
                            self.stats['processedArticles'] += 1
                            self.stats['successComments'] += 1
                            self.add_log('success', '测试模式 - 评论生成成功（未发布）', {
                                'articleTitle': title,
                                'comment': comment
                            })
                        
                        count += 1
                        
                        # 随机延迟
                        delay = random.randint(delay_min, delay_max)
                        self.add_log('info', f'等待 {delay} 秒后继续...')
                        
                        # 检查是否需要停止
                        for _ in range(delay):
                            if self.stop_event.is_set():
                                break
                            time.sleep(1)
                            
                    except Exception as e:
                        # 直接更新统计信息，不使用锁
                        self.stats['failedAttempts'] += 1
                        self.add_log('error', f'处理文章失败: {str(e)}', {
                            'articleTitle': article.get('title', '未知')
                        })
                        time.sleep(10)
                        continue
        except Exception as e:
            self.add_log('error', f'评论任务出错: {str(e)}')
        finally:
            self.add_log('info', f'任务完成，共处理 {count} 篇文章')
            self.is_running = False
    
    def stop(self):
        """停止任务"""
        self.stop_event.set()
        self.is_running = False  # 立即标记为停止状态
        self.add_log('info', '正在停止任务...')
