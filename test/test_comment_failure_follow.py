import requests
import time
import json

# 配置
XUEQIU_COOKIE = "xq_a_token=646296e3dc9581be9ca594e0177e818eef6e6977; xq_r_token=d0bcc78d11b5fdc4f3c6b2e6dd180ed793502600"
ARK_API_KEY = "39e67fe4-bbd5-4c0f-bf63-8629f873038b"

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
    
    # 3. 发布评论 - 使用无效的文章ID来模拟失败
    print("3. 发布评论...")
    reply_url = "https://xueqiu.com/statuses/reply.json"
    reply_data = {
        "comment": f"<p>{content}</p>",
        "forward": "1",
        "id": "9999999999",  # 无效的文章ID，确保评论失败
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

def follow_user(user_id):
    """关注雪球作者"""
    print(f"开始关注作者，UID: {user_id}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": f"https://xueqiu.com/{user_id}",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": XUEQIU_COOKIE
    }
    
    # 关注作者的API - 使用正确的参数格式
    follow_url = "https://xueqiu.com/friendships/create.json"
    follow_data = {
        "id": user_id
    }
    
    try:
        follow_response = requests.post(follow_url, headers=headers, data=follow_data)
        print(f"关注请求状态码: {follow_response.status_code}")
        print(f"关注请求响应: {follow_response.text}")
        
        if follow_response.status_code == 200:
            follow_result = follow_response.json()
            # 检查是否关注成功
            if follow_result.get("success") or "success" in str(follow_result).lower():
                print(f"✅ 成功关注作者，UID: {user_id}")
                return {"success": True, "message": f"成功关注作者，UID: {user_id}"}
            else:
                print(f"❌ 关注作者失败: {follow_result}")
                return {"success": False, "message": f"关注作者失败: {follow_result}"}
        else:
            print(f"❌ 关注作者请求失败，状态码: {follow_response.status_code}")
            return {"success": False, "message": f"关注作者请求失败，状态码: {follow_response.status_code}"}
    except Exception as e:
        print(f"❌ 关注作者请求失败: {str(e)}")
        return {"success": False, "message": f"关注作者请求失败: {str(e)}"}

def main():
    print("开始测试评论失败后关注作者功能...")
    
    # 测试文章信息
    title = "测试文章"
    text = "这是一篇测试文章"
    user_id = "1643044849"  # 目标作者UID
    
    # 生成评论
    comment = generate_comment(title, text)
    print(f"生成评论: {comment}")
    
    # 发布评论（故意使用无效ID导致失败）
    res = post_comment("9999999999", comment)
    print(f"发布结果: {res}")
    
    # 评论失败，尝试关注作者
    if not res.get("success"):
        print("评论发布失败，准备关注作者...")
        follow_result = follow_user(user_id)
        print(f"关注作者结果: {follow_result}")
    
    print("测试完成！")

if __name__ == "__main__":
    main()
