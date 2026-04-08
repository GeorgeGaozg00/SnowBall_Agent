import requests
import time
import random
import json

# 1. 你的配置
#XUEQIU_COOKIE = "xq_a_token=XXX; xq_r_token=XXX"  # 浏览器F12复制
XUEQIU_COOKIE = "xq_a_token=d60873c46cdcf7dfa29911900810768e779318a4; xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOjU2Nzg1OTczMjYsImlzcyI6InVjIiwiZXhwIjoxNzc3NzcxODAwLCJjdG0iOjE3NzUxNzk4MDAwMjMsImNpZCI6ImQ5ZDBuNEFadXAifQ.O7yHgZo1kPBoHyiRabvJEJeJbpnqtzcszqg9BjPzRTRyvTmtGK-1q8r1W-B8i8mrktJdg8NIUeGZHpJLthgtriGsw6DP61kGTE566TkzSIU8vPESw0fgQArDOs-ospFMtykSrR9EWfkJ5CevE9sfeSEya2Z0dZjnF5TzFIBaxPBGlOjWNxfZRfG4IVDobK2jIRroyf6jUA1ehM91n87E0lNPCz4vM7ppSrJTML5PDO8V8oDb1VJHrU0dM1VBjoB0_rc44Fr5NtVpCD2Q3SXmlL2rLyA_-V9wqWFqGUUAyCa2r2324nBNdePJofb4XJCHfeMOFombC2Gs43ba-xGhOw; xq_r_token=1c75559aedff3a301c44a9d3881b136637f01197"  # 浏览器F12复制
ARK_API_KEY = "39e67fe4-bbd5-4c0f-bf63-8629f873038b"
COMMENT_DELAY = (30, 120)  # 秒
DAILY_LIMIT = 60

# 全局变量：记录已处理的文章ID和分页信息
processed_articles = set()
current_max_id = None
current_page = 1

# 2. AI生成评论
def generate_comment(title, text):
    """使用火山引擎API生成评论"""
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ARK_API_KEY}"
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
        print(f"生成评论失败: {str(e)}")
        return "分析到位，学习了"

# 3. 检查Cookie有效性
def check_cookie_validity():
    """检查雪球Cookie是否有效"""
    print("检查Cookie有效性...")
    headers = {
        "Cookie": XUEQIU_COOKIE,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"
    }
    try:
        response = requests.get("https://xueqiu.com", headers=headers, timeout=10)
        if response.status_code == 200:
            if "登录" in response.text or "login" in response.text.lower():
                print("✗ Cookie无效，需要重新登录")
                return False
            else:
                print("✓ Cookie有效")
                return True
        else:
            print(f"✗ 访问失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 检查失败: {str(e)}")
        return False

