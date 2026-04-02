import requests
import time
import json

# 配置
XUEQIU_COOKIE = "xq_a_token=646296e3dc9581be9ca594e0177e818eef6e6977; xq_r_token=d0bcc78d11b5fdc4f3c6b2e6dd180ed793502600"
TARGET_USER_ID = "1643044849"  # 目标作者UID

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

def get_session_token():
    """获取会话token"""
    print("获取会话token...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": XUEQIU_COOKIE
    }
    
    token_url = "https://xueqiu.com/provider/session/token.json"
    token_params = {
        "api_path": "/friendships/create.json",
        "_": int(time.time() * 1000)
    }
    
    try:
        token_response = requests.get(token_url, headers=headers, params=token_params)
        if token_response.status_code != 200:
            print(f"❌ 获取token失败，状态码: {token_response.status_code}")
            return None
        
        token_data = token_response.json()
        session_token = token_data.get("session_token", "")
        if not session_token:
            print("❌ 未获取到session_token")
            return None
        print("✅ 获取到session_token")
        return session_token
    except Exception as e:
        print(f"❌ 获取token请求失败: {str(e)}")
        return None

def follow_user(user_id, session_token=None):
    """关注雪球作者"""
    print(f"开始关注作者，UID: {user_id}")
    
    # 尝试不同的请求头配置
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": f"https://xueqiu.com/{user_id}",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": XUEQIU_COOKIE,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive"
    }
    
    # 尝试不同的关注API端点
    follow_urls = [
        "https://xueqiu.com/friendships/create.json",
        "https://xueqiu.com/user/follow.json"
    ]
    
    # 尝试不同的请求数据
    follow_datas = [
        {"uid": user_id, "type": "1"},
        {"id": user_id},
        {"user_id": user_id}
    ]
    
    for url in follow_urls:
        for data in follow_datas:
            print(f"尝试API: {url}")
            print(f"尝试数据: {data}")
            
            try:
                follow_response = requests.post(url, headers=headers, data=data)
                print(f"关注请求状态码: {follow_response.status_code}")
                print(f"关注请求响应: {follow_response.text}")
                
                if follow_response.status_code == 200:
                    try:
                        follow_result = follow_response.json()
                        # 检查是否关注成功
                        if follow_result.get("result") or "success" in str(follow_result).lower() or follow_result.get("code") == 200:
                            print(f"✅ 成功关注作者，UID: {user_id}")
                            return True
                        else:
                            print(f"❌ 关注作者失败: {follow_result}")
                    except:
                        print("❌ 响应格式异常")
                else:
                    print(f"❌ 关注作者请求失败，状态码: {follow_response.status_code}")
            except Exception as e:
                print(f"❌ 关注作者请求失败: {str(e)}")
            
            # 等待一秒再尝试下一个
            time.sleep(1)
    
    return False

def main():
    print("开始测试关注指定作者功能...")
    print(f"目标作者UID: {TARGET_USER_ID}")
    
    # 检查Cookie有效性
    if not check_cookie_validity():
        print("请更新Cookie后重新运行！")
        return
    
    # 获取会话token
    session_token = get_session_token()
    
    # 执行关注操作
    success = follow_user(TARGET_USER_ID, session_token)
    
    if success:
        print("测试成功！已成功关注作者")
    else:
        print("测试失败！关注作者失败")

if __name__ == "__main__":
    main()
