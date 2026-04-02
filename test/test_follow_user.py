import requests
import time

# 配置
XUEQIU_COOKIE = "xq_a_token=646296e3dc9581be9ca594e0177e818eef6e6977; xq_r_token=d0bcc78d11b5fdc4f3c6b2e6dd180ed793502600"
TARGET_USER_ID = "1643044849"  # 目标作者UID

def follow_user(user_id):
    """关注雪球作者"""
    print(f"开始关注作者，UID: {user_id}")
    
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
        "uid": user_id,
        "type": "1"
    }
    
    try:
        follow_response = requests.post(follow_url, headers=headers, data=follow_data)
        print(f"关注请求状态码: {follow_response.status_code}")
        print(f"关注请求响应: {follow_response.text}")
        
        if follow_response.status_code == 200:
            follow_result = follow_response.json()
            # 检查是否关注成功
            if follow_result.get("result") or "success" in str(follow_result).lower():
                print(f"✅ 成功关注作者，UID: {user_id}")
                return True
            else:
                print(f"❌ 关注作者失败: {follow_result}")
                return False
        else:
            print(f"❌ 关注作者请求失败，状态码: {follow_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 关注作者请求失败: {str(e)}")
        return False

def main():
    print("开始测试关注作者功能...")
    print(f"目标作者UID: {TARGET_USER_ID}")
    
    # 执行关注操作
    success = follow_user(TARGET_USER_ID)
    
    if success:
        print("测试成功！已成功关注作者")
    else:
        print("测试失败！关注作者失败")

if __name__ == "__main__":
    main()
