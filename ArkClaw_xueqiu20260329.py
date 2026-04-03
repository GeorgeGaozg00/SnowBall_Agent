import requests
import time
import random

# 1. 你的配置
#XUEQIU_COOKIE = "xq_a_token=XXX; xq_r_token=XXX"  # 浏览器F12复制
XUEQIU_COOKIE = "xq_a_token=d60873c46cdcf7dfa29911900810768e779318a4; xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOjU2Nzg1OTczMjYsImlzcyI6InVjIiwiZXhwIjoxNzc3NzcxODAwLCJjdG0iOjE3NzUxNzk4MDAwMjMsImNpZCI6ImQ5ZDBuNEFadXAifQ.O7yHgZo1kPBoHyiRabvJEJeJbpnqtzcszqg9BjPzRTRyvTmtGK-1q8r1W-B8i8mrktJdg8NIUeGZHpJLthgtriGsw6DP61kGTE566TkzSIU8vPESw0fgQArDOs-ospFMtykSrR9EWfkJ5CevE9sfeSEya2Z0dZjnF5TzFIBaxPBGlOjWNxfZRfG4IVDobK2jIRroyf6jUA1ehM91n87E0lNPCz4vM7ppSrJTML5PDO8V8oDb1VJHrU0dM1VBjoB0_rc44Fr5NtVpCD2Q3SXmlL2rLyA_-V9wqWFqGUUAyCa2r2324nBNdePJofb4XJCHfeMOFombC2Gs43ba-xGhOw; xq_r_token=1c75559aedff3a301c44a9d3881b136637f01197"  # 浏览器F12复制
ARK_API_KEY = "39e67fe4-bbd5-4c0f-bf63-8629f873038b"
COMMENT_DELAY = (30, 120)  # 秒
DAILY_LIMIT = 30

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

# 4. 抓取热门文章 - 支持分页和去重
def fetch_hot_articles():
    """抓取雪球热门文章，支持分页"""
    global current_max_id, current_page, processed_articles
    
    headers = {
        "Cookie": XUEQIU_COOKIE,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Accept": "application/json",
        "Referer": "https://xueqiu.com",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # 抓取热门股票的帖子
    url = "https://xueqiu.com/statuses/hot/list.json"
    params = {"count": 10, "page": current_page}
    
    # 如果有max_id，使用它来获取下一页
    if current_max_id:
        params["max_id"] = current_max_id
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10.0)
        resp.raise_for_status()
        
        # 打印响应内容以便调试
        print(f"API响应状态码: {resp.status_code}")
        print(f"当前页码: {current_page}")
        print(f"当前max_id: {current_max_id}")
        
        data = resp.json()
        
        # 检查响应结构
        if "items" in data:
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
            articles = []
            for item in items:
                if "original_status" in item:
                    article = item["original_status"]
                    article_id = article.get("id")
                    
                    # 跳过已处理的文章
                    if article_id in processed_articles:
                        print(f"跳过已处理的文章ID: {article_id}")
                        continue
                    
                    articles.append({
                        "id": article_id,
                        "title": article.get("title"),
                        "text": article.get("description", "")
                    })
            
            print(f"转换后获取到 {len(articles)} 篇新文章")
            return articles
        elif "list" in data:
            articles = data.get("list", [])
            print(f"获取到 {len(articles)} 篇文章")
            return articles
        else:
            print(f"未知的响应结构: {list(data.keys())}")
            return []
    except Exception as e:
        print(f"抓取文章失败: {str(e)}")
        return []

# 5. 自动发布评论 - 基于API
def post_comment(article_id, content):
    """使用雪球API发布评论"""
    print("开始使用API发布评论...")
    
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
        text_check_response = requests.post(text_check_url, headers=headers, data=text_check_data)
        if text_check_response.status_code != 200:
            print("❌ 文本审核失败")
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
        token_response = requests.get(token_url, headers=headers, params=token_params)
        if token_response.status_code != 200:
            print("❌ 获取token失败")
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
        reply_response = requests.post(reply_url, headers=headers, data=reply_data)
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
            return {"success": False, "message": f"评论发布请求失败，状态码: {reply_response.status_code}"}
    except Exception as e:
        print(f"❌ 发布评论请求失败: {str(e)}")
        return {"success": False, "message": f"发布评论请求失败: {str(e)}"}

# 6. 主循环
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
    TEST_MODE = False  # 设置为True进行测试，False进行实际运行
    test_count = 1 if TEST_MODE else DAILY_LIMIT
    
    count = 0
    empty_page_count = 0  # 记录连续空页次数
    
    while count < test_count:
        print(f"\n第{count+1}轮抓取文章...")
        print(f"已处理文章数: {len(processed_articles)}")
        print(f"当前页码: {current_page}")
        
        articles = fetch_hot_articles()
        
        if not articles:
            empty_page_count += 1
            print(f"未抓取到新文章，连续空页次数: {empty_page_count}")
            
            # 如果连续多次没有新文章，重置到第一页
            if empty_page_count >= 3:
                print("连续多次无新文章，重置到第一页")
                current_page = 1
                current_max_id = None
                empty_page_count = 0
                time.sleep(60)
            else:
                # 继续翻页
                current_page += 1
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