# 4. 抓取热门文章 - 改进版
def fetch_hot_articles():
    """抓取雪球热门文章，改进版"""
    global current_max_id, current_page, processed_articles
    
    # 创建会话
    session = requests.Session()
    
    # 完整的请求头
    headers = {
        "Cookie": XUEQIU_COOKIE,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://xueqiu.com/",
        "Origin": "https://xueqiu.com",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }
    
    # 先访问首页建立会话
    print("访问雪球首页建立会话...")
    try:
        home_response = session.get("https://xueqiu.com/", headers=headers)
        print(f"首页访问状态码: {home_response.status_code}")
    except Exception as e:
        print(f"访问首页失败: {str(e)}")
        return []
    
    # 使用多个API端点来获取更多文章
    apis = [
        {
            "url": "https://xueqiu.com/statuses/hot/list.json",
            "params": {"count": 20, "page": current_page},
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
        },
        # 尝试新的API端点
        {
            "url": "https://xueqiu.com/stocks/statuses/hot.json",
            "params": {"count": 20},
            "name": "股票热门"
        },
        {
            "url": "https://xueqiu.com/statuses/stock.json",
            "params": {"count": 20},
            "name": "股票动态"
        }
    ]
    
    all_articles = []
    
    for api in apis:
        print(f"\n使用API: {api['name']}")
        url = api['url']
        params = api['params']
        
        # 对于热门列表API，添加分页参数
        if api['name'] == "热门列表" and current_max_id:
            params["max_id"] = current_max_id
        
        try:
            resp = session.get(url, headers=headers, params=params, timeout=10.0)
            print(f"API响应状态码: {resp.status_code}")
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    
                    # 保存响应到文件
                    with open(f"{api['name'].replace(' ', '_')}_articles.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    # 检查响应结构
                    if "items" in data:
                        # 热门列表API格式
                        items = data.get("items", [])
                        print(f"获取到 {len(items)} 个项目")
                        
                        # 更新分页信息
                        if "next_max_id" in data:
                            current_max_id = data["next_max_id"]
                            print(f"下一页max_id: {current_max_id}")
                        else:
                            # 如果没有next_max_id，增加页码
                            current_page += 1
                            print(f"没有next_max_id，页码增加到: {current_page}")
                        
                        # 转换items格式为我们需要的结构，并去重
                        for item in items:
                            if "original_status" in item:
                                article = item["original_status"]
                                article_id = article.get("id")
                                
                                # 跳过已处理的文章
                                if article_id in processed_articles:
                                    continue
                                
                                # 提取作者UID
                                user = article.get("user", {})
                                user_id = user.get("id", "")
                                
                                all_articles.append({
                                    "id": article_id,
                                    "title": article.get("title"),
                                    "text": article.get("description", ""),
                                    "user_id": user_id
                                })
                    elif "list" in data:
                        # 公共时间线API格式
                        items = data.get("list", [])
                        print(f"获取到 {len(items)} 个项目")
                        
                        for item in items:
                            if "data" in item:
                                try:
                                    data_str = item["data"]
                                    article_data = json.loads(data_str)
                                    article_id = article_data.get("id")
                                    
                                    # 跳过已处理的文章
                                    if article_id in processed_articles:
                                        continue
                                        
                                    # 提取作者UID
                                    user_id = article_data.get("user_id", "")
                                    
                                    all_articles.append({
                                        "id": article_id,
                                        "title": article_data.get("title", article_data.get("text", "无标题")),
                                        "text": article_data.get("description", article_data.get("text", "")),
                                        "user_id": user_id
                                    })
                                except Exception as e:
                                    pass
                    elif "statuses" in data:
                        # 可能的新格式
                        items = data.get("statuses", [])
                        print(f"获取到 {len(items)} 个项目")
                        
                        for item in items:
                            article_id = item.get("id")
                            
                            # 跳过已处理的文章
                            if article_id in processed_articles:
                                continue
                            
                            # 提取作者UID
                            user = item.get("user", {})
                            user_id = user.get("id", "")
                            
                            all_articles.append({
                                "id": article_id,
                                "title": item.get("title", item.get("text", "无标题")),
                                "text": item.get("description", item.get("text", "")),
                                "user_id": user_id
                            })
                    else:
                        print(f"未知的响应结构: {list(data.keys())}")
                except Exception as e:
                    print(f"解析响应失败: {str(e)}")
                    print(f"响应内容: {resp.text[:500]}")
            else:
                print(f"API请求失败，状态码: {resp.status_code}")
                print(f"响应内容: {resp.text[:500]}")
        except Exception as e:
            print(f"抓取文章失败: {str(e)}")
    
    # 去重
    unique_articles = []
    seen_ids = set()
    for article in all_articles:
        article_id = article.get("id")
        if article_id and article_id not in seen_ids and article_id not in processed_articles:
            seen_ids.add(article_id)
            unique_articles.append(article)
    
    print(f"\n总共获取到 {len(unique_articles)} 篇新文章")
    return unique_articles

# 5. 自动发布评论 - 基于API
def post_comment(article_id, content):
    """使用雪球API发布评论"""
    print("开始使用API发布评论...")
    
    # 创建会话
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": XUEQIU_COOKIE
    }
    
    # 1. 文本审核
    print("1. 进行文本审核...")
    text_check_url = "https://xueqiu.com/statuses/text_check.json"
    text_check_data = {
        "text": f"<p>{content}</p>",
        "type": "3"
    }
    
    try:
        text_check_response = session.post(text_check_url, headers=headers, data=text_check_data)
        if text_check_response.status_code != 200:
            print("❌ 文本审核失败")
            print(f"响应内容: {text_check_response.text}")
            return {"success": False, "message": "文本审核失败"}
    except Exception as e:
        print(f"❌ 文本审核请求失败: {str(e)}")
        return {"success": False, "message": f"文本审核请求失败: {str(e)}"}
    
    time.sleep(1)  # 避免请求过快
    
    # 2. 获取会话token
    print("2. 获取会话token...")
    token_url = "https://xueqiu.com/provider/session/token.json"
    token_params = {
        "api_path": "/statuses/reply.json",
        "_": int(time.time() * 1000)
    }
    
    try:
        token_response = session.get(token_url, headers=headers, params=token_params)
        if token_response.status_code != 200:
            print("❌ 获取token失败")
            print(f"响应内容: {token_response.text}")
            return {"success": False, "message": "获取token失败"}
        
        token_data = token_response.json()
        session_token = token_data.get("session_token", "")
        if not session_token:
            print("❌ 未获取到session_token")
            return {"success": False, "message": "未获取到session_token"}
        print("✅ 获取到session_token")
    except Exception as e:
        print(f"❌ 获取token请求失败: {str(e)}")
        return {"success": False, "message": f"获取token请求失败: {str(e)}"}
    
    time.sleep(1)  # 避免请求过快
    
    # 3. 发布评论
    print("3. 发布评论...")
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
        reply_response = session.post(reply_url, headers=headers, data=reply_data)
        if reply_response.status_code == 200:
            reply_data = reply_response.json()
            # 检查响应是否包含评论ID
            if "id" in reply_data:
                print("✅ 评论发布成功！")
                print(f"评论ID: {reply_data.get('id')}")
                print(f"评论内容: {reply_data.get('text')}")
                print(f"发布时间: {reply_data.get('timeBefore')}")
                return {"success": True, "message": "评论发布成功", "comment_id": reply_data.get('id')}
            else:
                print("❌ 评论发布失败: 响应格式异常")
                return {"success": False, "message": "评论发布失败: 响应格式异常"}
        else:
            print("❌ 评论发布请求失败")
            print(f"响应内容: {reply_response.text}")
            return {"success": False, "message": f"评论发布请求失败，状态码: {reply_response.status_code}"}
    except Exception as e:
        print(f"❌ 发布评论请求失败: {str(e)}")
        return {"success": False, "message": f"发布评论请求失败: {str(e)}"}

