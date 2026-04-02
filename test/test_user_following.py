import requests
import json
import time
import random
from playwright.sync_api import sync_playwright

# 1. 你的配置
# 注意：Cookie可能会过期，需要定期更新
XUEQIU_COOKIE = "xq_a_token=646296e3dc9581be9ca594e0177e818eef6e6977; xq_r_token=d0bcc78d11b5fdc4f3c6b2e6dd180ed793502600"

# 2. 测试配置
TEST_USER_ID = "5355205180"  # 用于测试的用户ID

# 请求头
headers = {
    "Cookie": XUEQIU_COOKIE,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Accept": "application/json",
    "Referer": "https://xueqiu.com",
    "X-Requested-With": "XMLHttpRequest"
}

def get_current_user_info():
    """获取当前登录用户信息"""
    print("获取当前登录用户信息...")
    
    # 方法0：使用新的API获取当前用户信息
    try:
        url = "https://xueqiu.com/statuses/original.json"
        params = {
            "user_id": -1,
            "count": 1
        }
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"原创状态API响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'user' in data:
                user = data['user']
                print(f"✅ 成功从原创状态API获取用户信息")
                print(f"用户ID: {user.get('id')}")
                print(f"用户名: {user.get('screen_name')}")
                return user
    except Exception as e:
        print(f"❌ 从原创状态API获取用户信息失败: {str(e)}")
    
    # 方法1：使用会话token API（这个在评论程序中成功使用过）
    try:
        # 访问雪球会话token API
        url = "https://xueqiu.com/provider/session/token.json"
        params = {
            "api_path": "/statuses/reply.json",
            "_": int(time.time() * 1000)
        }
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"会话token API响应状态码: {response.status_code}")
        print(f"会话token API响应内容: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功从会话token API获取用户信息")
            print(f"会话token: {data.get('session_token')}")
            # 如果响应中包含用户信息
            if 'user_id' in data:
                print(f"用户ID: {data.get('user_id')}")
                return data
    except Exception as e:
        print(f"❌ 从会话token API获取用户信息失败: {str(e)}")
    
    # 方法2：使用消息通知API
    try:
        # 访问雪球消息通知API
        url = "https://xueqiu.com/notifications/unread.json"
        response = requests.get(url, headers=headers, timeout=10)
        print(f"通知API响应状态码: {response.status_code}")
        print(f"通知API响应内容: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功从通知API获取用户信息")
            print(f"用户ID: {data.get('user_id')}")
            print(f"用户名: {data.get('screen_name')}")
            return data
    except Exception as e:
        print(f"❌ 从通知API获取用户信息失败: {str(e)}")
    
    # 方法3：使用用户信息API
    try:
        # 访问雪球用户信息API
        url = "https://xueqiu.com/user.json"
        response = requests.get(url, headers=headers, timeout=10)
        print(f"用户API响应状态码: {response.status_code}")
        print(f"用户API响应内容: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功从用户API获取用户信息")
            print(f"用户ID: {data.get('id')}")
            print(f"用户名: {data.get('screen_name')}")
            print(f"简介: {data.get('description')}")
            return data
    except Exception as e:
        print(f"❌ 从用户API获取用户信息失败: {str(e)}")
    
    # 方法4：访问用户设置页面API
    try:
        # 访问用户设置页面API
        url = "https://xueqiu.com/settings/account.json"
        response = requests.get(url, headers=headers, timeout=10)
        print(f"设置API响应状态码: {response.status_code}")
        print(f"设置API响应内容: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功从设置页面获取用户信息")
            print(f"用户ID: {data.get('id')}")
            print(f"用户名: {data.get('screen_name')}")
            print(f"邮箱: {data.get('email')}")
            return data
    except Exception as e:
        print(f"❌ 从设置页面获取用户信息失败: {str(e)}")
    
    # 方法5：访问雪球首页，从页面中提取用户信息
    try:
        response = requests.get("https://xueqiu.com", headers=headers, timeout=10)
        if response.status_code == 200:
            # 保存HTML内容以便分析
            with open("xueqiu_homepage.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            
            # 尝试从HTML中提取用户信息
            # 查找包含用户信息的JavaScript变量
            import re
            
            # 查找 SNB.currentUser 或类似的用户信息
            patterns = [
                r'SNB\.currentUser\s*=\s*({[^}]+})',
                r'currentUser\s*=\s*({[^}]+})',
                r'user_id["\']?\s*:\s*["\']?(\d+)["\']?',
                r'uid["\']?\s*:\s*["\']?(\d+)["\']?'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    print(f"✅ 找到匹配模式: {pattern}")
                    if '{' in match.group(1):
                        user_info_str = match.group(1)
                        user_info = json.loads(user_info_str)
                        print(f"✅ 成功从首页获取用户信息")
                        print(f"用户ID: {user_info.get('id')}")
                        print(f"用户名: {user_info.get('screen_name')}")
                        print(f"头像: {user_info.get('profile_image_url')}")
                        return user_info
                    else:
                        print(f"✅ 找到用户ID: {match.group(1)}")
                        return {"id": match.group(1)}
    except Exception as e:
        print(f"❌ 从首页获取用户信息失败: {str(e)}")
    
    # 方法6：访问个人中心页面
    try:
        url = "https://xueqiu.com/center"
        response = requests.get(url, headers=headers, timeout=10)
        print(f"个人中心响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 保存HTML内容以便分析
            with open("xueqiu_center.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            
            # 尝试从URL中提取用户ID
            import re
            # 查找 /u/数字 的模式
            match = re.search(r'/u/(\d+)', response.text)
            if match:
                user_id = match.group(1)
                print(f"✅ 从个人中心页面提取到用户ID: {user_id}")
                return {"id": user_id}
    except Exception as e:
        print(f"❌ 从个人中心获取用户信息失败: {str(e)}")
    
    return None

def get_following_list(user_id, page=1, count=20):
    """获取用户关注的人列表"""
    print(f"\n获取用户关注的人列表（用户ID: {user_id}，第 {page} 页）...")
    
    # 使用雪球关注列表API
    url = "https://xueqiu.com/friendships/friends.json"
    # 尝试使用不同的分页参数
    params = {
        "uid": user_id,
        "page": page,
        "count": count
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"请求URL: {response.url}")
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # 保存响应数据
            with open(f"following_list_page_{page}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 提取关注列表
            users = data.get("friends", [])
            print(f"✅ 成功获取 {len(users)} 个关注的人")
            print(f"响应中的page: {data.get('page')}")
            print(f"响应中的maxPage: {data.get('maxPage')}")
            print(f"响应中的count: {data.get('count')}")
            print(f"响应中的totalCount: {data.get('totalCount')}")
            
            # 打印关注的人的信息（只打印前5个，避免输出过多）
            for i, user in enumerate(users[:5]):
                print(f"  - 用户ID: {user.get('id')}, 用户名: {user.get('screen_name')}")
            if len(users) > 5:
                print(f"  ... 还有 {len(users) - 5} 个关注的人")
            
            return users
        else:
            print(f"❌ 获取关注列表失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            return []
    except Exception as e:
        print(f"❌ 获取关注列表失败: {str(e)}")
        return []

def get_all_following(user_id):
    """获取所有关注的人（使用Playwright模拟浏览器）"""
    print(f"\n开始获取所有关注的人（用户ID: {user_id}）...")
    
    all_following = []
    
    # 首先尝试使用API获取
    api_result = get_following_via_api(user_id)
    if api_result:
        all_following = api_result
    
    # 如果API获取的数据不足，尝试使用Playwright
    if len(all_following) < 50:
        print("\n尝试使用Playwright模拟浏览器获取关注列表...")
        playwright_result = get_following_via_playwright(user_id)
        if playwright_result and len(playwright_result) > len(all_following):
            all_following = playwright_result
    
    # 保存最终结果
    with open("all_following.json", "w", encoding="utf-8") as f:
        json.dump(all_following, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 最终获取到 {len(all_following)} 个关注的人")
    return all_following

def get_following_via_api(user_id):
    """通过API获取关注列表"""
    print("\n通过API获取关注列表...")
    
    all_following = []
    
    # 记录已获取的用户ID，避免重复
    seen_user_ids = set()
    
    # 使用主要API端点
    url = "https://xueqiu.com/friendships/friends.json"
    
    # 使用更完整的请求头，模拟真实浏览器
    full_headers = {
        "Cookie": XUEQIU_COOKIE,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"https://xueqiu.com/u/{user_id}",
        "X-Requested-With": "XMLHttpRequest",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    
    try:
        # 尝试不同的size值，看看能获取多少用户
        size_values = [50, 60, 70, 80, 90, 100, 150, 200]
        
        for size in size_values:
            params = {
                "uid": user_id,
                "page": 1,
                "size": size
            }
            
            print(f"\n尝试 size={size}...")
            print(f"请求URL: {url}")
            print(f"参数: {params}")
            
            response = requests.get(url, headers=full_headers, params=params, timeout=10)
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # 提取关注列表
                users = data.get("friends", [])
                total_count = data.get('count', len(users))
                max_page = data.get('maxPage', 1)
                
                print(f"✅ 成功获取 {len(users)} 个关注的人")
                print(f"响应中的总关注数: {total_count}")
                print(f"响应中的maxPage: {max_page}")
                
                # 打印前3个用户ID
                for i, user in enumerate(users[:3]):
                    user_id_val = user.get('id')
                    print(f"  - 用户ID: {user_id_val}")
                
                # 如果获取的用户数量等于总关注数，说明成功了
                if len(users) >= total_count:
                    print(f"\n🎉 成功！使用 size={size} 获取了所有 {len(users)} 个关注的人！")
                    
                    # 保存响应数据
                    with open(f"following_list_api_size{size}.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    # 添加用户到列表
                    for user in users:
                        user_id_val = user.get('id')
                        if user_id_val:
                            user_id_str = str(user_id_val)
                            if user_id_str not in seen_user_ids:
                                seen_user_ids.add(user_id_str)
                                all_following.append(user)
                    
                    break
                else:
                    # 保存响应数据以供分析
                    with open(f"following_list_api_size{size}.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                print(f"❌ API请求失败: {response.status_code}")
            
            # 模拟人类操作延迟
            import time
            time.sleep(2)
        
        # 如果所有size值都试过了，还是没有获取完整数据，使用最大的size值
        if not all_following:
            print(f"\n使用最大的size值重新获取...")
            params = {
                "uid": user_id,
                "page": 1,
                "size": 200
            }
            
            print(f"请求URL: {url}")
            print(f"参数: {params}")
            
            response = requests.get(url, headers=full_headers, params=params, timeout=10)
            print(f"响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # 提取关注列表
                users = data.get("friends", [])
                total_count = data.get('count', len(users))
                
                print(f"✅ 成功获取 {len(users)} 个关注的人")
                print(f"响应中的总关注数: {total_count}")
                
                # 添加用户到列表
                for user in users:
                    user_id_val = user.get('id')
                    if user_id_val:
                        user_id_str = str(user_id_val)
                        if user_id_str not in seen_user_ids:
                            seen_user_ids.add(user_id_str)
                            all_following.append(user)
        
        print(f"\n✅ API总共获取到 {len(all_following)} 个关注的人")
    except Exception as e:
        print(f"❌ API获取关注列表失败: {str(e)}")
    
    return all_following

def get_following_via_playwright(user_id):
    """通过Playwright模拟浏览器获取关注列表（用户手动登录和验证）"""
    print("\n通过Playwright模拟浏览器获取关注列表...")
    
    all_following = []
    
    try:
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=False)  # 使用非无头模式，让用户可以手动操作
            page = browser.new_page()
            
            # 访问雪球首页
            page.goto("https://xueqiu.com")
            
            # 提示用户手动登录和完成验证
            print("\n=========================================")
            print("请在打开的浏览器中完成以下操作：")
            print("1. 在浏览器中输入您的雪球账号和密码")
            print("2. 完成登录验证（如果有滑动验证，请手动完成）")
            print("3. 确保您已经成功登录到雪球首页")
            print("4. 登录完成后，请回到终端按回车键继续...")
            print("=========================================")
            
            # 等待用户按回车键
            input()
            
            # 提示用户进入个人页面并点击关注链接
            print("\n=========================================")
            print("请在浏览器中完成以下操作：")
            print("1. 点击页面顶部的用户头像，进入个人页面")
            print("2. 在个人页面中，找到'关注'链接并点击")
            print("3. 进入关注列表页面后，确保看到分页按钮（1、2、3等）")
            print("4. 完成后，请回到终端按回车键继续...")
            print("=========================================")
            
            # 等待用户按回车键
            input()
            
            # 保存页面内容以便分析
            with open("page_content.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("已保存页面内容到 page_content.html，用于分析页面结构")
            
            # 打印当前页面URL
            print(f"当前页面URL: {page.url}")
            
            # 记录已获取的用户ID，避免重复
            seen_user_ids = set()
            
            # 手动处理分页
            current_page = 1
            while True:
                print(f"\n正在处理第 {current_page} 页...")
                
                # 尝试获取所有链接，看看是否能找到用户链接
                links = page.query_selector_all("a")
                print(f"尝试获取所有链接，找到 {len(links)} 个链接")
                
                # 过滤出关注的人链接
                following_links = []
                for link in links:
                    href = link.get_attribute("href")
                    if href:
                        # 检查是否是用户链接，可能是 /u/{id} 或直接 /{id}
                        parts = href.split('/')
                        # 过滤掉空字符串
                        parts = [p for p in parts if p]
                        if len(parts) >= 1:
                            # 检查最后一部分是否是数字
                            if parts[-1].isdigit():
                                # 检查是否是用户页面链接
                                # 排除其他类型的数字链接，如帖子、状态等
                                if not any(keyword in href for keyword in ["/status/", "/post/", "/center/"]):
                                    following_links.append(link)
                print(f"找到 {len(following_links)} 个用户链接")
                
                # 提取用户信息
                for link in following_links:
                    try:
                        href = link.get_attribute("href")
                        if href:
                            # 从URL中提取用户ID
                            parts = href.split('/')
                            # 过滤掉空字符串
                            parts = [p for p in parts if p]
                            user_id_str = ""
                            # 查找最后一个数字部分作为用户ID
                            for part in reversed(parts):
                                if part.isdigit():
                                    user_id_str = part
                                    break
                            
                            if user_id_str and user_id_str.isdigit():
                                # 尝试获取用户名
                                screen_name = link.text_content().strip()
                                if not screen_name:
                                    screen_name = f"用户{user_id_str}"
                                
                                # 过滤重复用户
                                if user_id_str not in seen_user_ids:
                                    seen_user_ids.add(user_id_str)
                                    
                                    # 创建用户对象
                                    user = {
                                        "id": user_id_str,
                                        "screen_name": screen_name
                                    }
                                    
                                    all_following.append(user)
                                    
                                    # 打印获取的用户信息（只打印前10个）
                                    if len(all_following) <= 10:
                                        print(f"  - 用户ID: {user_id_str}, 用户名: {screen_name}")
                    except Exception as e:
                        print(f"❌ 提取用户信息失败: {str(e)}")
                
                # 提示用户手动点击下一页
                print("\n=========================================")
                print(f"已处理完第 {current_page} 页，共获取 {len(all_following)} 个关注的人")
                print(f"当前页面URL: {page.url}")
                print("请在浏览器中检查是否还有下一页")
                print("1. 找到页面底部的分页按钮")
                print("2. 如果有下一页按钮，请点击它并等待页面加载完成")
                print("3. 如果没有下一页按钮，直接按回车键结束")
                print("=========================================")
                print("请输入指令:")
                print("- 按回车键: 没有下一页，结束处理")
                print("- 输入 'next' 并按回车键: 已点击下一页，继续处理")
                print("=========================================")
                
                # 等待用户输入
                user_input = input().strip().lower()
                
                # 如果用户按回车键或输入其他内容，结束循环
                if user_input != 'next':
                    print("✅ 已处理完所有分页")
                    break
                
                # 增加当前页码
                current_page += 1
                
                # 模拟人类操作延迟
                import time
                time.sleep(1)
            
            # 保存结果
            with open("following_list_playwright.json", "w", encoding="utf-8") as f:
                json.dump(all_following, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Playwright获取到 {len(all_following)} 个关注的人")
            
            # 关闭浏览器
            browser.close()
    except Exception as e:
        print(f"❌ Playwright获取关注列表失败: {str(e)}")
    
    return all_following

def monitor_network_requests(user_id):
    """监听浏览器的网络请求，找出真实的API分页参数"""
    print("\n监听浏览器网络请求，破解API分页参数...")
    
    captured_requests = []
    
    try:
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # 监听网络请求
            def handle_request(request):
                # 记录所有的XHR和fetch请求
                if request.resource_type in ['xhr', 'fetch']:
                    print(f"\n捕获到网络请求:")
                    print(f"  URL: {request.url}")
                    print(f"  方法: {request.method}")
                    print(f"  类型: {request.resource_type}")
                    
                    # 保存请求信息
                    request_info = {
                        'url': request.url,
                        'method': request.method,
                        'resource_type': request.resource_type,
                        'headers': dict(request.headers),
                        'post_data': request.post_data
                    }
                    captured_requests.append(request_info)
                    
                    # 保存到文件
                    with open('captured_all_requests.json', 'w', encoding='utf-8') as f:
                        json.dump(captured_requests, f, ensure_ascii=False, indent=2)
            
            # 注册请求监听器
            page.on('request', handle_request)
            
            # 访问雪球首页
            page.goto("https://xueqiu.com")
            
            # 提示用户手动登录和完成验证
            print("\n=========================================")
            print("请在打开的浏览器中完成以下操作：")
            print("1. 在浏览器中输入您的雪球账号和密码")
            print("2. 完成登录验证（如果有滑动验证，请手动完成）")
            print("3. 确保您已经成功登录到雪球首页")
            print("4. 登录完成后，请回到终端按回车键继续...")
            print("=========================================")
            
            # 等待用户按回车键
            input()
            
            # 提示用户进入个人页面并点击关注链接
            print("\n=========================================")
            print("请在浏览器中完成以下操作：")
            print("1. 点击页面顶部的用户头像，进入个人页面")
            print("2. 在个人页面中，找到'关注'链接并点击")
            print("3. 进入关注列表页面后，确保看到分页按钮（1、2、3等）")
            print("4. 完成后，请回到终端按回车键继续...")
            print("=========================================")
            
            # 等待用户按回车键
            input()
            
            # 提示用户点击分页按钮
            print("\n=========================================")
            print("现在请点击第2页按钮")
            print("程序会自动捕获API请求")
            print("点击完成后，请回到终端按回车键继续...")
            print("=========================================")
            
            # 等待用户按回车键
            input()
            
            # 分析捕获的请求
            if captured_requests:
                print(f"\n✅ 成功捕获到 {len(captured_requests)} 个API请求")
                
                for i, req in enumerate(captured_requests):
                    print(f"\n请求 {i+1}:")
                    print(f"  URL: {req['url']}")
                    print(f"  方法: {req['method']}")
                    print(f"  关键请求头:")
                    for key in ['cookie', 'user-agent', 'referer', 'x-requested-with']:
                        if key in req['headers']:
                            print(f"    {key}: {req['headers'][key][:100]}...")
            else:
                print("\n⚠️  没有捕获到API请求")
            
            # 关闭浏览器
            browser.close()
    except Exception as e:
        print(f"❌ 监听网络请求失败: {str(e)}")
    
    return captured_requests

def main():
    print("=" * 60)
    print("雪球用户信息获取测试程序")
    print("=" * 60)
    
    # 选择模式
    print("\n请选择运行模式:")
    print("1. 获取关注列表（API方式）")
    print("2. 监听浏览器网络请求（破解API分页参数）")
    print("3. 获取关注列表（Playwright手动模式）")
    
    choice = input("\n请输入选项（1/2/3）: ").strip()
    
    if choice == '2':
        # 监听网络请求模式
        print("\n开始监听浏览器网络请求...")
        captured_requests = monitor_network_requests("5355205180")
        
        if captured_requests:
            print("\n✅ 已保存捕获的API请求到 captured_api_requests.json")
            print("请查看该文件，分析真实的分页参数")
        return
    elif choice == '3':
        # Playwright手动模式
        print("\n使用Playwright手动模式获取关注列表...")
        all_following = get_following_via_playwright("5355205180")
        
        if all_following:
            print(f"\n总共关注的人数: {len(all_following)}")
            
            # 保存完整的关注列表
            with open("all_following.json", "w", encoding="utf-8") as f:
                json.dump(all_following, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 已保存完整的关注列表到 all_following.json")
            
            # 提取所有UID
            uid_list = [user.get('id') for user in all_following if user.get('id')]
            print(f"\n关注的人的UID列表（共 {len(uid_list)} 个）:")
            for uid in uid_list[:10]:
                print(f"  - {uid}")
            if len(uid_list) > 10:
                print(f"  ... 还有 {len(uid_list) - 10} 个")
            
            # 保存UID列表
            with open("following_uids.txt", "w", encoding="utf-8") as f:
                for uid in uid_list:
                    f.write(f"{uid}\n")
            
            print(f"✅ 已保存UID列表到 following_uids.txt")
        return
    
    # 默认模式：API方式
    # 1. 获取当前登录用户信息
    user_info = get_current_user_info()
    
    if not user_info:
        print("\n❌ 无法获取用户信息，请检查Cookie是否有效")
        print("\n尝试使用默认用户ID进行测试...")
        # 使用一个已知的用户ID进行测试
        user_id = "5355205180"  # 这是一个示例用户ID
        print(f"使用默认用户ID: {user_id}")
    else:
        user_id = user_info.get('id')
        
        if not user_id:
            print("\n❌ 无法获取用户ID")
            print("\n尝试使用默认用户ID进行测试...")
            # 使用一个已知的用户ID进行测试
            user_id = "5355205180"  # 这是一个示例用户ID
            print(f"使用默认用户ID: {user_id}")
    
    # 2. 获取关注列表（第一页）
    print("\n" + "=" * 60)
    following_list = get_following_list(user_id, page=1, count=20)
    
    if following_list:
        print(f"\n第一页关注的人数量: {len(following_list)}")
        
        # 3. 获取所有关注的人
        print("\n" + "=" * 60)
        all_following = get_all_following(user_id)
        
        print(f"\n总共关注的人数: {len(all_following)}")
        
        # 保存完整的关注列表
        with open("all_following.json", "w", encoding="utf-8") as f:
            json.dump(all_following, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存完整的关注列表到 all_following.json")
        
        # 提取所有UID
        uid_list = [user.get('id') for user in all_following if user.get('id')]
        print(f"\n关注的人的UID列表（共 {len(uid_list)} 个）:")
        for uid in uid_list:
            print(f"  - {uid}")
        
        # 保存UID列表
        with open("following_uids.txt", "w", encoding="utf-8") as f:
            for uid in uid_list:
                f.write(f"{uid}\n")
        
        print(f"✅ 已保存UID列表到 following_uids.txt")
    else:
        print("\n❌ 无法获取关注列表")

if __name__ == "__main__":
    main()