# 6. 关注作者
def follow_user(user_id):
    """关注雪球作者"""
    print(f"开始关注作者，UID: {user_id}")
    
    # 创建会话
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": XUEQIU_COOKIE
    }
    
    # 关注作者的API
    follow_url = "https://xueqiu.com/friendships/create.json"
    follow_data = {
        "id": user_id
    }
    
    try:
        follow_response = session.post(follow_url, headers=headers, data=follow_data)
        if follow_response.status_code == 200:
            follow_result = follow_response.json()
            # 检查是否关注成功
            if follow_result.get("result") or "success" in str(follow_result).lower():
                print(f"✅ 成功关注作者，UID: {user_id}")
                return {"success": True, "message": f"成功关注作者，UID: {user_id}"}
            else:
                print(f"❌ 关注作者失败: {follow_result}")
                return {"success": False, "message": f"关注作者失败: {follow_result}"}
        else:
            print(f"❌ 关注作者请求失败，状态码: {follow_response.status_code}")
            print(f"响应内容: {follow_response.text}")
            return {"success": False, "message": f"关注作者请求失败，状态码: {follow_response.status_code}"}
    except Exception as e:
        print(f"❌ 关注作者请求失败: {str(e)}")
        return {"success": False, "message": f"关注作者请求失败: {str(e)}"}

# 7. 主循环
def main():
    global processed_articles, current_page, current_max_id
    
    print("开始自动评论任务...")
    
    # 检查Cookie有效性
    if not check_cookie_validity():
        print("\n请更新Cookie后重新运行脚本！")
        print("获取Cookie的方法：")
        print("1. 打开浏览器，登录雪球网站")
        print("2. 按F12打开开发者工具")
        print("3. 点击Network标签")
        print("4. 刷新页面，找到一个请求")
        print("5. 在Request Headers中找到Cookie字段")
        print("6. 复制完整的Cookie值到脚本中")
        return
    
    # 测试模式：只处理1篇文章，不实际发布评论
    TEST_MODE = True  # 设置为True进行测试，False进行实际运行
    test_count = 1 if TEST_MODE else DAILY_LIMIT
    
    count = 0
    empty_page_count = 0  # 记录连续空页次数
    
    while count < test_count:
        print(f"\n第{count+1}轮抓取文章...")
        print(f"已处理文章数: {len(processed_articles)}")
        print(f"当前max_id: {current_max_id}")
        
        articles = fetch_hot_articles()
        
        if not articles:
            empty_page_count += 1
            print(f"未抓取到新文章，连续空页次数: {empty_page_count}")
            
            # 如果连续多次没有新文章，重置到第一页
            if empty_page_count >= 3:
                print("连续多次无新文章，重置max_id和页码")
                current_max_id = None
                current_page = 1
                empty_page_count = 0
                time.sleep(60)
            else:
                # 继续翻页
                time.sleep(30)
            continue
        
        # 重置空页计数器
        empty_page_count = 0
        
        print(f"成功抓取到 {len(articles)} 篇新文章")
        
        for art in articles:
            if count >= test_count:
                break
            try:
                title = art.get("title", "无标题")
                text = art.get("text", "")
                article_id = art.get("id", "")
                
                if not article_id:
                    print(f"跳过无ID的文章: {title}")
                    continue
                
                print(f"\n处理文章: {title}")
                print(f"文章ID: {article_id}")
                print(f"文章内容: {text[:100]}...")
                
                # 提取作者UID
                user_id = art.get("user_id", "")
                if user_id:
                    print(f"作者UID: {user_id}")
                
                # 生成评论
                comment = generate_comment(title, text)
                print(f"生成评论: {comment}")
                
                # 测试模式下不发布评论
                if TEST_MODE:
                    print("测试模式：跳过发布评论")
                else:
                    res = post_comment(article_id, comment)
                    print(f"发布结果: {res}")
                    
                    # 只有发布成功才记录为已处理
                    if res.get("success"):
                        processed_articles.add(article_id)
                        print(f"已记录文章ID: {article_id}")
                    else:
                        # 评论失败，关注作者
                        if user_id:
                            print(f"评论发布失败，准备关注作者...")
                            follow_result = follow_user(user_id)
                            print(f"关注作者结果: {follow_result}")
                        else:
                            print("无法获取作者UID，跳过关注")
                
                count += 1
                print(f"已完成 {count}/{test_count}")
                
                # 随机延迟
                if not TEST_MODE:
                    delay = random.randint(*COMMENT_DELAY)
                    print(f"等待 {delay} 秒...")
                    time.sleep(delay)
                else:
                    # 测试模式下短延迟
                    time.sleep(2)
                    
            except Exception as e:
                print(f"处理文章失败: {str(e)}")
                time.sleep(10)

    print("\n任务完成！")
    print(f"总共处理了 {len(processed_articles)} 篇不同的文章")

if __name__ == "__main__":
    main()
