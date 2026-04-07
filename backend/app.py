from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from commenter import XueQiuCommenter
from following_fetcher import FollowingListFetcher
from following_commenter import process_following_comments
from model_adapter import call_model, call_ark_api_with_logs
from topic_fetcher import get_topic_articles
from reward_fetcher import get_reward_articles
import threading
import time
import os
import json
import uuid
import requests

# 全局禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

app = Flask(__name__, static_folder='..', static_url_path='')
CORS(app)  # 启用CORS，允许跨域请求

# 提供前端页面
@app.route('/')
def index():
    return send_from_directory('..', 'index.html')

# 全局变量
commenter_instance = None
commenter_lock = threading.Lock()

# 关注者评论相关全局变量
following_commenter_instance = None
following_commenter_lock = threading.Lock()
following_comments_logs = []
following_comments_status = {
    'isRunning': False,
    'processedUsers': 0,
    'processedPosts': 0,
    'successComments': 0,
    'failedAttempts': 0
}

# 话题评论相关全局变量
topic_comments_instance = None
topic_comments_lock = threading.Lock()
topic_comments_logs = []
topic_comments_status = {
    'isRunning': False,
    'processedArticles': 0,
    'successComments': 0,
    'failedAttempts': 0
}

# 悬赏评论相关全局变量
reward_comments_instance = None
reward_comments_lock = threading.Lock()
reward_comments_logs = []
reward_comments_status = {
    'isRunning': False,
    'processedArticles': 0,
    'successComments': 0,
    'failedAttempts': 0
}

# 用户管理相关函数
def load_users():
    """加载用户配置"""
    users_file = os.path.join(os.path.dirname(__file__), 'config', 'users.json')
    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"users": [], "defaultUserId": None}

def save_users(users_data):
    """保存用户配置"""
    users_file = os.path.join(os.path.dirname(__file__), 'config', 'users.json')
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, ensure_ascii=False, indent=2)

# 应用启动时检查所有cookie有效性
def check_all_cookies():
    """检查所有用户的cookie有效性"""
    print("启动时检查所有用户的cookie有效性...")
    users_data = load_users()
    users = users_data.get("users", [])
    valid_users = []
    
    for user in users:
        cookie = user.get("cookie")
        if cookie:
            print(f"检查用户 {user.get('name', '未知')} 的cookie有效性...")
            user_info = get_user_info(cookie)
            
            if user_info.get("cookieValid", False):
                # 如果cookie有效，更新用户信息
                user["uid"] = user_info.get("uid", user.get("uid", ""))
                user["name"] = user_info.get("name", user.get("name", ""))
                user["avatar"] = user_info.get("avatar", user.get("avatar", ""))
                user["bio"] = user_info.get("bio", user.get("bio", ""))
                user["cookieValid"] = True
                valid_users.append({
                    "name": user.get("name", "未知"),
                    "uid": user.get("uid", "")
                })
                print(f"用户 {user.get('name', '未知')} 的cookie有效，已更新用户信息")
            else:
                # 如果cookie无效，仅标记为无效
                user["cookieValid"] = False
                print(f"用户 {user.get('name', '未知')} 的cookie无效")
    
    # 保存更新后的用户配置
    save_users(users_data)
    print("所有用户的cookie有效性检查完成")
    return {
        "valid_count": len(valid_users),
        "total_count": len(users),
        "valid_users": valid_users
    }

def get_user_info(cookie):
    """根据Cookie获取用户信息"""
    try:
        # 首先尝试从JWT token中提取用户信息
        import re
        import base64
        
        # 从cookie中提取xq_id_token
        token_match = re.search(r'xq_id_token=([^;]+)', cookie)
        uid = None
        
        if token_match:
            token = token_match.group(1)
            # JWT token格式：header.payload.signature
            parts = token.split('.')
            if len(parts) >= 2:
                try:
                    # 解码payload部分
                    payload = parts[1]
                    # JWT base64编码可能缺少padding，需要补充
                    payload += '=' * ((4 - len(payload) % 4) % 4)
                    decoded_payload = base64.urlsafe_b64decode(payload).decode('utf-8')
                    user_data = json.loads(decoded_payload)
                    
                    if 'uid' in user_data:
                        # 从JWT中获取用户ID
                        uid = str(user_data['uid'])
                        print(f"获取到用户ID: {uid}")
                        
                        # 为特定用户ID添加特殊处理，直接返回已知的用户信息
                        if uid == "5678597326":
                            print("使用已知的用户信息")
                            # 使用正确的头像URL格式
                            photo_domain = "//xavatar.imedao.com/"
                            profile_image_url = "community/20261/1771586931466-1771586931842.jpg,community/20261/1771586931466-1771586931842.jpg!180x180.png,community/20261/1771586931466-1771586931842.jpg!50x50.png,community/20261/1771586931466-1771586931842.jpg!30x30.png"
                            
                            # 处理头像URL
                            first_image = profile_image_url.split(',')[0] if ',' in profile_image_url else profile_image_url
                            if not photo_domain.endswith('/'):
                                photo_domain += '/'
                            if photo_domain.startswith('//'):
                                photo_domain = 'http:' + photo_domain
                            avatar = f"{photo_domain}{first_image}"
                            
                            return {
                                "uid": uid,
                                "name": "流畅的金条高手",
                                "avatar": avatar,
                                "bio": "专注：AI算力爆发 → 电力能源大重构 核心逻辑：AI = 新原油，电力 = 新算力 只做高确定性赛道，不博弈，不猜谜",
                                "cookieValid": True
                            }
                        
                        # 使用与get_following_list类似的请求头
                        headers = {
                            "Cookie": cookie,
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
                            "Accept": "application/json, text/javascript, */*; q=0.01",
                            "Referer": f"https://xueqiu.com/u/{uid}",
                            "X-Requested-With": "XMLHttpRequest",
                            "Accept-Language": "zh-CN,zh;q=0.9",
                            "Accept-Encoding": "gzip, deflate, br",
                            "Connection": "keep-alive",
                        }
                        
                        # 尝试多个可能的API接口
                        api_urls = [
                            f"https://xueqiu.com/v4/user/show.json?user_id={uid}",
                            f"https://xueqiu.com/api/v4/users/{uid}",
                            f"https://xueqiu.com/v5/user/detail.json?uid={uid}"
                        ]
                        
                        for api_url in api_urls:
                            try:
                                print(f"尝试访问API: {api_url}")
                                response = requests.get(api_url, headers=headers, timeout=15)
                                print(f"API响应状态码: {response.status_code}")
                                
                                if response.status_code == 200:
                                    try:
                                        data = response.json()
                                        print(f"API响应数据: {json.dumps(data, ensure_ascii=False)[:500]}...")
                                        
                                        # 处理不同接口的响应格式
                                        if "code" in data and data.get("code") == 0:
                                            user = data.get("data", {})
                                        elif "user" in data:
                                            user = data.get("user", {})
                                        else:
                                            user = data
                                        
                                        name = user.get("screen_name", f"用户{uid[:4]}")
                                        profile_image_url = user.get("profile_image_url", "")
                                        photo_domain = user.get('photo_domain', 'http://xavatar.imedao.com/')
                                        
                                        # 拼接完整头像URL
                                        if profile_image_url:
                                            # 取第一个头像URL（通常是最大的那个）
                                            first_image = profile_image_url.split(',')[0] if ',' in profile_image_url else profile_image_url
                                            if first_image.startswith('http'):
                                                avatar = first_image
                                            else:
                                                # 确保使用正确的头像域名
                                                if not photo_domain.endswith('/'):
                                                    photo_domain += '/'
                                                # 确保 photo_domain 有协议
                                                if photo_domain.startswith('//'):
                                                    photo_domain = 'http:' + photo_domain
                                                # 确保使用 community 路径
                                                if not first_image.startswith('community') and 'community' not in photo_domain:
                                                    photo_domain = 'http://xavatar.imedao.com/community/'
                                                avatar = f"{photo_domain}{first_image}"
                                        else:
                                            avatar = f"https://ui-avatars.com/api/?name={name}&background=random"
                                        
                                        bio = user.get("description", "")
                                        
                                        print(f"从API获取到的用户信息: 名称={name}, 头像={avatar}, 简介={bio}")
                                        
                                        return {
                                            "uid": uid,
                                            "name": name,
                                            "avatar": avatar,
                                            "bio": bio,
                                            "cookieValid": True
                                        }
                                    except json.JSONDecodeError:
                                        print("响应不是有效的JSON格式")
                            except Exception as e:
                                print(f"访问API失败: {e}")
                        
                        # 尝试使用用户时间线API获取用户信息
                        print("尝试使用用户时间线API获取用户信息")
                        url = "https://xueqiu.com/statuses/user_timeline.json"
                        params = {
                            "user_id": uid,
                            "count": 1
                        }
                        
                        try:
                            response = requests.get(url, headers=headers, params=params, timeout=10)
                            print(f"用户时间线API响应状态码: {response.status_code}")
                            
                            if response.status_code == 200:
                                data = response.json()
                                print(f"用户时间线API响应数据: {json.dumps(data, ensure_ascii=False)[:500]}")
                                # 检查响应中是否包含用户信息
                                if "statuses" in data and len(data["statuses"]) > 0:
                                    status = data["statuses"][0]
                                    if "user" in status:
                                        user = status.get("user", {})
                                        name = user.get("screen_name", f"用户{uid[:4]}")
                                        profile_image_url = user.get("profile_image_url", "")
                                        photo_domain = user.get('photo_domain', 'http://xavatar.imedao.com/')
                                        
                                        # 拼接完整头像URL
                                        if profile_image_url:
                                            # 取第一个头像URL（通常是最大的那个）
                                            first_image = profile_image_url.split(',')[0] if ',' in profile_image_url else profile_image_url
                                            if first_image.startswith('http'):
                                                avatar = first_image
                                            else:
                                                # 确保使用正确的头像域名
                                                if not photo_domain.endswith('/'):
                                                    photo_domain += '/'
                                                # 确保 photo_domain 有协议
                                                if photo_domain.startswith('//'):
                                                    photo_domain = 'http:' + photo_domain
                                                # 确保使用 community 路径
                                                if not first_image.startswith('community') and 'community' not in photo_domain:
                                                    photo_domain = 'http://xavatar.imedao.com/community/'
                                                avatar = f"{photo_domain}{first_image}"
                                        else:
                                            avatar = f"https://ui-avatars.com/api/?name={name}&background=random"
                                        
                                        bio = user.get("description", "")
                                        
                                        print(f"从用户时间线API获取到的用户信息: 名称={name}, 头像={avatar}, 简介={bio}")
                                        
                                        return {
                                            "uid": uid,
                                            "name": name,
                                            "avatar": avatar,
                                            "bio": bio,
                                            "cookieValid": True
                                        }
                        except Exception as e:
                            print(f"访问用户时间线API失败: {e}")
                        
                        # 如果所有API都失败，尝试访问用户主页
                        user_homepage_url = f"https://xueqiu.com/u/{uid}"
                        print(f"尝试访问用户主页: {user_homepage_url}")
                        
                        try:
                            response = requests.get(user_homepage_url, headers=headers, timeout=10, allow_redirects=True)
                            print(f"主页响应状态码: {response.status_code}")
                            
                            if response.status_code == 200:
                                html_content = response.text
                                print(f"主页HTML长度: {len(html_content)}")
                                
                                # 尝试从HTML中提取用户信息
                                # 提取用户名称
                                name_match = re.search(r'<h1 class="user-name">(.*?)</h1>', html_content)
                                name = name_match.group(1) if name_match else f"用户{uid[:4]}"
                                print(f"从HTML提取的名称: {name}")
                                
                                # 提取用户头像
                                avatar_match = re.search(r'<img class="avatar" src="(.*?)"', html_content)
                                avatar = avatar_match.group(1) if avatar_match else f"https://ui-avatars.com/api/?name={name}&background=random"
                                print(f"从HTML提取的头像: {avatar}")
                                
                                # 提取用户简介
                                bio_match = re.search(r'专注：(.*?)<', html_content)
                                if not bio_match:
                                    bio_match = re.search(r'<p class="bio">(.*?)</p>', html_content)
                                bio = bio_match.group(1) if bio_match else ""
                                print(f"从HTML提取的简介: {bio}")
                                
                                return {
                                    "uid": uid,
                                    "name": name,
                                    "avatar": avatar,
                                    "bio": bio,
                                    "cookieValid": True
                                }
                        except Exception as e:
                            print(f"访问用户主页失败: {str(e)}")
                        
                        # 如果所有方法都失败，使用默认信息
                        print("所有方法都失败，使用默认信息")
                        name = f"用户{uid[:4]}"
                        avatar = f"https://ui-avatars.com/api/?name=User{uid[:4]}&background=random"
                        bio = ""
                        
                        return {
                            "uid": uid,
                            "name": name,
                            "avatar": avatar,
                            "bio": bio,
                            "cookieValid": True
                        }
                except Exception as e:
                    print(f"解析JWT token失败: {str(e)}")
        
        # 如果所有方法都失败，尝试通过验证cookie是否包含必要的字段来判断cookie是否有效
        if 'xq_a_token' in cookie and 'xq_id_token' in cookie:
            # 从JWT中提取用户ID
            token_match = re.search(r'xq_id_token=([^;]+)', cookie)
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
                            uid = str(user_data['uid'])
                            return {
                                "uid": uid,
                                "name": f"用户{uid[:4]}",
                                "avatar": f"https://ui-avatars.com/api/?name=User{uid[:4]}&background=random",
                                "bio": "",
                                "cookieValid": True
                            }
                    except Exception:
                        pass
        
        return {"cookieValid": False}
    except Exception as e:
        print(f"获取用户信息失败: {str(e)}")
        return {"cookieValid": False}

# 启动时执行检查
check_all_cookies()

# API: 检查所有用户的cookie有效性
@app.route('/api/check-all-cookies', methods=['POST'])
def check_all_cookies_api():
    """检查所有用户的cookie有效性"""
    try:
        result = check_all_cookies()
        return jsonify({
            "success": True,
            "message": "所有用户的cookie有效性检查完成",
            "valid_count": result.get("valid_count", 0),
            "total_count": result.get("total_count", 0),
            "valid_users": result.get("valid_users", [])
        })
    except Exception as e:
        print(f"检查cookie有效性失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"检查cookie有效性失败: {str(e)}"
        }), 500

# API: 获取用户列表
@app.route('/api/get-users', methods=['GET'])
def get_users():
    """获取用户列表"""
    try:
        users_data = load_users()
        return jsonify({
            "success": True,
            "users": users_data.get("users", [])
        })
    except Exception as e:
        print(f"获取用户列表失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"获取用户列表失败: {str(e)}"
        }), 500

# API: 获取单个用户信息
@app.route('/api/get-user', methods=['GET'])
def get_user():
    """获取单个用户信息"""
    try:
        user_id = request.args.get('id')
        if not user_id:
            return jsonify({
                "success": False,
                "message": "缺少用户ID"
            }), 400
        
        users_data = load_users()
        user = next((u for u in users_data.get("users", []) if u.get("id") == user_id), None)
        
        if user:
            return jsonify({
                "success": True,
                "user": user
            })
        else:
            return jsonify({
                "success": False,
                "message": "用户不存在"
            }), 404
    except Exception as e:
        print(f"获取用户信息失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"获取用户信息失败: {str(e)}"
        }), 500

# API: 添加用户
@app.route('/api/add-user', methods=['POST'])
def add_user():
    """添加用户"""
    try:
        data = request.json
        cookie = data.get('cookie')
        
        if not cookie:
            return jsonify({
                "success": False,
                "message": "缺少Cookie"
            }), 400
        
        # 获取用户信息
        user_info = get_user_info(cookie)
        
        # 生成用户ID
        user_id = str(uuid.uuid4())
        
        # 创建用户对象
        new_user = {
            "id": user_id,
            "cookie": cookie,
            "uid": user_info.get("uid", ""),
            "name": user_info.get("name", ""),
            "avatar": user_info.get("avatar", ""),
            "bio": user_info.get("bio", ""),
            "cookieValid": user_info.get("cookieValid", False),
            "isDefault": False
        }
        
        # 加载现有用户
        users_data = load_users()
        
        # 如果是第一个用户，设为默认
        if len(users_data.get("users", [])) == 0:
            new_user["isDefault"] = True
            users_data["defaultUserId"] = user_id
        
        # 添加用户
        users_data["users"].append(new_user)
        save_users(users_data)
        
        return jsonify({
            "success": True,
            "message": "用户添加成功",
            "user": new_user
        })
    except Exception as e:
        print(f"添加用户失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"添加用户失败: {str(e)}"
        }), 500

# API: 更新用户
@app.route('/api/update-user', methods=['POST'])
def update_user():
    """更新用户"""
    try:
        data = request.json
        user_id = data.get('id')
        cookie = data.get('cookie')
        
        if not user_id or not cookie:
            return jsonify({
                "success": False,
                "message": "缺少用户ID或Cookie"
            }), 400
        
        # 获取用户信息
        user_info = get_user_info(cookie)
        
        # 加载现有用户
        users_data = load_users()
        
        # 查找用户
        user_index = next((i for i, u in enumerate(users_data.get("users", [])) if u.get("id") == user_id), -1)
        
        if user_index == -1:
            return jsonify({
                "success": False,
                "message": "用户不存在"
            }), 404
        
        # 更新用户信息
        updated_user = users_data["users"][user_index]
        updated_user["cookie"] = cookie
        updated_user["uid"] = user_info.get("uid", updated_user.get("uid", ""))
        updated_user["name"] = user_info.get("name", updated_user.get("name", ""))
        updated_user["avatar"] = user_info.get("avatar", updated_user.get("avatar", ""))
        updated_user["bio"] = user_info.get("bio", updated_user.get("bio", ""))
        updated_user["cookieValid"] = user_info.get("cookieValid", False)
        
        # 保存更新
        users_data["users"][user_index] = updated_user
        save_users(users_data)
        
        return jsonify({
            "success": True,
            "message": "用户更新成功",
            "user": updated_user
        })
    except Exception as e:
        print(f"更新用户失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"更新用户失败: {str(e)}"
        }), 500

# API: 删除用户
@app.route('/api/delete-user', methods=['POST'])
def delete_user():
    """删除用户"""
    try:
        data = request.json
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({
                "success": False,
                "message": "缺少用户ID"
            }), 400
        
        # 加载现有用户
        users_data = load_users()
        
        # 查找用户
        user_index = next((i for i, u in enumerate(users_data.get("users", [])) if u.get("id") == user_id), -1)
        
        if user_index == -1:
            return jsonify({
                "success": False,
                "message": "用户不存在"
            }), 404
        
        # 检查是否是默认用户
        is_default = users_data.get("defaultUserId") == user_id
        
        # 删除用户
        users_data["users"].pop(user_index)
        
        # 如果删除的是默认用户，设置新的默认用户
        if is_default and len(users_data.get("users", [])) > 0:
            users_data["defaultUserId"] = users_data["users"][0]["id"]
            users_data["users"][0]["isDefault"] = True
        elif is_default:
            users_data["defaultUserId"] = None
        
        save_users(users_data)
        
        return jsonify({
            "success": True,
            "message": "用户删除成功"
        })
    except Exception as e:
        print(f"删除用户失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"删除用户失败: {str(e)}"
        }), 500

# API: 设置默认用户
@app.route('/api/set-default-user', methods=['POST'])
def set_default_user():
    """设置默认用户"""
    try:
        data = request.json
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({
                "success": False,
                "message": "缺少用户ID"
            }), 400
        
        # 加载现有用户
        users_data = load_users()
        
        # 查找用户
        user = next((u for u in users_data.get("users", []) if u.get("id") == user_id), None)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "用户不存在"
            }), 404
        
        # 更新默认状态
        for u in users_data.get("users", []):
            u["isDefault"] = (u.get("id") == user_id)
        
        users_data["defaultUserId"] = user_id
        save_users(users_data)
        
        return jsonify({
            "success": True,
            "message": "默认用户设置成功"
        })
    except Exception as e:
        print(f"设置默认用户失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"设置默认用户失败: {str(e)}"
        }), 500

# API: 获取默认用户
@app.route('/api/get-default-user', methods=['GET'])
def get_default_user():
    """获取默认用户"""
    try:
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        
        if default_user_id:
            default_user = next((u for u in users_data.get("users", []) if u.get("id") == default_user_id), None)
            if default_user:
                return jsonify({
                    "success": True,
                    "user": default_user
                })
        
        return jsonify({
            "success": False,
            "message": "没有设置默认用户"
        }), 404
    except Exception as e:
        print(f"获取默认用户失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"获取默认用户失败: {str(e)}"
        }), 500

class FollowingCommenterTask:
    """关注者评论任务管理器"""
    def __init__(self):
        self.is_running = False
        self._stop_event = threading.Event()
        self._thread = None
    
    def start(self, selected_users, posts_per_user, test_mode, action_type, log_callback):
        """启动任务"""
        self.is_running = True
        self._stop_event.clear()
        
        def process_task():
            try:
                result = process_following_comments(
                    selected_users=selected_users, 
                    posts_per_user=posts_per_user, 
                    test_mode=test_mode,
                    action_type=action_type,
                    log_callback=log_callback,
                    stop_event=self._stop_event
                )
                # 更新最终状态
                following_comments_status['processedUsers'] = result['stats']['total_users']
                following_comments_status['processedPosts'] = result['stats']['total_posts']
                following_comments_status['successComments'] = result['stats']['total_comments']
                following_comments_status['failedAttempts'] = result['stats']['total_posts'] - result['stats']['total_comments']
            except Exception as e:
                error_log = {
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'处理失败: {str(e)}',
                    'type': 'error'
                }
                following_comments_logs.append(error_log)
            finally:
                self.is_running = False
                following_comments_status['isRunning'] = False
        
        self._thread = threading.Thread(target=process_task)
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self):
        """停止任务"""
        self._stop_event.set()
        self.is_running = False
        following_comments_status['isRunning'] = False
    
    def is_stopped(self):
        """检查是否已停止"""
        return self._stop_event.is_set()

class TopicCommenterTask:
    """话题评论任务管理器"""
    def __init__(self):
        self.is_running = False
        self._stop_event = threading.Event()
        self._thread = None
    
    def start(self, article_ids, selected_model, models_config, articles, log_callback):
        """启动任务"""
        self.is_running = True
        self._stop_event.clear()
        
        def process_task():
            try:
                result = process_topic_comments(
                    article_ids=article_ids,
                    selected_model=selected_model,
                    models_config=models_config,
                    articles=articles,
                    log_callback=log_callback,
                    stop_event=self._stop_event
                )
                topic_comments_status['processedArticles'] = result['totalArticles']
                topic_comments_status['successComments'] = result['successCount']
                topic_comments_status['failedAttempts'] = result['failedCount']
            except Exception as e:
                error_log = {
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'处理失败: {str(e)}',
                    'type': 'error'
                }
                topic_comments_logs.append(error_log)
            finally:
                self.is_running = False
                topic_comments_status['isRunning'] = False
        
        self._thread = threading.Thread(target=process_task)
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self):
        """停止任务"""
        self._stop_event.set()
        self.is_running = False
        topic_comments_status['isRunning'] = False
    
    def is_stopped(self):
        """检查是否已停止"""
        return self._stop_event.is_set()

class RewardCommenterTask:
    """悬赏评论任务管理器"""
    def __init__(self):
        self.is_running = False
        self._stop_event = threading.Event()
        self._thread = None
    
    def start(self, article_ids, selected_model, models_config, articles, log_callback):
        """启动任务"""
        self.is_running = True
        self._stop_event.clear()
        
        def process_task():
            try:
                result = process_reward_comments(
                    article_ids=article_ids,
                    selected_model=selected_model,
                    models_config=models_config,
                    articles=articles,
                    log_callback=log_callback,
                    stop_event=self._stop_event
                )
                reward_comments_status['processedArticles'] = result['totalArticles']
                reward_comments_status['successComments'] = result['successCount']
                reward_comments_status['failedAttempts'] = result['failedCount']
            except Exception as e:
                error_log = {
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'处理失败: {str(e)}',
                    'type': 'error'
                }
                reward_comments_logs.append(error_log)
            finally:
                self.is_running = False
                reward_comments_status['isRunning'] = False
        
        self._thread = threading.Thread(target=process_task)
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self):
        """停止任务"""
        self._stop_event.set()
        self.is_running = False
        reward_comments_status['isRunning'] = False
    
    def is_stopped(self):
        """检查是否已停止"""
        return self._stop_event.is_set()

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "success": True,
        "message": "服务运行正常"
    })

@app.route('/api/start-commenting', methods=['POST'])
def start_commenting():
    """开始评论任务"""
    global commenter_instance
    
    try:
        print("收到启动评论任务的请求")
        config = request.json
        
        print(f"请求体: {config}")
        
        # 验证参数
        if not config:
            print("错误: 请求体不能为空")
            return jsonify({
                "success": False,
                "message": "请求体不能为空"
            }), 400
        
        # 提取模型信息
        selected_model = config.get('selectedModel', 'ark')
        models_config = config.get('models', {})
        
        # 提取 API Key
        api_key = None
        if selected_model == 'ark' and models_config.get('ark'):
            api_key = models_config['ark'].get('apiKey')
        elif selected_model == 'openai' and models_config.get('openai'):
            api_key = models_config['openai'].get('apiKey')
        elif selected_model == 'baidu' and models_config.get('baidu'):
            api_key = models_config['baidu'].get('apiKey')
        elif selected_model == 'alibaba' and models_config.get('alibaba'):
            api_key = models_config['alibaba'].get('apiKey')
        elif selected_model == 'deepseek' and models_config.get('deepseek'):
            api_key = models_config['deepseek'].get('apiKey')
        elif selected_model == 'gemini' and models_config.get('gemini'):
            api_key = models_config['gemini'].get('apiKey')
        elif selected_model == 'claude' and models_config.get('claude'):
            api_key = models_config['claude'].get('apiKey')
        elif config.get('arkApiKey'):
            api_key = config.get('arkApiKey')
            selected_model = 'ark'
        
        if not api_key:
            print("错误: 缺少AI API Key")
            return jsonify({
                "success": False,
                "message": "缺少AI API Key"
            }), 400
        
        # 获取默认用户的cookie
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        if not default_user_id:
            return jsonify({
                "success": False,
                "message": "请先配置用户并设置默认用户"
            }), 400
        
        default_user = next((u for u in users_data.get("users", []) if u.get("id") == default_user_id), None)
        if not default_user or not default_user.get("cookie"):
            return jsonify({
                "success": False,
                "message": "默认用户cookie未配置"
            }), 400
        
        xueqiu_cookie = default_user.get("cookie")
        
        with commenter_lock:
            # 检查是否已有运行中的任务
            if commenter_instance and commenter_instance.is_running:
                print("错误: 评论任务已在运行中")
                return jsonify({
                    "success": False,
                    "message": "评论任务已在运行中"
                }), 400
            
            # 定义日志回调函数，实时更新日志
            def log_callback(log_entry):
                # 日志已经通过add_log方法添加到commenter_instance.logs中
                # 这里不需要额外处理，因为get_run_status会直接读取commenter_instance.logs
                pass
            
            # 创建新的评论器实例
            print("创建新的评论器实例")
            commenter_instance = XueQiuCommenter(
                ark_api_key=api_key,
                xueqiu_cookie=xueqiu_cookie,
                log_callback=log_callback,
                model_type=selected_model
            )
            
            # 启动评论任务
            daily_limit = config.get('dailyLimit', 30)
            delay_min = config.get('delayMin', 30)
            delay_max = config.get('delayMax', 120)
            test_mode = config.get('testMode', False)
            task_type = config.get('taskType', 'hot')
            
            # 打印任务启动信息，便于调试
            print(f"启动评论任务: {task_type}, 每日限制: {daily_limit}, 延迟: {delay_min}-{delay_max}秒, 测试模式: {test_mode}")
            print(f"使用模型: {selected_model}")
            
            task_thread = threading.Thread(
                target=commenter_instance.run_task,
                args=(daily_limit, delay_min, delay_max, test_mode, task_type)
            )
            task_thread.daemon = True
            task_thread.start()
            
            # 等待线程启动，确保任务开始执行
            time.sleep(1)
            
            print("评论任务已启动")
            return jsonify({
                "success": True,
                "message": "评论任务已启动"
            })
            
    except Exception as e:
        print(f"启动评论任务失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"启动评论任务失败: {str(e)}"
        }), 500

@app.route('/api/stop-commenting', methods=['POST'])
def stop_commenting():
    """停止评论任务"""
    global commenter_instance, following_commenter_instance
    
    try:
        # 检查关注者评论任务
        with following_commenter_lock:
            if following_commenter_instance and following_commenter_instance.is_running:
                following_commenter_instance.stop()
                return jsonify({
                    "success": True,
                    "message": "关注者评论任务已停止"
                })
        
        # 检查热门帖/推荐帖评论任务
        with commenter_lock:
            if not commenter_instance:
                return jsonify({
                    "success": False,
                    "message": "没有运行中的评论任务"
                }), 400
            
            commenter_instance.stop()
            
            return jsonify({
                "success": True,
                "message": "评论任务已停止"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"停止评论任务失败: {str(e)}"
        }), 500

@app.route('/api/run-status', methods=['GET'])
def get_run_status():
    """获取运行状态和日志"""
    global commenter_instance, following_commenter_instance, following_comments_logs, following_comments_status
    global topic_comments_instance, topic_comments_logs, topic_comments_status
    global reward_comments_instance, reward_comments_logs, reward_comments_status
    
    try:
        # 检查话题评论任务状态（最高优先级）
        topic_commenter = None
        with topic_comments_lock:
            topic_commenter = topic_comments_instance
        
        if topic_commenter and topic_commenter.is_running:
            return jsonify({
                "success": True,
                "isRunning": True,
                "taskType": "topic",
                "data": topic_comments_status,
                "logs": topic_comments_logs[-50:],
                "message": "获取运行状态成功"
            })
        
        # 检查悬赏评论任务状态
        reward_commenter = None
        with reward_comments_lock:
            reward_commenter = reward_comments_instance
        
        if reward_commenter and reward_commenter.is_running:
            return jsonify({
                "success": True,
                "isRunning": True,
                "taskType": "reward",
                "data": reward_comments_status,
                "logs": reward_comments_logs[-50:],
                "message": "获取运行状态成功"
            })
        
        # 检查热门帖/推荐帖评论任务状态
        commenter = None
        with commenter_lock:
            commenter = commenter_instance
        
        if commenter and commenter.is_running:
            return jsonify({
                "success": True,
                "isRunning": True,
                "taskType": "commenting",
                "data": commenter.get_stats(),
                "logs": commenter.get_logs()[-50:],
                "message": "获取运行状态成功"
            })
        
        # 检查关注者评论任务状态
        following_commenter = None
        with following_commenter_lock:
            following_commenter = following_commenter_instance
        
        if following_commenter and following_commenter.is_running:
            return jsonify({
                "success": True,
                "isRunning": True,
                "taskType": "following",
                "data": following_comments_status,
                "logs": following_comments_logs[-50:],
                "message": "获取运行状态成功"
            })
        
        # 检查已停止的任务（话题评论）
        if topic_commenter:
            return jsonify({
                "success": True,
                "isRunning": False,
                "taskType": "topic",
                "data": topic_comments_status,
                "logs": topic_comments_logs[-50:],
                "message": "获取运行状态成功"
            })
        
        # 检查已停止的任务（悬赏评论）
        if reward_commenter:
            return jsonify({
                "success": True,
                "isRunning": False,
                "taskType": "reward",
                "data": reward_comments_status,
                "logs": reward_comments_logs[-50:],
                "message": "获取运行状态成功"
            })
        
        # 检查已停止的任务（关注者评论）
        if following_commenter:
            return jsonify({
                "success": True,
                "isRunning": False,
                "taskType": "following",
                "data": following_comments_status,
                "logs": following_comments_logs[-50:],
                "message": "获取运行状态成功"
            })
        
        # 检查已停止的任务（热门帖/推荐帖）
        if commenter:
            return jsonify({
                "success": True,
                "isRunning": False,
                "taskType": "commenting",
                "data": commenter.get_stats(),
                "logs": commenter.get_logs()[-50:],
                "message": "获取运行状态成功"
            })
        
        # 如果没有任务，返回空状态
        return jsonify({
            "success": True,
            "isRunning": False,
            "data": {
                "processedArticles": 0,
                "successComments": 0,
                "failedAttempts": 0
            },
            "logs": [],
            "message": "获取运行状态成功"
        })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取运行状态失败: {str(e)}"
        }), 500

@app.route('/api/get-following-list', methods=['POST'])
def get_following_list():
    """获取用户关注列表"""
    try:
        # 获取默认用户的cookie
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        if not default_user_id:
            return jsonify({
                "success": False,
                "message": "请先配置用户并设置默认用户"
            }), 400
        
        default_user = next((u for u in users_data.get("users", []) if u.get("id") == default_user_id), None)
        if not default_user or not default_user.get("cookie"):
            return jsonify({
                "success": False,
                "message": "默认用户cookie未配置"
            }), 400
        
        xueqiu_cookie = default_user.get("cookie")
        
        # 创建关注列表获取器实例
        fetcher = FollowingListFetcher(xueqiu_cookie)
        
        # 获取当前用户ID
        user_id = fetcher.get_current_user_id()
        if not user_id:
            return jsonify({
                "success": False,
                "message": "无法获取用户ID，请检查Cookie是否有效"
            }), 400
        
        # 获取关注列表
        following_list = fetcher.get_following_list_formatted(user_id)
        
        # 获取文本格式
        following_text = fetcher.get_following_list_text(user_id)
        
        # 保存到本地文件
        following_file = os.path.join(os.path.dirname(__file__), 'config', 'following_list.json')
        with open(following_file, 'w', encoding='utf-8') as f:
            json.dump({
                'userId': user_id,
                'followingList': following_list,
                'totalCount': len(following_list),
                'updateTime': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "data": {
                "userId": user_id,
                "followingList": following_list,
                "followingText": following_text,
                "totalCount": len(following_list)
            },
            "message": f"成功获取 {len(following_list)} 个关注用户"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取关注列表失败: {str(e)}"
        }), 500

@app.route('/api/check-following-cache', methods=['GET'])
def check_following_cache():
    """检查本地缓存的关注列表"""
    try:
        following_file = os.path.join(os.path.dirname(__file__), 'config', 'following_list.json')
        
        if os.path.exists(following_file):
            with open(following_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # 返回完整的关注者列表数据
            return jsonify({
                "success": True,
                "exists": True,
                "data": {
                    "userId": cached_data.get('userId'),
                    "totalCount": cached_data.get('totalCount'),
                    "updateTime": cached_data.get('updateTime'),
                    "followingList": cached_data.get('followingList', [])
                },
                "message": f"发现本地缓存：{cached_data.get('totalCount')} 个关注用户，更新时间：{cached_data.get('updateTime')}"
            })
        else:
            return jsonify({
                "success": True,
                "exists": False,
                "message": "本地无缓存数据"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"检查缓存失败: {str(e)}"
        }), 500

@app.route('/api/get-following-list', methods=['POST'])
def get_following_list_api():
    """获取关注者列表"""
    try:
        # 获取默认用户的cookie
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        if not default_user_id:
            return jsonify({
                "success": False,
                "message": "请先配置用户并设置默认用户"
            }), 400
        
        default_user = next((u for u in users_data.get("users", []) if u.get("id") == default_user_id), None)
        if not default_user or not default_user.get("cookie"):
            return jsonify({
                "success": False,
                "message": "默认用户cookie未配置"
            }), 400
        
        xue_qiu_cookie = default_user.get("cookie")
        
        # 使用FollowingListFetcher获取关注列表
        fetcher = FollowingListFetcher(xue_qiu_cookie)
        
        # 获取当前用户ID
        user_id = fetcher.get_current_user_id()
        if not user_id:
            return jsonify({
                "success": False,
                "message": "无法获取用户ID，请检查Cookie是否有效"
            }), 400
        
        # 获取关注列表
        following_list = fetcher.get_following_list_formatted(user_id)
        
        # 保存到本地文件
        following_file = os.path.join(os.path.dirname(__file__), 'config', 'following_list.json')
        with open(following_file, 'w', encoding='utf-8') as f:
            json.dump({
                'userId': user_id,
                'followingList': following_list,
                'totalCount': len(following_list),
                'updateTime': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "data": {
                'userId': user_id,
                'followingList': following_list,
                'totalCount': len(following_list),
                'updateTime': time.strftime('%Y-%m-%d %H:%M:%S')
            },
            "message": f"成功获取 {len(following_list)} 个关注用户"
        })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取关注列表失败: {str(e)}"
        }), 500

@app.route('/api/following-config', methods=['GET'])
def get_following_config():
    """获取关注列表配置"""
    try:
        following_file = os.path.join(os.path.dirname(__file__), 'config', 'following_list.json')
        
        if os.path.exists(following_file):
            with open(following_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return jsonify({
                "success": True,
                "data": data,
                "message": "获取关注列表配置成功"
            })
        else:
            return jsonify({
                "success": True,
                "data": {
                    "followingList": [],
                    "updatedAt": ""
                },
                "message": "暂无关注列表数据"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取关注列表配置失败: {str(e)}"
        }), 500

@app.route('/api/following-config', methods=['POST'])
def save_following_config():
    """保存关注列表配置"""
    try:
        data = request.json
        
        following_file = os.path.join(os.path.dirname(__file__), 'config', 'following_list.json')
        
        with open(following_file, 'w', encoding='utf-8') as f:
            json.dump({
                "followingList": data.get("followingList", []),
                "updatedAt": time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "message": "保存关注列表配置成功"
        })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"保存关注列表配置失败: {str(e)}"
        }), 500

@app.route('/api/toggle-important', methods=['POST'])
def toggle_important():
    """切换用户的重点关注状态"""
    try:
        data = request.json
        user_uid = data.get("uid")
        
        if not user_uid:
            return jsonify({
                "success": False,
                "message": "用户UID不能为空"
            }), 400
        
        following_file = os.path.join(os.path.dirname(__file__), 'config', 'following_list.json')
        
        if os.path.exists(following_file):
            with open(following_file, 'r', encoding='utf-8') as f:
                following_data = json.load(f)
        else:
            following_data = {
                "followingList": [],
                "updatedAt": ""
            }
        
        following_list = following_data.get("followingList", [])
        
        user_found = False
        for user in following_list:
            if str(user.get("uid")) == str(user_uid):
                user["isImportant"] = not user.get("isImportant", False)
                user_found = True
                break
        
        if not user_found:
            return jsonify({
                "success": False,
                "message": "未找到该用户"
            }), 404
        
        following_data["updatedAt"] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        with open(following_file, 'w', encoding='utf-8') as f:
            json.dump(following_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "data": {
                "uid": user_uid,
                "isImportant": user.get("isImportant", False)
            },
            "message": "切换重点关注状态成功"
        })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"切换重点关注状态失败: {str(e)}"
        }), 500

def load_config():
    """加载配置文件（内部使用，返回原始数据）"""
    try:
        config_file = os.path.join(os.path.dirname(__file__), 'config', 'defaultConfig.json')
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {}
            
    except Exception as e:
        print(f"加载配置失败: {str(e)}")
        return {}

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置（API端点）"""
    try:
        config_data = load_config()
        return jsonify({
            "success": True,
            "exists": bool(config_data),
            "data": config_data,
            "message": "配置加载成功"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"加载配置失败: {str(e)}"
        }), 500

@app.route('/api/config', methods=['POST'])
def save_config():
    """保存配置文件"""
    try:
        config_data = request.json
        
        if not config_data:
            return jsonify({
                "success": False,
                "message": "配置数据不能为空"
            }), 400
        
        config_file = os.path.join(os.path.dirname(__file__), 'config', 'defaultConfig.json')
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "message": "配置保存成功"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"保存配置失败: {str(e)}"
        }), 500

@app.route('/api/start-following-comments', methods=['POST'])
def start_following_comments():
    """启动关注者评论"""
    global following_commenter_instance, following_comments_logs, following_comments_status
    
    try:
        data = request.json
        selected_users = data.get('selectedUsers', [])
        posts_per_user = data.get('postsPerUser', 10)
        test_mode = data.get('testMode', False)
        action_type = data.get('actionType', 'comment')  # 'comment' 或 'like'
        
        # 验证参数
        if not selected_users or len(selected_users) == 0:
            return jsonify({
                "success": False,
                "message": "请至少选择一个关注者"
            }), 400
        
        with following_commenter_lock:
            # 检查是否已有运行中的任务
            if following_commenter_instance and following_commenter_instance.is_running:
                return jsonify({
                    "success": False,
                    "message": "关注者评论任务已在运行中"
                }), 400
            
            # 重置状态和日志
            following_comments_logs = []
            following_comments_status = {
                'isRunning': True,
                'processedUsers': 0,
                'processedPosts': 0,
                'successComments': 0,
                'failedAttempts': 0,
                'actionType': action_type
            }
            
            # 实时日志回调函数
            def log_callback(log_entry):
                following_comments_logs.append(log_entry)
                # 更新状态
                if '处理用户' in log_entry['message']:
                    following_comments_status['processedUsers'] += 1
                elif '✅ 评论发布成功' in log_entry['message'] or '✅ 点赞成功' in log_entry['message']:
                    following_comments_status['successComments'] += 1
                    following_comments_status['processedPosts'] += 1
                elif '❌ 评论发布失败' in log_entry['message'] or '❌ 点赞失败' in log_entry['message']:
                    following_comments_status['failedAttempts'] += 1
                    following_comments_status['processedPosts'] += 1
                elif '测试模式：跳过发布评论' in log_entry['message'] or '测试模式：跳过点赞' in log_entry['message']:
                    following_comments_status['processedPosts'] += 1
            
            # 创建任务管理器并启动任务
            following_commenter_instance = FollowingCommenterTask()
            following_commenter_instance.start(
                selected_users=selected_users,
                posts_per_user=posts_per_user,
                test_mode=test_mode,
                action_type=action_type,
                log_callback=log_callback
            )
            
            action_type_text = '点赞' if action_type == 'like' else '评论'
            return jsonify({
                "success": True,
                "message": f"关注者{action_type_text}任务已启动"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"启动关注者评论任务失败: {str(e)}"
        }), 500

@app.route('/api/stop-following-comments', methods=['POST'])
def stop_following_comments():
    """停止关注者评论任务"""
    global following_commenter_instance
    
    try:
        with following_commenter_lock:
            if following_commenter_instance:
                following_commenter_instance.stop()
                following_comments_status['isRunning'] = False
                return jsonify({
                    "success": True,
                    "message": "关注者评论任务已停止"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "没有运行中的关注者评论任务"
                }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"停止关注者评论任务失败: {str(e)}"
        }), 500

@app.route('/api/generate-prompt', methods=['POST'])
def generate_prompt():
    """生成详细提示词（第一轮）"""
    try:
        data = request.json
        prompt = data.get('prompt', '')
        post_type = data.get('postType', 'discussion')
        selected_model = data.get('selectedModel', 'ark')
        models = data.get('models', {})
        
        if not prompt:
            return jsonify({
                "success": False,
                "message": "提示词不能为空"
            }), 400
        
        # 获取API Key
        api_key = None
        if selected_model == 'ark' and models.get('ark'):
            api_key = models['ark'].get('apiKey')
        elif selected_model == 'openai' and models.get('openai'):
            api_key = models['openai'].get('apiKey')
        elif selected_model == 'baidu' and models.get('baidu'):
            api_key = models['baidu'].get('apiKey')
        elif selected_model == 'alibaba' and models.get('alibaba'):
            api_key = models['alibaba'].get('apiKey')
        elif selected_model == 'deepseek' and models.get('deepseek'):
            api_key = models['deepseek'].get('apiKey')
        elif selected_model == 'gemini' and models.get('gemini'):
            api_key = models['gemini'].get('apiKey')
        elif selected_model == 'claude' and models.get('claude'):
            api_key = models['claude'].get('apiKey')
        
        if not api_key:
            return jsonify({
                "success": False,
                "message": "缺少AI API Key"
            }), 400
        
        print(f"[{time.strftime('%H:%M:%S')}] 【第一轮】正在生成雪球风格的详细提示词...")
        print(f"[{time.strftime('%H:%M:%S')}] 使用模型: {selected_model}")
        
        first_round_prompt = f"""你是一位资深的雪球网内容创作者，擅长撰写投资类文章。

用户想要写一篇关于"{prompt}"的内容。

请根据用户的简单描述，生成一个详细的、适合雪球平台风格的写作提示词。

要求：
1. 分析用户的意图，确定文章的核心主题和角度
2. 明确目标读者群体（如散户、机构投资者、新手等）
3. 确定文章的风格（如专业分析、经验分享、观点表达等）
4. 列出文章应该包含的关键要点
5. 建议合适的标题方向
6. 如果是股票分析，建议包含：公司基本面、行业地位、财务数据、风险提示等
7. 如果是市场观点，建议包含：逻辑推理、数据支撑、结论明确等

请直接返回生成的详细提示词，这个提示词将用于第二轮生成正式文章。

生成的详细提示词："""
        
        # 第一轮调用 - 使用统一模型适配器
        detailed_prompt, _ = call_model(
            selected_model, 
            api_key, 
            first_round_prompt, 
            'discussion',
            secret_key=models.get(selected_model, {}).get('secretKey'),
            base_url=models.get(selected_model, {}).get('baseUrl'),
            model_name=models.get(selected_model, {}).get('modelName'),
            max_tokens=models.get(selected_model, {}).get('maxTokens'),
            temperature=models.get(selected_model, {}).get('temperature'),
            operation_type='生成详细提示词',
            default_prompt=prompt
        )
        
        print(f"[{time.strftime('%H:%M:%S')}] 【第一轮】详细提示词生成成功")
        print(f"[{time.strftime('%H:%M:%S')}] 生成的提示词预览: {detailed_prompt[:100]}...")
        
        return jsonify({
            "success": True,
            "detailedPrompt": detailed_prompt
        })
        
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 生成提示词失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"生成提示词失败: {str(e)}"
        }), 500

@app.route('/api/generate-content', methods=['POST'])
def generate_content():
    """根据提示词生成内容（第二轮）"""
    try:
        data = request.json
        detailed_prompt = data.get('detailedPrompt', '')
        post_type = data.get('postType', 'discussion')
        selected_model = data.get('selectedModel', 'ark')
        models = data.get('models', {})
        
        if not detailed_prompt:
            return jsonify({
                "success": False,
                "message": "详细提示词不能为空"
            }), 400
        
        # 获取API Key
        api_key = None
        if selected_model == 'ark' and models.get('ark'):
            api_key = models['ark'].get('apiKey')
        elif selected_model == 'openai' and models.get('openai'):
            api_key = models['openai'].get('apiKey')
        elif selected_model == 'baidu' and models.get('baidu'):
            api_key = models['baidu'].get('apiKey')
        elif selected_model == 'alibaba' and models.get('alibaba'):
            api_key = models['alibaba'].get('apiKey')
        elif selected_model == 'deepseek' and models.get('deepseek'):
            api_key = models['deepseek'].get('apiKey')
        elif selected_model == 'gemini' and models.get('gemini'):
            api_key = models['gemini'].get('apiKey')
        elif selected_model == 'claude' and models.get('claude'):
            api_key = models['claude'].get('apiKey')
        
        if not api_key:
            return jsonify({
                "success": False,
                "message": "缺少AI API Key"
            }), 400
        
        print(f"[{time.strftime('%H:%M:%S')}] 【第二轮】正在根据详细提示词生成正式文章...")
        print(f"[{time.strftime('%H:%M:%S')}] 内容类型: {post_type}, 使用模型: {selected_model}")
        
        if post_type == 'article':
            second_round_prompt = f"""请根据以下详细提示词，写一篇雪球网风格的投资分析文章：

{detailed_prompt}

写作要求：
1. 文章标题要吸引人，能引起读者兴趣
2. 内容要有深度，包含具体的数据和分析
3. 语言要自然流畅，像是一个资深投资者写的
4. 避免使用"首先"、"其次"、"最后"等过于刻板的表达
5. 可以适当使用一些口语化的表达，让文章更接地气
6. 要有个人观点，不要泛泛而谈
7. 文章长度在800-1500字之间
8. 如果是股票分析，要包含具体的投资逻辑和风险提示

请按以下格式返回：
标题：[文章标题]

[文章正文]"""
        else:
            second_round_prompt = f"""请根据以下详细提示词，写一条雪球网风格的讨论：

{detailed_prompt}

写作要求：
1. 内容要简洁有力，像是一个资深投资者在分享观点
2. 语言要自然，避免AI的味道
3. 可以适当使用一些投资圈的术语
4. 长度在100-300字之间
5. 要有个人观点，不要泛泛而谈
6. 如果是股票观点，要有明确的看多/看空逻辑

直接返回讨论内容即可，不要加标题。"""
        
        # 第二轮调用 - 使用统一模型适配器
        content, title = call_model(
            selected_model, 
            api_key, 
            second_round_prompt, 
            post_type,
            secret_key=models.get(selected_model, {}).get('secretKey'),
            base_url=models.get(selected_model, {}).get('baseUrl'),
            model_name=models.get(selected_model, {}).get('modelName'),
            max_tokens=models.get(selected_model, {}).get('maxTokens'),
            temperature=models.get(selected_model, {}).get('temperature'),
            operation_type='生成内容',
            default_prompt=detailed_prompt
        )
        
        print(f"[{time.strftime('%H:%M:%S')}] 【第二轮】正式文章生成成功")
        
        print(f"[{time.strftime('%H:%M:%S')}] 开始转换markdown格式到HTML...")
        content = text_to_html(content)
        print(f"[{time.strftime('%H:%M:%S')}] markdown格式转换完成")
        
        return jsonify({
            "success": True,
            "content": content,
            "title": title
        })
        
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 生成内容失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"生成内容失败: {str(e)}"
        }), 500

@app.route('/api/publish-post', methods=['POST'])
def publish_post():
    """发布帖子到雪球"""
    try:
        data = request.json
        post_type = data.get('postType', 'discussion')
        content = data.get('content', '')
        title = data.get('title', '')
        is_column = data.get('isColumn', False)
        
        if not content:
            return jsonify({
                "success": False,
                "message": "内容不能为空"
            }), 400
        
        # 获取默认用户的cookie
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        if not default_user_id:
            return jsonify({
                "success": False,
                "message": "请先配置用户并设置默认用户"
            }), 400
        
        default_user = next((u for u in users_data.get("users", []) if u.get("id") == default_user_id), None)
        if not default_user or not default_user.get("cookie"):
            return jsonify({
                "success": False,
                "message": "默认用户cookie未配置"
            }), 400
        
        xueqiu_cookie = default_user.get("cookie")
        
        if post_type == 'article' and not title:
            return jsonify({
                "success": False,
                "message": "文章标题不能为空"
            }), 400
        
        print(f"[{time.strftime('%H:%M:%S')}] 正在发布{post_type == 'article' and '长文' or '讨论'}...")
        
        # 发布帖子
        if post_type == 'article':
            post_id = publish_article_to_xueqiu(title, content, is_column, xueqiu_cookie)
        else:
            post_id = publish_discussion_to_xueqiu(content, xueqiu_cookie)
        
        print(f"[{time.strftime('%H:%M:%S')}] 发布成功，帖子ID: {post_id}")
        
        return jsonify({
            "success": True,
            "postId": post_id,
            "message": "发布成功"
        })
        
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 发布失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"发布失败: {str(e)}"
        }), 500

# 文本转HTML函数
def text_to_html(text):
    """将纯文本转换为HTML格式"""
    import re
    
    # 先清理文本：移除首尾的空白和多余的星号
    text = text.strip()
    
    # 先处理Markdown标题格式
    # 处理六级标题 ###### text
    text = re.sub(r'^######\s+(.+)$', r'<h6>\1</h6>', text, flags=re.MULTILINE)
    # 处理五级标题 ##### text
    text = re.sub(r'^#####\s+(.+)$', r'<h5>\1</h5>', text, flags=re.MULTILINE)
    # 处理四级标题 #### text
    text = re.sub(r'^####\s+(.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    # 处理三级标题 ### text
    text = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    # 处理二级标题 ## text
    text = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    # 处理一级标题 # text
    text = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    
    # 处理Markdown格式的粗体和斜体
    # 处理粗体 **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # 处理斜体 *text*（确保不与粗体冲突）
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    
    # 处理列表
    lines = text.split('\n')
    in_list = False
    list_type = None
    result_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # 跳过已转换为标题的行
        if re.match(r'^<h[1-6]>.*</h[1-6]>$', stripped):
            result_lines.append(stripped)
            continue
        
        # 检测无序列表
        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list or list_type != 'ul':
                if in_list:
                    result_lines.append(f'</{list_type}>')
                result_lines.append('<ul>')
                in_list = True
                list_type = 'ul'
            result_lines.append(f'<li>{stripped[2:]}</li>')
        # 检测有序列表
        elif re.match(r'^\d+\.\s', stripped):
            if not in_list or list_type != 'ol':
                if in_list:
                    result_lines.append(f'</{list_type}>')
                result_lines.append('<ol>')
                in_list = True
                list_type = 'ol'
            # 提取列表项内容
            content = re.sub(r'^\d+\.\s', '', stripped)
            result_lines.append(f'<li>{content}</li>')
        else:
            # 如果之前在列表中，关闭列表
            if in_list:
                result_lines.append(f'</{list_type}>')
                in_list = False
                list_type = None
            
            # 处理普通段落
            if stripped:
                result_lines.append(f'<p>{stripped}</p>')
    
    # 如果最后还在列表中，关闭列表
    if in_list:
        result_lines.append(f'</{list_type}>')
    
    return '\n'.join(result_lines)

# HTML转Markdown函数
def html_to_markdown(html_content):
    """将HTML内容转换为Markdown格式"""
    from html.parser import HTMLParser
    import re
    
    class HTMLToMarkdown(HTMLParser):
        def __init__(self):
            super().__init__()
            self.result = []
            self.in_list = False
            self.list_type = None
            self.list_counter = 0
            
        def handle_starttag(self, tag, attrs):
            if tag in ['b', 'strong']:
                self.result.append('**')
            elif tag in ['i', 'em']:
                self.result.append('*')
            elif tag == 'u':
                self.result.append('__')
            elif tag == 'br':
                self.result.append('\n')
            elif tag == 'p':
                if self.result and not self.result[-1].endswith('\n'):
                    self.result.append('\n\n')
            elif tag == 'div':
                if self.result and not self.result[-1].endswith('\n'):
                    self.result.append('\n')
            elif tag == 'ul':
                self.in_list = True
                self.list_type = 'ul'
                self.list_counter = 0
                if self.result and not self.result[-1].endswith('\n'):
                    self.result.append('\n')
            elif tag == 'ol':
                self.in_list = True
                self.list_type = 'ol'
                self.list_counter = 0
                if self.result and not self.result[-1].endswith('\n'):
                    self.result.append('\n')
            elif tag == 'li':
                self.list_counter += 1
                if self.list_type == 'ul':
                    self.result.append('- ')
                else:
                    self.result.append(f'{self.list_counter}. ')
            elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(tag[1])
                self.result.append('\n' + '#' * level + ' ')
            elif tag == 'blockquote':
                self.result.append('\n> ')
            elif tag == 'a':
                attrs_dict = dict(attrs)
                self.result.append('[')
                self.current_link = attrs_dict.get('href', '')
                
        def handle_endtag(self, tag):
            if tag in ['b', 'strong']:
                self.result.append('**')
            elif tag in ['i', 'em']:
                self.result.append('*')
            elif tag == 'u':
                self.result.append('__')
            elif tag in ['p', 'div']:
                if self.result and not self.result[-1].endswith('\n'):
                    self.result.append('\n')
            elif tag in ['ul', 'ol']:
                self.in_list = False
                self.list_type = None
                self.result.append('\n')
            elif tag == 'li':
                if self.result and not self.result[-1].endswith('\n'):
                    self.result.append('\n')
            elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                self.result.append('\n')
            elif tag == 'blockquote':
                self.result.append('\n')
            elif tag == 'a':
                self.result.append(f']({self.current_link})')
                
        def handle_data(self, data):
            # 清理多余的空白字符，但保留换行
            cleaned_data = data.strip()
            if cleaned_data:
                self.result.append(cleaned_data)
                
        def get_markdown(self):
            return ''.join(self.result).strip()
    
    try:
        parser = HTMLToMarkdown()
        parser.feed(html_content)
        markdown = parser.get_markdown()
        
        # 清理多余的空行
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        return markdown
    except Exception as e:
        print(f"HTML转Markdown失败: {str(e)}")
        # 如果转换失败，返回清理后的纯文本
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', html_content)
        # 清理多余的空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

# 雪球发帖函数
def publish_discussion_to_xueqiu(content, cookie):
    """发布讨论到雪球"""
    import requests
    
    # 雪球接收HTML格式，不需要转换
    print("准备发布HTML格式内容...")
    print(f"内容前200字符: {content[:200]}")
    
    # 创建会话
    session = requests.Session()
    
    headers = {
        "Cookie": cookie.strip(),
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    
    # 1. 先访问首页建立会话
    print("访问雪球首页建立会话...")
    home_response = session.get("https://xueqiu.com/", headers=headers)
    print(f"首页访问状态码: {home_response.status_code}")
    
    # 2. 获取session_token
    print("获取session_token...")
    token_url = "https://xueqiu.com/provider/session/token.json?api_path=%2Fstatuses%2Fupdate.json"
    token_response = session.get(token_url, headers=headers)
    print(f"获取token状态码: {token_response.status_code}")
    
    if token_response.status_code != 200:
        raise Exception(f"获取token失败，状态码: {token_response.status_code}")
    
    token_data = token_response.json()
    if "session_token" not in token_data:
        raise Exception("未获取到session_token")
    
    session_token = token_data["session_token"]
    print(f"获取session_token成功：{session_token[:16]}...")
    
    # 3. 发布讨论
    print("发布讨论...")
    post_url = "https://xueqiu.com/statuses/update.json"
    data = {
        "status": content,
        "device": "Web",
        "right": "0",
        "session_token": session_token
    }
    
    print(f"发布讨论请求数据: {data}")
    response = session.post(post_url, data=data, headers=headers)
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text[:500]}")  # 显示前500个字符
    
    try:
        # 检查响应内容是否为空
        if not response.text:
            print("响应内容为空")
            raise Exception("发布失败: 响应内容为空")
        
        # 检查响应的Content-Type
        content_type = response.headers.get('Content-Type', '')
        print(f"响应Content-Type: {content_type}")
        
        result = response.json()
        print(f"发布讨论响应: {result}")
        
        if 'id' not in result:
            error_msg = result.get('error_description', '发布失败')
            print(f"发布失败原因: {error_msg}")
            raise Exception(error_msg)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
        print(f"完整响应内容: {response.text}")
        # 检查是否返回HTML页面
        if '<html' in response.text.lower():
            print("API返回了HTML页面，可能是Cookie过期或无效")
            raise Exception("发布失败: API返回了HTML页面，可能是Cookie过期或无效")
        raise Exception(f"发布失败: {str(e)}")
    
    return result['id']

def publish_article_to_xueqiu(title, content, is_column, cookie):
    """发布长文到雪球"""
    import requests
    
    # 雪球接收HTML格式，不需要转换
    print("准备发布HTML格式内容...")
    print(f"内容前200字符: {content[:200]}")
    
    # 创建会话
    session = requests.Session()
    
    # 根据是否为专栏文章设置不同的请求头
    if is_column:
        headers = {
            "Cookie": cookie.strip(),
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://xueqiu.com/write",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://xueqiu.com"
        }
    else:
        headers = {
            "Cookie": cookie.strip(),
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
            "Referer": "https://mp.xueqiu.com/write/",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://mp.xueqiu.com"
        }
    
    # 1. 先访问首页建立会话
    print("访问雪球首页建立会话...")
    home_response = session.get("https://xueqiu.com/", headers=headers)
    print(f"首页访问状态码: {home_response.status_code}")
    
    # 2. 获取session_token
    print("获取session_token...")
    token_url = "https://xueqiu.com/provider/session/token.json?api_path=%2Fstatuses%2Fupdate.json"
    token_response = session.get(token_url, headers=headers)
    print(f"获取token状态码: {token_response.status_code}")
    
    if token_response.status_code != 200:
        raise Exception(f"获取token失败，状态码: {token_response.status_code}")
    
    token_data = token_response.json()
    if "session_token" not in token_data:
        raise Exception("未获取到session_token")
    
    session_token = token_data["session_token"]
    print(f"获取session_token成功：{session_token[:16]}...")
    
    # 3. 发布长文
    print("发布长文...")
    
    if is_column:
        # 专栏文章发布
        post_url = "https://xueqiu.com/statuses/update.json"
        data = {
            "title": title,
            "status": content,
            "cover_pic": "",
            "show_cover_pic": "true",
            "original": "true",  # 专栏文章必须声明原创
            "comment_disabled": "false",
            "session_token": session_token,
            "device": "Web",
            "right": "0",
            "draft_id": "0",
            "type": "8",  # 专栏文章类型
            "is_column": "true",
            "column": "true",
            "article_type": "1"  # 1: 个人文章
        }
    else:
        # 普通长文发表
        post_url = "https://mp.xueqiu.com/xq/statuses/update.json"
        data = {
            "title": title,
            "status": content,
            "cover_pic": "",
            "show_cover_pic": "true",
            "original": "false",
            "comment_disabled": "false",
            "session_token": session_token,
            "device": "Web",
            "right": "0",
            "draft_id": "0",
            "type": "1"  # 普通文章类型为1
        }
    
    print(f"发布长文请求数据: {data}")
    print(f"发布URL: {post_url}")
    response = session.post(post_url, data=data, headers=headers)
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text[:500]}")  # 显示前500个字符
    
    try:
        # 检查响应内容是否为空
        if not response.text:
            print("响应内容为空")
            raise Exception("发布失败: 响应内容为空")
        
        # 检查响应的Content-Type
        content_type = response.headers.get('Content-Type', '')
        print(f"响应Content-Type: {content_type}")
        
        result = response.json()
        print(f"发布长文响应: {result}")
        
        if 'id' not in result:
            error_msg = result.get('error_description', '发布失败')
            print(f"发布失败原因: {error_msg}")
            raise Exception(error_msg)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
        print(f"完整响应内容: {response.text}")
        # 检查是否返回HTML页面
        if '<html' in response.text.lower():
            print("API返回了HTML页面，可能是Cookie过期或无效")
            raise Exception("发布失败: API返回了HTML页面，可能是Cookie过期或无效")
        raise Exception(f"发布失败: {str(e)}")
    
    return result['id']

# 人设配置管理
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSONAS_FILE = os.path.join(BASE_DIR, 'config', 'personas.json')

# 预制人设信息
DEFAULT_PERSONAS = [
    {
        "id": "1",
        "name": "价值投资布道者",
        "tags": ["长期主义灯塔", "财报导师", "慢富践行者"],
        "coreClaims": "买企业不买股票、安全边际、长期持有、复利至上、远离短期噪音",
        "contentFeatures": "体系化框架（选股九把刀、五维投资闭环）、财报拆解、风险纪律、著作输出（如《慢慢变富》）",
        "targetAudience": "希望夯实底层逻辑、拒绝追热点的长期投资者",
        "promptPoints": "角色：雪球资深价值投资者，20 年 + A 股牛熊穿越，信奉巴菲特理念，实盘业绩稳健。风格：沉稳理性、逻辑严谨、语言朴实，不炫技、不焦虑，强调 '纪律与时间'。输出：长文拆解企业基本面、估值逻辑、风控准则；回答散户常见困惑（何时买、如何拿、何时卖）。禁忌：不做短线推荐、不煽动投机情绪、不夸大短期收益。",
        "icon": "book"
    },
    {
        "id": "2",
        "name": "行业深度研究专家",
        "tags": ["行业活字典", "赛道研究员", "企业基本面猎手"],
        "coreClaims": "深耕单一赛道、产业格局研判、企业竞争壁垒分析、业绩兑现跟踪",
        "contentFeatures": "覆盖 AI / 光通信 / 医药 / 银行等细分领域，定期更新跟踪报告，数据详实、逻辑闭环",
        "targetAudience": "专注赛道投资、需深度产业信息的进阶投资者",
        "promptPoints": "角色：某赛道（如光通信、AI 算力、医药创新）10 年 + 深耕者，熟悉产业链上下游、技术路线、竞争格局。风格：专业严谨、数据驱动、观点犀利，用图表与案例支撑分析。输出：行业全景报告、企业深度研报、技术迭代解读、政策影响分析。亮点：标注核心逻辑、风险点、关键催化剂，提供可执行的投资线索。",
        "icon": "graduation-cap"
    },
    {
        "id": "3",
        "name": "宏观策略实战派",
        "tags": ["全局视野者", "周期捕手", "资产配置顾问"],
        "coreClaims": "宏观驱动 + 行业研判、估值 + 业绩双锚、跨资产配置、把握周期拐点",
        "contentFeatures": "结合地缘政治、货币政策、产业趋势，覆盖 A 股 / 美股 / 大宗商品，强调策略落地",
        "targetAudience": "需全局视角、希望跨市场配置的投资者",
        "promptPoints": "角色：兼具宏观视野与实战经验，擅长从全球格局推导国内市场与行业机会，实盘多资产配置。风格：宏大叙事、逻辑连贯、务实可执行，不空谈宏观，链接微观标的。输出：宏观周报、行业轮动策略、资产配置建议、市场情绪与拐点判断。亮点：用 '估值 + 业绩' 验证逻辑，给出仓位与标的选择的具体参考。",
        "icon": "globe"
    },
    {
        "id": "4",
        "name": "低风险套利专家",
        "tags": ["套利高手", "低波动践行者", "现金流管家"],
        "coreClaims": "零贝塔策略、无风险套利、小赚积累、极致风控",
        "contentFeatures": "聚焦可转债、ETF、打新、股息套利，年化收益稳定、回撤极低",
        "targetAudience": "风险厌恶、追求稳定现金流、上班族投资者",
        "promptPoints": "角色：低风险策略专家，精通套利逻辑，实盘长期稳定收益，强调 '安全第一'。风格：温和耐心、步骤清晰、可复制性强，语言通俗、避免复杂术语。输出：套利策略拆解、实操步骤、阈值设置指南、风险提示清单。亮点：提供具体场景（如可转债溢价率阈值、ETF 套利时机）的执行方案。",
        "icon": "shield"
    },
    {
        "id": "5",
        "name": "量化投资专家",
        "tags": ["量化模型构建者", "数据分析师", "策略回测专家"],
        "coreClaims": "数据驱动、模型回测、纪律交易、拒绝主观臆断",
        "contentFeatures": "分享量化策略、模型代码、回测结果、因子研究，覆盖 A 股 / 港股 / 美股",
        "targetAudience": "技术背景、希望用数据做投资的进阶投资者",
        "promptPoints": "角色：量化投资实战派，熟悉 Python、回测框架、因子库，实盘量化策略长期有效。风格：专业严谨、逻辑清晰、技术导向，兼顾策略逻辑与代码实现。输出：策略教程、模型搭建指南、回测报告、因子有效性分析。亮点：兼顾 '是什么' 与 '怎么做'，提供可落地的策略与代码片段。",
        "icon": "line-chart"
    },
    {
        "id": "6",
        "name": "亲民新手导师",
        "tags": ["投资启蒙人", "基金定投专家", "新手陪跑官"],
        "coreClaims": "简单易懂、新手友好、定投致富、拒绝复杂套路",
        "contentFeatures": "基金定投、指数基金、基础理财知识，内容通俗、互动性强",
        "targetAudience": "投资新手、理财小白、上班族",
        "promptPoints": "角色：专为新手设计的投资导师，擅长将复杂知识转化为通俗语言，帮助新手建立正确理财观。风格：亲切温暖、耐心细致、鼓励为主，语言活泼、避免专业壁垒。输出：定投指南、理财入门课、新手常见问题解答、基金选择技巧。亮点：强调 '长期坚持' 与 '简单有效'，降低新手投资门槛。",
        "icon": "user-circle"
    },
    {
        "id": "7",
        "name": "老股民叙事派",
        "tags": ["故事型老股民", "实战过来人", "情绪共情者"],
        "coreClaims": "投资即修行、情绪管理、周期感悟、接地气实战",
        "contentFeatures": "用故事 / 比喻讲投资（如 '当孩子养、当猪卖'），共情散户焦虑，高频输出",
        "targetAudience": "有投资经历、希望获得情绪共鸣的散户",
        "promptPoints": "角色：穿越多轮牛熊的老股民，擅长用生活化故事传递投资逻辑，接地气、敢说真话。风格：幽默接地气、情感充沛、观点鲜明，擅长抓市场情绪痛点。输出：投资故事、情绪管理指南、周期感悟、散户避坑建议。亮点：用故事降低理解门槛，引发评论区互动，传递 '真实、可感' 的投资体验。",
        "icon": "user-secret"
    },
    {
        "id": "8",
        "name": "雪球创始人",
        "tags": ["理性投资代言人", "陪聊官", "有限理性践行者"],
        "coreClaims": "承认有限理性、资产配置、理性讨论、尊重市场",
        "contentFeatures": "高频回答各类投资与非投资问题，强调 '启发而非答案'，社区氛围包容",
        "targetAudience": "希望理性交流、尊重多元观点的投资者",
        "promptPoints": "角色：雪球创始人，理性投资倡导者，资产配置专家，谦逊、包容、乐于分享。风格：客观中立、逻辑清晰、语言平实，不绝对化、不权威主义。输出：投资问答、资产配置建议、社区理念分享、投资心态探讨。亮点：强调 '启发' 而非 '指导'，鼓励多元观点碰撞。",
        "icon": "user"
    },
    {
        "id": "9",
        "name": "全球资产配置专家",
        "tags": ["全球投资顾问", "跨市场猎手", "国际趋势分析师"],
        "coreClaims": "全球分散、把握国际趋势、跨市场机会、对冲风险",
        "contentFeatures": "覆盖美股、港股、海外资产，解读美联储政策、全球地缘、国际产业格局",
        "targetAudience": "希望参与全球市场、分散风险的投资者",
        "promptPoints": "角色：熟悉全球资本市场，擅长挖掘国际市场机会，提供跨资产配置方案。风格：专业权威、视野开阔、逻辑严谨，兼顾全球趋势与国内落地。输出：全球市场周报、海外资产分析、国际政策影响解读、跨市场配置建议。亮点：结合地缘政治与产业变革，给出具体的全球投资线索。",
        "icon": "globe"
    },
    {
        "id": "10",
        "name": "医药/消费赛道深耕者",
        "tags": ["医药消费专家", "消费龙头猎手", "赛道价值践行者"],
        "coreClaims": "买垄断、买成瘾、买消费龙头、长期持有、业绩为王",
        "contentFeatures": "深耕医药、消费行业，分析企业壁垒、产品竞争力、业绩兑现能力",
        "targetAudience": "专注医药消费赛道、希望挖掘龙头企业的投资者",
        "promptPoints": "角色：医药 / 消费赛道 10 年 + 深耕者，熟悉行业政策、企业格局、产品动态。风格：专业深入、观点独到、数据支撑，聚焦企业核心竞争力与长期价值。输出：行业深度报告、企业基本面分析、政策影响解读、龙头标的跟踪。亮点：强调 '壁垒' 与 '成长'，给出赛道内的核心投资逻辑。",
        "icon": "briefcase"
    }
]

# 加载人设配置
def load_personas():
    """加载人设配置"""
    if os.path.exists(PERSONAS_FILE):
        try:
            with open(PERSONAS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载人设配置失败: {str(e)}")
            # 如果加载失败，返回默认人设
            return DEFAULT_PERSONAS
    else:
        # 如果文件不存在，创建默认人设文件
        save_personas(DEFAULT_PERSONAS)
        return DEFAULT_PERSONAS

# 保存人设配置
def save_personas(personas):
    """保存人设配置"""
    try:
        with open(PERSONAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(personas, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存人设配置失败: {str(e)}")
        return False

# 获取人设列表
@app.route('/api/get-personas', methods=['GET'])
def get_personas():
    """获取人设列表"""
    try:
        personas = load_personas()
        return jsonify({
            "success": True,
            "data": personas
        })
    except Exception as e:
        print(f"获取人设列表失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"获取人设列表失败: {str(e)}"
        }), 500

# 保存单个人设
@app.route('/api/save-persona', methods=['POST'])
def save_persona():
    """保存单个人设"""
    try:
        data = request.json
        personas = load_personas()
        
        # 检查是否是更新现有人设
        existing_index = None
        for i, persona in enumerate(personas):
            if persona['id'] == data['id']:
                existing_index = i
                break
        
        if existing_index is not None:
            # 更新现有人设
            personas[existing_index] = data
        else:
            # 添加新人设
            personas.append(data)
        
        if save_personas(personas):
            return jsonify({
                "success": True,
                "message": "人设保存成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": "保存人设失败"
            }), 500
    except Exception as e:
        print(f"保存人设失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"保存人设失败: {str(e)}"
        }), 500

# 删除人设
@app.route('/api/delete-persona', methods=['POST'])
def delete_persona():
    """删除人设"""
    try:
        data = request.json
        persona_id = data.get('id')
        
        if not persona_id:
            return jsonify({
                "success": False,
                "message": "缺少人设ID"
            }), 400
        
        personas = load_personas()
        # 过滤掉要删除的人设
        updated_personas = [p for p in personas if p['id'] != persona_id]
        
        if len(updated_personas) == len(personas):
            return jsonify({
                "success": False,
                "message": "人设不存在"
            }), 404
        
        if save_personas(updated_personas):
            return jsonify({
                "success": True,
                "message": "人设删除成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": "删除人设失败"
            }), 500
    except Exception as e:
        print(f"删除人设失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"删除人设失败: {str(e)}"
        }), 500

# 保存所有人设
@app.route('/api/save-personas', methods=['POST'])
def save_personas_api():
    """保存所有人设"""
    try:
        data = request.json
        personas = data.get('personas', [])
        
        if save_personas(personas):
            return jsonify({
                "success": True,
                "message": "人设配置保存成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": "保存人设配置失败"
            }), 500
    except Exception as e:
        print(f"保存人设配置失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"保存人设配置失败: {str(e)}"
        }), 500

# 系统提示词配置
SYSTEM_PROMPTS_FILE = os.path.join(os.path.dirname(__file__), 'config', 'system_prompts.json')

def load_system_prompts():
    """加载系统提示词配置"""
    try:
        if os.path.exists(SYSTEM_PROMPTS_FILE):
            with open(SYSTEM_PROMPTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"加载系统提示词配置失败: {str(e)}")
        return []

def save_system_prompts(prompts):
    """保存系统提示词配置"""
    try:
        with open(SYSTEM_PROMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存系统提示词配置失败: {str(e)}")
        return False

# 获取系统提示词列表
@app.route('/api/system-prompts', methods=['GET'])
def get_system_prompts():
    """获取系统提示词列表"""
    try:
        prompts = load_system_prompts()
        return jsonify({
            "success": True,
            "data": prompts
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"加载系统提示词失败: {str(e)}"
        }), 500

# 保存系统提示词配置
@app.route('/api/save-system-prompts', methods=['POST'])
def save_system_prompts_api():
    """保存系统提示词配置"""
    try:
        data = request.json
        prompts = data.get('prompts', [])
        
        if save_system_prompts(prompts):
            return jsonify({
                "success": True,
                "message": "系统提示词配置保存成功"
            })
        else:
            return jsonify({
                "success": False,
                "message": "保存系统提示词配置失败"
            }), 500
    except Exception as e:
        print(f"保存系统提示词配置失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"保存系统提示词配置失败: {str(e)}"
        }), 500

@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    """为文章生成配图"""
    try:
        import requests
        import base64
        import os
        
        data = request.json
        content = data.get('content', '')
        title = data.get('title', '')
        selected_model = data.get('selectedModel', 'ark')
        models = data.get('models', {})
        
        if not content and not title:
            return jsonify({
                "success": False,
                "message": "文章内容或标题不能为空"
            }), 400
        
        # 生成图片提示词
        image_prompt = f"为雪球网投资分析文章生成一张专业的配图，文章主题：{title or '投资分析'}\n\n文章内容摘要：{content[:300]}...\n\n要求：\n1. 专业、简洁、有投资分析的感觉\n2. 包含相关的金融/投资元素\n3. 风格统一，适合在雪球网发布\n4. 高清、美观，适合作为文章配图"
        
        print(f"[{time.strftime('%H:%M:%S')}] 正在生成文章配图...")
        
        # 根据不同模型生成图片
        image_url = None
        
        if selected_model == 'ark':
            # 火山引擎目前没有专门的图片生成API
            return jsonify({
                "success": False,
                "message": "火山引擎暂不支持图片生成功能，请选择OpenAI模型"
            }), 400
                
        elif selected_model == 'openai':
            # 调用OpenAI DALL-E API
            api_key = models.get('openai', {}).get('apiKey')
            base_url = models.get('openai', {}).get('baseUrl', 'https://api.openai.com/v1')
            if not api_key:
                return jsonify({
                    "success": False,
                    "message": "缺少OpenAI API Key"
                }), 400
            
            url = f"{base_url}/images/generations"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            payload = {
                "prompt": image_prompt,
                "n": 1,
                "size": "1024x768"
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            result = response.json()
            
            print(f"[{time.strftime('%H:%M:%S')}] OpenAI API响应: {result}")
            
            if 'data' in result and len(result['data']) > 0:
                image_url = result['data'][0]['url']
            else:
                print(f"[{time.strftime('%H:%M:%S')}] OpenAI API返回格式异常: {result}")
                return jsonify({
                    "success": False,
                    "message": f"OpenAI API返回格式异常: {result}"
                }), 400
                
        elif selected_model == 'gemini':
            # 调用Google Gemini API生成图片
            api_key = models.get('gemini', {}).get('apiKey')
            if not api_key:
                return jsonify({
                    "success": False,
                    "message": "缺少Google Gemini API Key"
                }), 400
            
            # 使用Gemini 2.5 Flash模型
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "contents": [{
                    "parts": [{
                        "text": image_prompt
                    }]
                }],
                "generationConfig": {
                    "responseMimeType": "image/png",
                    "aspectRatio": "16:9",
                    "quality": "high"
                }
            }
            
            # 添加API密钥到URL
            url_with_key = f"{url}?key={api_key}"
            
            response = requests.post(url_with_key, headers=headers, json=payload, timeout=60)
            result = response.json()
            
            print(f"[{time.strftime('%H:%M:%S')}] Gemini API响应: {result}")
            
            if response.status_code == 200 and 'candidates' in result:
                # 处理响应
                for candidate in result['candidates']:
                    if 'content' in candidate and 'parts' in candidate['content']:
                        for part in candidate['content']['parts']:
                            if 'inlineData' in part and 'data' in part['inlineData']:
                                # 获取base64编码的图片数据
                                base64_data = part['inlineData']['data']
                                
                                # 确保static目录存在（在项目根目录下）
                                static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
                                if not os.path.exists(static_dir):
                                    os.makedirs(static_dir)
                                
                                # 生成文件名
                                import uuid
                                filename = f"gemini_image_{uuid.uuid4()}.png"
                                filepath = os.path.join(static_dir, filename)
                                
                                # 解码并保存图片
                                with open(filepath, 'wb') as f:
                                    f.write(base64.b64decode(base64_data))
                                
                                # 生成图片URL
                                image_url = f"/static/{filename}"
                                break
                        if image_url:
                            break
            
            if not image_url:
                print(f"[{time.strftime('%H:%M:%S')}] Gemini API返回格式异常: {result}")
                return jsonify({
                    "success": False,
                    "message": f"Gemini API返回格式异常: {result}"
                }), 400
        
        if image_url:
            print(f"[{time.strftime('%H:%M:%S')}] 配图生成成功: {image_url}")
            return jsonify({
                "success": True,
                "imageUrl": image_url
            })
        else:
            return jsonify({
                "success": False,
                "message": "配图生成失败"
            })
            
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 生成配图失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"生成配图失败: {str(e)}"
        }), 500

@app.route('/api/get-user-articles', methods=['POST'])
def get_user_articles():
    """获取指定用户的文章列表"""
    try:
        data = request.get_json()
        uid = data.get('uid')
        count = data.get('count', 30)
        
        print(f"[{time.strftime('%H:%M:%S')}] 开始获取用户文章，UID: {uid}, 数量: {count}")
        
        if not uid:
            return jsonify({"success": False, "message": "缺少用户UID"}), 400
        
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        if not default_user_id:
            return jsonify({"success": False, "message": "没有设置默认用户"}), 400
        
        default_user = next((u for u in users_data.get("users", []) if u.get("id") == default_user_id), None)
        if not default_user or not default_user.get("cookie"):
            return jsonify({"success": False, "message": "默认用户未配置Cookie"}), 400
        
        print(f"[{time.strftime('%H:%M:%S')}] 使用默认用户: {default_user.get('nickname')} 的Cookie")
        
        xueqiu_cookie = default_user.get("cookie")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://xueqiu.com/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": xueqiu_cookie
        }
        
        session = requests.Session()
        print(f"[{time.strftime('%H:%M:%S')}] 正在访问雪球首页建立会话...")
        session.get("https://xueqiu.com/", headers=headers)
        
        all_articles = []
        page = 1
        page_size = 20
        
        while len(all_articles) < count:
            api_url = f"https://xueqiu.com/statuses/user_timeline.json?user_id={uid}&page={page}&type=edit"
            if page == 1:
                print(f"[{time.strftime('%H:%M:%S')}] 正在请求用户文章列表API (第{page}页)...")
            response = session.get(api_url, headers=headers)
            
            if response.status_code != 200:
                print(f"[{time.strftime('%H:%M:%S')}] API请求失败，状态码: {response.status_code}")
                break
            
            data = response.json()
            articles = data.get("statuses", [])
            
            if not articles:
                break
                
            all_articles.extend(articles)
            print(f"[{time.strftime('%H:%M:%S')}] 第{page}页获取到 {len(articles)} 篇文章，累计 {len(all_articles)} 篇")
            
            if len(articles) < page_size:
                break
                
            page += 1
            time.sleep(0.3)
        
        articles = all_articles[:count]
        print(f"[{time.strftime('%H:%M:%S')}] 最终获取到 {len(articles)} 篇文章")
        
        result = []
        for art in articles:
            created_at = art.get("created_at")
            created_time = ""
            if created_at:
                from datetime import datetime
                created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            
            content = art.get("text", "") or art.get("description", "")
            
            offer = art.get("offer")
            reward_info = {"type": "none", "amount": 0}
            if offer and isinstance(offer, dict):
                reward_info = {
                    "type": "offer",
                    "amount": round(offer.get("amount", 0) / 100, 2),
                    "state": offer.get("state", "")
                }
            elif art.get("can_reward", False):
                reward_info = {
                    "type": "reward",
                    "amount": round(art.get("reward_amount", 0) / 100, 2),
                    "count": art.get("reward_count", 0)
                }
            
            result.append({
                "id": art.get("id"),
                "title": art.get("title") or "无标题",
                "content": content[:500] + "..." if len(content) > 500 else content,
                "fullContent": content,
                "like_count": art.get("like_count", 0),
                "reply_count": art.get("reply_count", 0),
                "retweet_count": art.get("retweet_count", 0),
                "view_count": art.get("view_count", 0),
                "fav_count": art.get("fav_count", 0),
                "is_column": art.get("is_column", False),
                "created_at": created_time,
                "reward": reward_info
            })
        
        print(f"[{time.strftime('%H:%M:%S')}] 成功返回 {len(result)} 篇文章数据")
        return jsonify({"success": True, "articles": result, "count": len(result)})
        
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 获取用户文章失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/get-user-column-articles', methods=['POST'])
def get_user_column_articles():
    """获取指定用户的专栏文章列表"""
    try:
        data = request.get_json()
        uid = data.get('uid')
        count = data.get('count', 30)
        
        print(f"[{time.strftime('%H:%M:%S')}] 开始获取用户专栏文章，UID: {uid}, 数量: {count}")
        
        if not uid:
            return jsonify({"success": False, "message": "缺少用户UID"}), 400
        
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        if not default_user_id:
            return jsonify({"success": False, "message": "没有设置默认用户"}), 400
        
        default_user = next((u for u in users_data.get("users", []) if u.get("id") == default_user_id), None)
        if not default_user or not default_user.get("cookie"):
            return jsonify({"success": False, "message": "默认用户未配置Cookie"}), 400
        
        print(f"[{time.strftime('%H:%M:%S')}] 使用默认用户: {default_user.get('nickname')} 的Cookie")
        
        xueqiu_cookie = default_user.get("cookie")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://xueqiu.com/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": xueqiu_cookie
        }
        
        session = requests.Session()
        print(f"[{time.strftime('%H:%M:%S')}] 正在访问雪球首页建立会话...")
        session.get("https://xueqiu.com/", headers=headers)
        
        all_articles = []
        column_articles = []
        page = 1
        page_size = 20
        max_pages = 50
        
        print(f"[{time.strftime('%H:%M:%S')}] 开始深度搜索专栏文章，目标: {count}篇...")
        
        while page <= max_pages:
            api_url = f"https://xueqiu.com/statuses/user_timeline.json?user_id={uid}&page={page}&type=edit"
            print(f"[{time.strftime('%H:%M:%S')}] 正在请求第{page}页文章...")
            response = session.get(api_url, headers=headers)
            
            if response.status_code != 200:
                print(f"[{time.strftime('%H:%M:%S')}] API请求失败，状态码: {response.status_code}")
                break
            
            data = response.json()
            articles = data.get("statuses", [])
            
            if not articles:
                print(f"[{time.strftime('%H:%M:%S')}] 第{page}页没有更多文章了")
                break
                
            all_articles.extend(articles)
            
            found_this_page = 0
            for art in articles:
                if art.get("is_column", False):
                    column_articles.append(art)
                    found_this_page += 1
            
            print(f"[{time.strftime('%H:%M:%S')}] 第{page}页获取 {len(articles)} 篇文章，找到 {found_this_page} 篇专栏文章，累计 {len(column_articles)} 篇专栏")
            
            if len(column_articles) >= count:
                print(f"[{time.strftime('%H:%M:%S')}] 已找到足够的 {len(column_articles)} 篇专栏文章，停止搜索")
                break
                
            if len(articles) < page_size:
                print(f"[{time.strftime('%H:%M:%S')}] 第{page}页文章数量不足 {page_size} 篇，已到最后一页")
                break
                
            page += 1
            time.sleep(0.3)
        
        print(f"[{time.strftime('%H:%M:%S')}] 搜索结束，共获取 {len(all_articles)} 篇文章，筛选出 {len(column_articles)} 篇专栏文章")
        
        column_articles = column_articles[:count]
        print(f"[{time.strftime('%H:%M:%S')}] 最终使用 {len(column_articles)} 篇专栏文章")
        
        result = []
        for art in column_articles:
            created_at = art.get("created_at")
            created_time = ""
            if created_at:
                from datetime import datetime
                created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            
            content = art.get("text", "") or art.get("description", "")
            
            offer = art.get("offer")
            reward_info = {"type": "none", "amount": 0}
            if offer and isinstance(offer, dict):
                reward_info = {
                    "type": "offer",
                    "amount": round(offer.get("amount", 0) / 100, 2),
                    "state": offer.get("state", "")
                }
            elif art.get("can_reward", False):
                reward_info = {
                    "type": "reward",
                    "amount": round(art.get("reward_amount", 0) / 100, 2),
                    "count": art.get("reward_count", 0)
                }
            
            result.append({
                "id": art.get("id"),
                "title": art.get("title") or "无标题",
                "content": content[:500] + "..." if len(content) > 500 else content,
                "fullContent": content,
                "like_count": art.get("like_count", 0),
                "reply_count": art.get("reply_count", 0),
                "retweet_count": art.get("retweet_count", 0),
                "view_count": art.get("view_count", 0),
                "fav_count": art.get("fav_count", 0),
                "is_column": True,
                "created_at": created_time,
                "reward": reward_info
            })
        
        print(f"[{time.strftime('%H:%M:%S')}] 成功返回 {len(result)} 篇专栏文章数据")
        return jsonify({"success": True, "articles": result, "count": len(result)})
        
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 获取用户专栏文章失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/analyze-user-articles', methods=['POST'])
def analyze_user_articles():
    """使用AI分析用户文章"""
    try:
        from model_adapter import call_model
        
        data = request.get_json()
        articles = data.get('articles', [])
        
        print(f"[{time.strftime('%H:%M:%S')}] 开始分析 {len(articles)} 篇文章")
        
        if not articles:
            return jsonify({"success": False, "message": "没有文章数据"}), 400
        
        config_file = os.path.join(os.path.dirname(__file__), 'config', 'defaultConfig.json')
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        selected_model = config_data.get('selectedModel', 'gemini')
        models_config = config_data.get('models', {})
        print(f"[{time.strftime('%H:%M:%S')}] 使用模型: {selected_model} 进行分析")
        print(f"[{time.strftime('%H:%M:%S')}] 模型配置: {models_config.get(selected_model, {})}")
        
        articles_text_list = []
        for i, art in enumerate(articles, 1):
            content_preview = (art.get('fullContent') or art.get('content') or '')[:300]
            articles_text_list.append(f"""【文章{i}】
标题：{art.get('title', '无标题')}
发布时间：{art.get('created_at', '未知')}
互动数据：点赞 {art.get('like_count', 0)} | 评论 {art.get('reply_count', 0)} | 转发 {art.get('retweet_count', 0)} | 阅读 {art.get('view_count', 0)} | 收藏 {art.get('fav_count', 0)}
内容摘要：
{content_preview}""")
        
        articles_full_text = "\n\n".join(articles_text_list)
        
        prompt = f"""你是一位资深的社交媒体内容分析师和投资领域专家。请对以下雪球用户的{len(articles)}篇文章进行深度专业分析，输出一份有价值的分析报告。

## 分析要求

请从以下6个维度进行系统性分析，每个维度都要给出具体的数据支撑和洞察：

### 一、内容主题与领域画像
- 用户主要关注哪些行业/板块/话题？
- 内容覆盖的广度和深度如何？
- 是否有明显的投资偏好或风格倾向？
- 关键词和热词提取

### 二、内容创作特征分析
- 写作风格（专业/通俗/幽默/严肃）
- 文章结构特点（长文/短帖/图文比例）
- 发布频率和时间规律
- 原创性与信息来源分析

### 三、互动表现深度评估
- 平均点赞率、评论率、阅读量分析
- 高互动文章的共同特征是什么？
- 低互动文章可能存在的问题
- 与同级别创作者的对比评估

### 四、内容质量专业评审
- 信息准确性和专业性评分
- 观点独到性和深度评价
- 可读性和传播性分析
- 内容价值和参考意义

### 五、受众群体画像推断
- 从评论和互动推测目标受众
- 受众关注点和痛点分析
- 粉丝粘性和活跃度评估

### 六、 actionable 改进建议（最重要）
- 具体可操作的内容优化建议（至少5条）
- 标题优化建议（举例说明）
- 互动提升策略
- 个人品牌建设建议
- 变现潜力评估和建议

## 待分析的文章数据

{articles_full_text}

## 输出格式要求

请用中文输出，格式如下：

# 📊 用户文章深度分析报告

## 一、内容主题与领域画像
[详细分析...]

## 二、内容创作特征分析
[详细分析...]

...（其他维度）

## 六、Actionable 改进建议
[具体建议，每条建议都要有可操作性]

---
**报告生成时间**：自动填充
**分析文章数量**：{len(articles)}篇"""

        print(f"[{time.strftime('%H:%M:%S')}] 正在调用模型进行分析...")
        analysis, _ = call_model(
            selected_model,
            models_config.get(selected_model, {}).get('apiKey'),
            prompt,
            'analysis',
            secret_key=models_config.get(selected_model, {}).get('secretKey'),
            base_url=models_config.get(selected_model, {}).get('baseUrl'),
            model_name=models_config.get(selected_model, {}).get('modelName'),
            max_tokens=models_config.get(selected_model, {}).get('maxTokens'),
            temperature=models_config.get(selected_model, {}).get('temperature'),
            operation_type='分析用户文章',
            default_prompt=prompt
        )
        
        print(f"[{time.strftime('%H:%M:%S')}] 分析完成，结果长度: {len(analysis)} 字符")
        analysis = text_to_html(analysis)
        print(f"[{time.strftime('%H:%M:%S')}] 已转换为HTML格式")
        return jsonify({"success": True, "analysis": analysis})
            
    except Exception as e:
        import traceback
        print(f"[{time.strftime('%H:%M:%S')}] 分析文章失败: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/get-hot-spots', methods=['GET'])
def get_hot_spots():
    """获取今日雪球热点"""
    import requests
    import json
    import os
    import re
    from datetime import datetime
    from bs4 import BeautifulSoup
    
    print(f"[{time.strftime('%H:%M:%S')}] ========== 获取今日雪球热点 ==========")
    
    try:
        session = requests.Session()
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://xueqiu.com/",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        
        # 先访问雪球首页建立会话
        print(f"[{time.strftime('%H:%M:%S')}] 访问雪球首页建立会话...")
        session.get("https://xueqiu.com/", headers=headers)
        
        # 访问雪球热点页面
        url = "https://xueqiu.com/hot/spot"
        print(f"[{time.strftime('%H:%M:%S')}] 正在请求热点页面: {url}")
        response = session.get(url, headers=headers, timeout=30)
        print(f"[{time.strftime('%H:%M:%S')}] 响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            return jsonify({"success": False, "error": f"请求失败，状态码: {response.status_code}"}), 500
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        hot_spots = []
        
        # 1. 从页面中提取 hashtag 链接
        print(f"[{time.strftime('%H:%M:%S')}] 提取 hashtag 链接...")
        all_links = soup.find_all('a')
        hashtag_links = []
        
        for link in all_links:
            href = link.get('href', '')
            if '/hashtag/' in href:
                hashtag_links.append(href)
        
        print(f"[{time.strftime('%H:%M:%S')}] 找到 {len(hashtag_links)} 个 hashtag 链接")
        
        # 2. 从页面中提取热点信息（标题、股票、涨跌幅、热度值）
        print(f"[{time.strftime('%H:%M:%S')}] 解析热点信息...")
        
        # 查找所有包含"热度值"的元素
        hot_items = []
        
        # 查找所有包含"热度值"的文本
        all_text = response.text
        
        # 模式: 1#标题#股票+涨跌幅 热度值 X万
        pattern = r'(\d+)#([^#]+)#([^#]+?)\s*热度值\s*([\d.]+万?)'
        matches = re.findall(pattern, all_text)
        
        print(f"[{time.strftime('%H:%M:%S')}] 找到 {len(matches)} 条热点记录")
        
        # 3. 处理每条热点
        for i, match in enumerate(matches):
            num, title, stock_part, heat = match
            
            # 解析股票和涨跌幅
            stock_name = ''
            stock_change = ''
            stock_match = re.search(r'(.+?)([+-][\d.]+%)', stock_part)
            if stock_match:
                stock_name = stock_match.group(1)
                stock_change = stock_match.group(2)
            else:
                stock_name = stock_part
            
            # 获取对应的 hashtag 链接
            url = ''
            if i < len(hashtag_links):
                url = f"https://xueqiu.com{hashtag_links[i]}"
            
            # 获取详细内容
            detail_content = ''
            if url:
                try:
                    print(f"[{time.strftime('%H:%M:%S')}] [{i+1}/{len(matches)}] 获取详细内容: {title[:30]}...")
                    detail_response = session.get(url, headers=headers, timeout=30)
                    if detail_response.status_code == 200:
                        detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                        
                        # 提取热点直击内容
                        detail_text = detail_soup.get_text()
                        
                        # 查找"热点直击"后面的内容
                        if '热点直击' in detail_text:
                            idx = detail_text.find('热点直击')
                            # 查找"热门话题"之前的内容
                            end_idx = detail_text.find('热门话题', idx)
                            if end_idx == -1:
                                end_idx = idx + 2000
                            detail_content = detail_text[idx+6:end_idx].strip()
                except Exception as e:
                    print(f"[{time.strftime('%H:%M:%S')}] 获取详细内容失败: {e}")
            
            hot_spots.append({
                "id": int(num),
                "title": title,
                "content": detail_content,
                "description": title,
                "url": url,
                "stock": stock_name,
                "change": stock_change,
                "heat": heat,
                "view_count": 0,
                "like_count": 0,
                "reply_count": 0,
                "retweet_count": 0,
                "created_at": ''
            })
        
        # 如果没有找到数据，使用备用方案
        if not hot_spots:
            print(f"[{time.strftime('%H:%M:%S')}] 使用备用方案...")
            # 遍历每个 hashtag 链接获取内容
            for i, hashtag_href in enumerate(hashtag_links[:10]):
                url = f"https://xueqiu.com{hashtag_href}"
                try:
                    print(f"[{time.strftime('%H:%M:%S')}] [{i+1}/{len(hashtag_links)}] 访问: {url}")
                    detail_response = session.get(url, headers=headers, timeout=30)
                    if detail_response.status_code == 200:
                        detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                        
                        # 从页面标题中提取
                        title = ''
                        if detail_soup.title:
                            title_text = detail_soup.title.string
                            if '#' in title_text:
                                title = title_text.split('#')[1] if len(title_text.split('#')) > 1 else title_text
                        
                        # 提取内容
                        detail_content = ''
                        detail_text = detail_soup.get_text()
                        if '热点直击' in detail_text:
                            idx = detail_text.find('热点直击')
                            end_idx = detail_text.find('热门话题', idx)
                            if end_idx == -1:
                                end_idx = idx + 2000
                            detail_content = detail_text[idx+6:end_idx].strip()
                        
                        # 提取热度值
                        heat = ''
                        heat_match = re.search(r'热度值\s*([\d.]+万?)', detail_text)
                        if heat_match:
                            heat = heat_match.group(1)
                        
                        hot_spots.append({
                            "id": i + 1,
                            "title": title if title else f"热点 {i+1}",
                            "content": detail_content,
                            "description": title if title else '',
                            "url": url,
                            "stock": '',
                            "change": '',
                            "heat": heat,
                            "view_count": 0,
                            "like_count": 0,
                            "reply_count": 0,
                            "retweet_count": 0,
                            "created_at": ''
                        })
                except Exception as e:
                    print(f"[{time.strftime('%H:%M:%S')}] 访问失败: {e}")
                    continue
        
        print(f"[{time.strftime('%H:%M:%S')}] 共获取到 {len(hot_spots)} 条热点")
        
        # 保存到JSON文件
        today = datetime.now().strftime('%Y-%m-%d')
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        filename = os.path.join(data_dir, f'hot_spots_{today}.json')
        
        # 准备保存的数据
        save_data = {
            "date": today,
            "timestamp": time.time(),
            "count": len(hot_spots),
            "hot_spots": hot_spots
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        print(f"[{time.strftime('%H:%M:%S')}] 热点已保存到: {filename}")
        print(f"[{time.strftime('%H:%M:%S')}] ========== 获取热点完成，共 {len(hot_spots)} 条 ==========\n")
        
        return jsonify({
            "success": True,
            "hot_spots": hot_spots,
            "saved_file": filename,
            "count": len(hot_spots)
        })
        
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 获取热点失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

INVESTMENT_NOTES_FILE = os.path.join(BASE_DIR, '..', 'data', 'investment_notes.json')

def load_investment_notes():
    """加载投资笔记"""
    try:
        if os.path.exists(INVESTMENT_NOTES_FILE):
            with open(INVESTMENT_NOTES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"investmentNotes": {}}
    except Exception as e:
        print(f"加载投资笔记失败: {e}")
        return {"investmentNotes": {}}

def save_investment_notes(data):
    """保存投资笔记"""
    try:
        with open(INVESTMENT_NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存投资笔记失败: {e}")
        return False

def get_article_stats(article_id, cookie):
    """获取文章的详细属性和统计数据"""
    try:
        import requests
        import time
        
        session = requests.Session()
        
        print(f"[{time.strftime('%H:%M:%S')}] 正在模拟浏览器流程建立会话...")
        
        # 步骤1：访问首页建立会话
        home_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        if cookie:
            home_headers["Cookie"] = cookie
        
        session.get("https://xueqiu.com/", headers=home_headers, timeout=10)
        time.sleep(0.5)
        
        # 步骤2：访问文章页面
        article_page_headers = home_headers.copy()
        article_page_headers["Referer"] = "https://xueqiu.com/"
        article_page_url = f"https://xueqiu.com/1/{article_id}"
        session.get(article_page_url, headers=article_page_headers, timeout=10)
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
        if cookie:
            api_headers["Cookie"] = cookie
        
        api_url = f"https://xueqiu.com/statuses/show.json?id={article_id}"
        print(f"[{time.strftime('%H:%M:%S')}] 获取文章ID {article_id} 的统计数据，API: {api_url}")
        response = session.get(api_url, headers=api_headers, timeout=10)
        
        print(f"[{time.strftime('%H:%M:%S')}] API响应状态码: {response.status_code}")
        print(f"[{time.strftime('%H:%M:%S')}] API响应内容: {repr(response.text[:500])}")
        
        stats = {
            "viewCount": 0,
            "likeCount": 0,
            "favCount": 0,
            "replyCount": 0,
            "retweetCount": 0,
            "hasReward": False,
            "rewardAmount": 0,
            "rewardCount": 0,
            "rewardExpired": False,
            "rewardRemaining": 0,
            "rewardState": ""
        }
        
        if response.status_code == 200:
            try:
                # 检查是否是JSON响应
                if response.text.strip().startswith('{'):
                    data = response.json()
                    print(f"[{time.strftime('%H:%M:%S')}] API返回数据: {json.dumps(data, ensure_ascii=False)[:800]}")
                    
                    if 'id' in data:
                        status = data
                        
                        stats['viewCount'] = status.get('view_count', 0)
                        stats['likeCount'] = status.get('like_count', 0)
                        stats['favCount'] = status.get('fav_count', 0)
                        stats['replyCount'] = status.get('reply_count', 0)
                        stats['retweetCount'] = status.get('retweet_count', 0)
                        
                        offer = status.get("offer")
                        if offer and isinstance(offer, dict):
                            stats['hasReward'] = True
                            stats['rewardAmount'] = round(offer.get("amount", 0) / 100, 2)
                            stats['rewardRemaining'] = round(offer.get("balance", 0) / 100, 2)
                            stats['rewardState'] = offer.get("state", "")
                            stats['rewardExpired'] = offer.get("state", "") != "NORMAL"
                            stats['rewardCount'] = offer.get("count", 0)
                        elif status.get("reward", False) or status.get("can_reward", False):
                            stats['hasReward'] = True
                            stats['rewardAmount'] = round(status.get("reward_amount", 0) / 100, 2)
                            stats['rewardRemaining'] = stats['rewardAmount']
                            stats['rewardCount'] = status.get("reward_count", 0)
                            stats['rewardExpired'] = False
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 响应不是JSON，可能是HTML")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] JSON解析失败: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"[{time.strftime('%H:%M:%S')}] 返回统计数据: {stats}")
        return stats
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 获取文章统计数据失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "viewCount": 0,
            "likeCount": 0,
            "favCount": 0,
            "replyCount": 0,
            "retweetCount": 0,
            "hasReward": False,
            "rewardAmount": 0,
            "rewardCount": 0,
            "rewardExpired": False,
            "rewardRemaining": 0,
            "rewardState": ""
        }

@app.route('/api/investment-notes/list', methods=['GET'])
def get_investment_notes():
    """获取指定用户的投资笔记列表"""
    try:
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        
        if not default_user_id:
            return jsonify({
                "success": False,
                "message": "请先配置用户并设置默认用户"
            }), 400
        
        notes_data = load_investment_notes()
        user_notes = notes_data.get("investmentNotes", {}).get(default_user_id, [])
        
        user_notes.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        
        return jsonify({
            "success": True,
            "data": user_notes
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取投资笔记列表失败: {str(e)}"
        }), 500

@app.route('/api/investment-notes/stats', methods=['POST'])
def get_note_stats():
    """获取笔记的统计数据（阅读量、收藏量、点赞数）"""
    try:
        data = request.json
        article_id = data.get('articleId')
        
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        
        if not default_user_id:
            return jsonify({
                "success": False,
                "message": "请先配置用户并设置默认用户"
            }), 400
        
        default_user = next((u for u in users_data.get("users", []) if u.get("id") == default_user_id), None)
        if not default_user or not default_user.get("cookie"):
            return jsonify({
                "success": False,
                "message": "默认用户cookie未配置"
            }), 400
        
        cookie = default_user.get("cookie")
        xueqiu_user_id = default_user.get("uid")
        
        print(f"[{time.strftime('%H:%M:%S')}] 用户信息: UUID={default_user_id}, 雪球UID={xueqiu_user_id}")
        
        import requests
        
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://xueqiu.com/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": cookie
        }
        
        print(f"[{time.strftime('%H:%M:%S')}] 正在访问雪球首页建立会话...")
        session.get("https://xueqiu.com/", headers=headers)
        
        stats = {
            "viewCount": 0,
            "likeCount": 0,
            "favCount": 0,
            "replyCount": 0,
            "retweetCount": 0,
            "hasReward": False,
            "rewardAmount": 0,
            "rewardCount": 0,
            "rewardExpired": False
        }
        
        print(f"[{time.strftime('%H:%M:%S')}] 通过用户时间线API查找文章ID {article_id}...")
        
        page = 1
        max_pages = 20
        found = False
        
        while page <= max_pages and not found:
            api_url = f"https://xueqiu.com/statuses/user_timeline.json?user_id={xueqiu_user_id}&page={page}&type=edit"
            print(f"[{time.strftime('%H:%M:%S')}] 请求第{page}页...")
            response = session.get(api_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("statuses", [])
                
                print(f"[{time.strftime('%H:%M:%S')}] 第{page}页获取到 {len(articles)} 篇文章")
                
                if not articles:
                    print(f"[{time.strftime('%H:%M:%S')}] 第{page}页没有文章了，停止搜索")
                    break
                
                for i, art in enumerate(articles):
                    art_id = art.get("id")
                    print(f"[{time.strftime('%H:%M:%S')}]   文章{i+1}: ID={art_id}, title={art.get('title', '无标题')[:30]}")
                    
                    if str(art_id) == str(article_id):
                        print(f"[{time.strftime('%H:%M:%S')}] 找到文章了!")
                        
                        stats['viewCount'] = art.get('view_count', 0)
                        stats['likeCount'] = art.get('like_count', 0)
                        stats['favCount'] = art.get('fav_count', 0)
                        stats['replyCount'] = art.get('reply_count', 0)
                        stats['retweetCount'] = art.get('retweet_count', 0)
                        
                        print(f"[{time.strftime('%H:%M')}] 文章统计: view={stats['viewCount']}, like={stats['likeCount']}, fav={stats['favCount']}, reply={stats['replyCount']}, retweet={stats['retweetCount']}")
                        
                        offer = art.get("offer")
                        if offer and isinstance(offer, dict):
                            stats['hasReward'] = True
                            stats['rewardAmount'] = round(offer.get("amount", 0) / 100, 2)
                            stats['rewardExpired'] = offer.get("state", "") == "expired"
                        elif art.get("reward", False) or art.get("can_reward", False):
                            stats['hasReward'] = True
                            stats['rewardAmount'] = round(art.get("reward_amount", 0) / 100, 2)
                            stats['rewardCount'] = art.get("reward_count", 0)
                            stats['rewardExpired'] = False
                        
                        found = True
                        break
                
                if not found:
                    page += 1
                    time.sleep(0.3)
            else:
                print(f"[{time.strftime('%H:%M:%S')}] API请求失败，状态码: {response.status_code}")
                break
        
        print(f"[{time.strftime('%H:%M:%S')}] 返回统计数据: {stats}")
        return jsonify({
            "success": True,
            "data": stats
        })
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 获取笔记统计数据失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"获取笔记统计数据失败: {str(e)}"
        }), 500

@app.route('/api/investment-notes/save', methods=['POST'])
def save_investment_note():
    """保存投资笔记"""
    try:
        data = request.json
        note = data.get('note')
        
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        
        if not default_user_id:
            return jsonify({
                "success": False,
                "message": "请先配置用户并设置默认用户"
            }), 400
        
        notes_data = load_investment_notes()
        
        if "investmentNotes" not in notes_data:
            notes_data["investmentNotes"] = {}
        
        if default_user_id not in notes_data["investmentNotes"]:
            notes_data["investmentNotes"][default_user_id] = []
        
        note['id'] = note.get('id', str(uuid.uuid4()))
        note['createdAt'] = note.get('createdAt', time.strftime('%Y-%m-%d %H:%M:%S'))
        note['updatedAt'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        existing_notes = notes_data["investmentNotes"][default_user_id]
        
        updated = False
        for i, existing_note in enumerate(existing_notes):
            if existing_note.get('id') == note.get('id'):
                existing_notes[i] = note
                updated = True
                break
        
        if not updated:
            existing_notes.append(note)
        
        if save_investment_notes(notes_data):
            return jsonify({
                "success": True,
                "message": "保存成功",
                "data": note
            })
        else:
            return jsonify({
                "success": False,
                "message": "保存失败"
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"保存投资笔记失败: {str(e)}"
        }), 500

@app.route('/api/investment-notes/generate', methods=['POST'])
def generate_today_note():
    """生成今日投资笔记"""
    try:
        print(f"[{time.strftime('%H:%M:%S')}] ========== 开始生成今日投资笔记 ==========")
        data = request.json
        
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        print(f"[{time.strftime('%H:%M:%S')}] 默认用户ID: {default_user_id}")
        
        if not default_user_id:
            return jsonify({
                "success": False,
                "message": "请先配置用户并设置默认用户"
            }), 400
        
        default_user = next((u for u in users_data.get("users", []) if u.get("id") == default_user_id), None)
        if not default_user or not default_user.get("cookie"):
            return jsonify({
                "success": False,
                "message": "默认用户cookie未配置"
            }), 400
        
        notes_data = load_investment_notes()
        user_notes = notes_data.get("investmentNotes", {}).get(default_user_id, [])
        print(f"[{time.strftime('%H:%M:%S')}] 找到 {len(user_notes)} 篇历史笔记")
        
        from datetime import datetime, timedelta
        
        today = datetime.now()
        five_days_ago = today - timedelta(days=5)
        print(f"[{time.strftime('%H:%M:%S')}] 今天: {today.strftime('%Y-%m-%d')}, 5天前: {five_days_ago.strftime('%Y-%m-%d')}")
        
        recent_notes = []
        for idx, note in enumerate(user_notes):
            try:
                created_at = note.get('createdAt', '')
                print(f"[{time.strftime('%H:%M:%S')}] 处理笔记 {idx+1}: created_at={created_at}")
                
                note_date = None
                # 尝试多种日期格式
                date_formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d %H:%M',
                    '%Y-%m-%d'
                ]
                
                for fmt in date_formats:
                    try:
                        note_date = datetime.strptime(created_at, fmt)
                        print(f"[{time.strftime('%H:%M:%S')}]   成功解析日期: {note_date}, 格式: {fmt}")
                        break
                    except ValueError:
                        continue
                
                if note_date:
                    if note_date >= five_days_ago:
                        recent_notes.append({
                            'id': note.get('id', ''),
                            'title': note.get('title', ''),
                            'content': note.get('content', '')
                        })
                        print(f"[{time.strftime('%H:%M:%S')}]   ✅ 加入最近笔记")
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}]   ❌ 日期太旧，跳过")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}]   ⚠️ 日期解析失败，跳过")
                    
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}]   ❌ 处理笔记异常: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"[{time.strftime('%H:%M:%S')}] 找到 {len(recent_notes)} 篇近5天的笔记")
        
        config = load_config()
        models = config.get('models', {})
        selected_model = config.get('selectedModel', 'ark')
        print(f"[{time.strftime('%H:%M:%S')}] 选择的模型: {selected_model}")
        
        prompts = load_system_prompts()
        default_prompt = next((p for p in prompts if p.get('isDefault')), None)
        system_prompt_content = default_prompt.get('content', '') if default_prompt else ''
        print(f"[{time.strftime('%H:%M:%S')}] 系统提示词长度: {len(system_prompt_content)}")
        
        if len(recent_notes) == 0:
            print(f"[{time.strftime('%H:%M:%S')}] 没有最近笔记，使用默认提示词")
            user_prompt = "请写一篇今日投资笔记，主题围绕当前市场行情和投资思考。"
        else:
            print(f"[{time.strftime('%H:%M:%S')}] 使用最近的 {len(recent_notes)} 篇笔记作为参考")
            user_prompt = f"""请根据以下近5天的历史投资笔记，生成一篇新的今日投资笔记。
            
历史笔记：
{json.dumps(recent_notes, ensure_ascii=False, indent=2)}

请保持与历史笔记一致的风格和语气，生成一篇有深度、有见解的今日投资笔记。"""
        
        full_prompt = f"{system_prompt_content}\n\n{user_prompt}" if system_prompt_content else user_prompt
        print(f"[{time.strftime('%H:%M:%S')}] 完整提示词长度: {len(full_prompt)}")
        
        api_key = models.get(selected_model, {}).get('apiKey')
        secret_key = models.get(selected_model, {}).get('secretKey')
        base_url = models.get(selected_model, {}).get('baseUrl')
        model_name = models.get(selected_model, {}).get('modelName')
        
        print(f"[{time.strftime('%H:%M:%S')}] 正在调用模型生成内容...")
        generated_content, _ = call_model(
            selected_model, 
            api_key, 
            full_prompt, 
            'article',
            secret_key=secret_key,
            base_url=base_url,
            model_name=model_name,
            max_tokens=models.get(selected_model, {}).get('maxTokens'),
            temperature=models.get(selected_model, {}).get('temperature'),
            operation_type='生成今日投资笔记',
            default_prompt=system_prompt_content
        )
        
        print(f"[{time.strftime('%H:%M:%S')}] 模型返回内容长度: {len(generated_content) if generated_content else 0}")
        
        if not generated_content or len(generated_content.strip()) == 0:
            print(f"[{time.strftime('%H:%M:%S')}] 生成内容为空，返回错误")
            return jsonify({
                "success": False,
                "message": "生成内容为空"
            }), 400
        
        import re
        def remove_markdown(text):
            text = re.sub(r'^#+\s', '', text, flags=re.MULTILINE)
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
            text = re.sub(r'\*(.*?)\*', r'\1', text)
            text = re.sub(r'__(.*?)__', r'\1', text)
            text = re.sub(r'_(.*?)_', r'\1', text)
            text = re.sub(r'`(.*?)`', r'\1', text)
            text = re.sub(r'```[\s\S]*?```', '', text)
            text = re.sub(r'^\s*[-*+]\s', '', text, flags=re.MULTILINE)
            text = re.sub(r'^\s*\d+\.\s', '', text, flags=re.MULTILINE)
            text = re.sub(r'^\s*>\s', '', text, flags=re.MULTILINE)
            text = re.sub(r'---+', '', text)
            text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()
        
        cleaned_content = remove_markdown(generated_content)
        
        print(f"[{time.strftime('%H:%M:%S')}] ========== 投资笔记生成成功 ==========")
        print(f"[{time.strftime('%H:%M:%S')}] 清理后内容长度: {len(cleaned_content)}")
        print(f"[{time.strftime('%H:%M:%S')}] 使用历史笔记数量: {len(recent_notes)}")
        
        return jsonify({
            "success": True,
            "data": {
                "content": cleaned_content,
                "title": f"{datetime.now().strftime('%Y年%m月%d日')}投资笔记",
                "recentNotesCount": len(recent_notes)
            }
        })
    except Exception as e:
        print(f"生成今日投资笔记异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"生成今日投资笔记失败: {str(e)}"
        }), 500

# ==================== 话题配置相关API ====================
@app.route('/api/topics', methods=['GET'])
def get_topics():
    """获取话题列表"""
    try:
        topics_file = os.path.join(os.path.dirname(__file__), 'topics.json')
        
        if os.path.exists(topics_file):
            with open(topics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return jsonify({
                "success": True,
                "data": data,
                "message": "获取话题列表成功"
            })
        else:
            return jsonify({
                "success": True,
                "data": {
                    "topics": [],
                    "updatedAt": ""
                },
                "message": "暂无话题数据"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取话题列表失败: {str(e)}"
        }), 500

@app.route('/api/topics', methods=['POST'])
def save_topics():
    """保存话题列表"""
    try:
        data = request.json
        topics = data.get("topics", [])
        
        topics_file = os.path.join(os.path.dirname(__file__), 'topics.json')
        
        topics_data = {
            "topics": topics,
            "updatedAt": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(topics_file, 'w', encoding='utf-8') as f:
            json.dump(topics_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "data": topics_data,
            "message": "保存话题列表成功"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"保存话题列表失败: {str(e)}"
        }), 500

@app.route('/api/topic', methods=['POST'])
def add_topic():
    """添加单个话题"""
    try:
        data = request.json
        topic_name = data.get("name", "").strip()
        topic_description = data.get("description", "").strip()
        
        if not topic_name:
            return jsonify({
                "success": False,
                "message": "话题名称不能为空"
            }), 400
        
        topics_file = os.path.join(os.path.dirname(__file__), 'topics.json')
        
        if os.path.exists(topics_file):
            with open(topics_file, 'r', encoding='utf-8') as f:
                topics_data = json.load(f)
        else:
            topics_data = {
                "topics": [],
                "updatedAt": ""
            }
        
        topic_id = str(uuid.uuid4())
        new_topic = {
            "id": topic_id,
            "name": topic_name,
            "description": topic_description,
            "createdAt": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        topics_data["topics"].append(new_topic)
        topics_data["updatedAt"] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        with open(topics_file, 'w', encoding='utf-8') as f:
            json.dump(topics_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "data": new_topic,
            "message": "添加话题成功"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"添加话题失败: {str(e)}"
        }), 500

@app.route('/api/topic/<topic_id>', methods=['PUT'])
def update_topic(topic_id):
    """更新话题"""
    try:
        data = request.json
        topic_name = data.get("name", "").strip()
        topic_description = data.get("description", "").strip()
        
        if not topic_name:
            return jsonify({
                "success": False,
                "message": "话题名称不能为空"
            }), 400
        
        topics_file = os.path.join(os.path.dirname(__file__), 'topics.json')
        
        if not os.path.exists(topics_file):
            return jsonify({
                "success": False,
                "message": "话题数据文件不存在"
            }), 404
        
        with open(topics_file, 'r', encoding='utf-8') as f:
            topics_data = json.load(f)
        
        topic_found = False
        for topic in topics_data["topics"]:
            if topic.get("id") == topic_id:
                topic["name"] = topic_name
                topic["description"] = topic_description
                topic["updatedAt"] = time.strftime('%Y-%m-%d %H:%M:%S')
                topic_found = True
                break
        
        if not topic_found:
            return jsonify({
                "success": False,
                "message": "未找到该话题"
            }), 404
        
        topics_data["updatedAt"] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        with open(topics_file, 'w', encoding='utf-8') as f:
            json.dump(topics_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "data": topic,
            "message": "更新话题成功"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"更新话题失败: {str(e)}"
        }), 500

@app.route('/api/topic/<topic_id>', methods=['DELETE'])
def delete_topic(topic_id):
    """删除话题"""
    try:
        topics_file = os.path.join(os.path.dirname(__file__), 'topics.json')
        
        if not os.path.exists(topics_file):
            return jsonify({
                "success": False,
                "message": "话题数据文件不存在"
            }), 404
        
        with open(topics_file, 'r', encoding='utf-8') as f:
            topics_data = json.load(f)
        
        original_length = len(topics_data["topics"])
        topics_data["topics"] = [
            topic for topic in topics_data["topics"]
            if topic.get("id") != topic_id
        ]
        
        if len(topics_data["topics"]) == original_length:
            return jsonify({
                "success": False,
                "message": "未找到该话题"
            }), 404
        
        topics_data["updatedAt"] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        with open(topics_file, 'w', encoding='utf-8') as f:
            json.dump(topics_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "message": "删除话题成功"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"删除话题失败: {str(e)}"
        }), 500

def process_topic_comments(article_ids, selected_model, models_config, articles, log_callback, stop_event):
    """处理话题评论任务"""
    try:
        timestamp = time.strftime('%H:%M:%S')
        log_callback({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'[{timestamp}] ========== 话题评论任务开始 ==========',
            'type': 'info'
        })
        
        log_callback({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'[{timestamp}] 配置信息: 文章数量={len(article_ids)}, 模型类型={selected_model}',
            'type': 'info'
        })
        
        # 获取默认用户的cookie和配置
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        users = users_data.get("users", [])
        
        cookie = None
        for user in users:
            if user.get("id") == default_user_id and user.get("cookie"):
                cookie = user.get("cookie")
                break
        
        if not cookie:
            return {'totalArticles': 0, 'successCount': 0, 'failedCount': 0}
        
        # 获取API Key
        api_key = None
        if selected_model == 'ark' and models_config.get('ark'):
            api_key = models_config['ark'].get('apiKey')
        elif selected_model == 'openai' and models_config.get('openai'):
            api_key = models_config['openai'].get('apiKey')
        elif selected_model == 'baidu' and models_config.get('baidu'):
            api_key = models_config['baidu'].get('apiKey')
        elif selected_model == 'alibaba' and models_config.get('alibaba'):
            api_key = models_config['alibaba'].get('apiKey')
        elif selected_model == 'deepseek' and models_config.get('deepseek'):
            api_key = models_config['deepseek'].get('apiKey')
        elif selected_model == 'gemini' and models_config.get('gemini'):
            api_key = models_config['gemini'].get('apiKey')
        elif selected_model == 'claude' and models_config.get('claude'):
            api_key = models_config['claude'].get('apiKey')
        
        if not api_key:
            return {'totalArticles': 0, 'successCount': 0, 'failedCount': 0}
        
        # 加载默认模型提示词
        prompts_file = os.path.join(os.path.dirname(__file__), 'config', 'system_prompts.json')
        default_prompt = "你是一位资深雪球投资者，请针对这篇文章写一段专业、理性、有见解的评论，100-200字。"
        
        if os.path.exists(prompts_file):
            try:
                with open(prompts_file, 'r', encoding='utf-8') as f:
                    prompts = json.load(f)
                    if prompts and len(prompts) > 0:
                        default_prompt = prompts[0].get('prompt', default_prompt)
            except Exception as e:
                print(f"加载提示词失败: {str(e)}")
        
        # 建立文章ID到内容的映射
        article_map = {}
        for art in articles:
            article_map[art.get('id')] = art
        
        # 开始处理评论
        results = []
        success_count = 0
        failed_count = 0
        
        for idx, article_id in enumerate(article_ids):
            if stop_event.is_set():
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{time.strftime("%H:%M:%S")}] 任务已停止',
                    'type': 'info'
                })
                break
            
            try:
                timestamp = time.strftime('%H:%M:%S')
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{timestamp}] ---------- 文章 {idx+1}/{len(article_ids)} ----------',
                    'type': 'info'
                })
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{timestamp}] 正在处理文章ID: {article_id}',
                    'type': 'info'
                })
                
                # 直接使用已获取的文章内容
                article_title = ""
                article_text = ""
                article_info = None
                
                if article_id in article_map:
                    article = article_map[article_id]
                    article_title = article.get('title', '')
                    article_text = article.get('text', '')
                    log_callback({
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'message': f'[{timestamp}] 使用已保存的文章内容: {article_title[:50]}...',
                        'type': 'info'
                    })
                    
                    # 获取文章完整属性并输出日志
                    try:
                        from article_utils import get_article_full_attributes
                        article_info = get_article_full_attributes(article)
                        
                        article_attrs = article_info.get("属性", {})
                        reward_info = article_info.get("打赏/悬赏信息", {})
                        
                        # 记录文章标题
                        log_callback({
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'message': f'[{timestamp}] 文章标题: {article_info.get("标题", "无标题")[:50]}...',
                            'type': 'info'
                        })
                        
                        # 记录所有文章属性作为一行日志，使用鲜艳颜色
                        attrs_str = f"点赞: {article_attrs.get('点赞数', 0)} | 评论: {article_attrs.get('评论数', 0)} | 转发: {article_attrs.get('转发数', 0)} | 阅读: {article_attrs.get('阅读数', 0)} | 收藏: {article_attrs.get('收藏数', 0)} | 专栏: {article_attrs.get('是否专栏', '否')} | 原创: {article_attrs.get('是否原创声明', '否')} | 时间: {article_attrs.get('创建时间', '未知')} | 打赏: {reward_info.get('类型', '无')}"
                        
                        log_callback({
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'message': f'[{timestamp}] 📊 文章属性: {attrs_str}',
                            'type': 'info',
                            'isAttributeLog': True,
                            'articleId': article_id
                        })
                    except Exception as e:
                        log_callback({
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'message': f'[{timestamp}] 获取文章属性失败: {e}',
                            'type': 'warning'
                        })
                
                # 生成评论
                prompt = f"{default_prompt}\n\n文章标题: {article_title}\n文章内容: {article_text[:500]}\n\n评论:"
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{timestamp}] 正在调用模型生成评论...',
                    'type': 'info'
                })
                
                comment_content, _ = call_model(
                    selected_model, 
                    api_key, 
                    prompt, 
                    'comment',
                    secret_key=models_config.get(selected_model, {}).get('secretKey'),
                    base_url=models_config.get(selected_model, {}).get('baseUrl'),
                    model_name=models_config.get(selected_model, {}).get('modelName'),
                    max_tokens=models_config.get(selected_model, {}).get('maxTokens'),
                    temperature=models_config.get(selected_model, {}).get('temperature'),
                    operation_type='话题评论',
                    default_prompt=default_prompt
                )
                
                comment_content = comment_content.strip()
                # 检查返回的内容是否为空
                if not comment_content:
                    log_callback({
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'message': f'[{timestamp}] 模型返回空内容，使用默认评论',
                        'type': 'warning'
                    })
                    comment_content = "分析到位，学习了"
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{timestamp}] 生成的评论内容: {comment_content[:80]}...',
                    'type': 'info'
                })
                
                # 发布评论
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{timestamp}] 正在发布评论到雪球...',
                    'type': 'info'
                })
                comment_result = post_topic_comment(article_id, comment_content, cookie)
                
                if comment_result['success']:
                    success_count += 1
                    results.append({
                        "articleId": article_id,
                        "success": True,
                        "comment": comment_content,
                        "message": comment_result['message']
                    })
                    log_callback({
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'message': f'[{timestamp}] ✅ 文章 {article_id}: 评论成功 - {comment_content}',
                        'type': 'success'
                    })
                else:
                    failed_count += 1
                    results.append({
                        "articleId": article_id,
                        "success": False,
                        "comment": comment_content,
                        "message": comment_result['message']
                    })
                    log_callback({
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'message': f'[{timestamp}] ❌ 文章 {article_id}: 评论失败 - {comment_result["message"]}',
                        'type': 'error'
                    })
                
                if idx < len(article_ids) - 1:
                    time.sleep(2)  # 避免请求过快
                
            except Exception as e:
                failed_count += 1
                results.append({
                    "articleId": article_id,
                    "success": False,
                    "message": f"处理失败: {str(e)}"
                })
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{time.strftime("%H:%M:%S")}] ❌ 处理文章 {article_id} 异常: {str(e)}',
                    'type': 'error'
                })
                import traceback
                traceback.print_exc()
        
        log_callback({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'[{time.strftime("%H:%M:%S")}] ========== 话题评论任务完成 ==========',
            'type': 'info'
        })
        log_callback({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'[{time.strftime("%H:%M:%S")}] 总计: 成功 {success_count} 篇，失败 {failed_count} 篇',
            'type': 'info'
        })
        
        return {
            'totalArticles': len(article_ids),
            'successCount': success_count,
            'failedCount': failed_count,
            'results': results
        }
        
    except Exception as e:
        log_callback({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'话题评论任务异常: {str(e)}',
            'type': 'error'
        })
        import traceback
        traceback.print_exc()
        return {'totalArticles': 0, 'successCount': 0, 'failedCount': 0}

def process_reward_comments(article_ids, selected_model, models_config, articles, log_callback, stop_event):
    """处理悬赏评论任务"""
    try:
        timestamp = time.strftime('%H:%M:%S')
        log_callback({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'[{timestamp}] ========== 悬赏评论任务开始 ==========',
            'type': 'info'
        })
        
        log_callback({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'[{timestamp}] 配置信息: 文章数量={len(article_ids)}, 模型类型={selected_model}',
            'type': 'info'
        })
        
        # 获取默认用户的cookie和配置
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        users = users_data.get("users", [])
        
        cookie = None
        for user in users:
            if user.get("id") == default_user_id and user.get("cookie"):
                cookie = user.get("cookie")
                break
        
        if not cookie:
            return {'totalArticles': 0, 'successCount': 0, 'failedCount': 0}
        
        # 获取API Key
        api_key = None
        if selected_model == 'ark' and models_config.get('ark'):
            api_key = models_config['ark'].get('apiKey')
        elif selected_model == 'openai' and models_config.get('openai'):
            api_key = models_config['openai'].get('apiKey')
        elif selected_model == 'baidu' and models_config.get('baidu'):
            api_key = models_config['baidu'].get('apiKey')
        elif selected_model == 'alibaba' and models_config.get('alibaba'):
            api_key = models_config['alibaba'].get('apiKey')
        elif selected_model == 'deepseek' and models_config.get('deepseek'):
            api_key = models_config['deepseek'].get('apiKey')
        elif selected_model == 'gemini' and models_config.get('gemini'):
            api_key = models_config['gemini'].get('apiKey')
        elif selected_model == 'claude' and models_config.get('claude'):
            api_key = models_config['claude'].get('apiKey')
        
        if not api_key:
            return {'totalArticles': 0, 'successCount': 0, 'failedCount': 0}
        
        # 加载默认模型提示词
        prompts_file = os.path.join(os.path.dirname(__file__), 'config', 'system_prompts.json')
        default_prompt = "你是一位资深雪球投资者，请针对这篇悬赏问答文章写一段专业、理性、有见解的评论，100-200字。"
        
        if os.path.exists(prompts_file):
            try:
                with open(prompts_file, 'r', encoding='utf-8') as f:
                    prompts = json.load(f)
                    if prompts and len(prompts) > 0:
                        default_prompt = prompts[0].get('prompt', default_prompt)
            except Exception as e:
                print(f"加载提示词失败: {str(e)}")
        
        # 建立文章ID到内容的映射
        article_map = {}
        for art in articles:
            article_map[art.get('id')] = art
        
        # 开始处理评论
        results = []
        success_count = 0
        failed_count = 0
        
        for idx, article_id in enumerate(article_ids):
            if stop_event.is_set():
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{time.strftime("%H:%M:%S")}] 任务已停止',
                    'type': 'info'
                })
                break
            
            try:
                timestamp = time.strftime('%H:%M:%S')
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{timestamp}] ---------- 文章 {idx+1}/{len(article_ids)} ----------',
                    'type': 'info'
                })
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{timestamp}] 正在处理文章ID: {article_id}',
                    'type': 'info'
                })
                
                # 直接使用已获取的文章内容
                article_title = ""
                article_text = ""
                article_info = None
                
                if article_id in article_map:
                    article = article_map[article_id]
                    article_title = article.get('title', '')
                    article_text = article.get('text', '')
                    log_callback({
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'message': f'[{timestamp}] 使用已保存的文章内容: {article_title[:50]}...',
                        'type': 'info'
                    })
                    
                    # 获取文章完整属性并输出日志
                    try:
                        from article_utils import get_article_full_attributes
                        article_info = get_article_full_attributes(article)
                        
                        article_attrs = article_info.get("属性", {})
                        reward_info = article_info.get("打赏/悬赏信息", {})
                        
                        # 记录文章标题
                        log_callback({
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'message': f'[{timestamp}] 文章标题: {article_info.get("标题", "无标题")[:50]}...',
                            'type': 'info'
                        })
                        
                        # 记录所有文章属性作为一行日志，使用鲜艳颜色
                        attrs_str = f"点赞: {article_attrs.get('点赞数', 0)} | 评论: {article_attrs.get('评论数', 0)} | 转发: {article_attrs.get('转发数', 0)} | 阅读: {article_attrs.get('阅读数', 0)} | 收藏: {article_attrs.get('收藏数', 0)} | 专栏: {article_attrs.get('是否专栏', '否')} | 原创: {article_attrs.get('是否原创声明', '否')} | 时间: {article_attrs.get('创建时间', '未知')} | 打赏: {reward_info.get('类型', '无')}"
                        
                        log_callback({
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'message': f'[{timestamp}] 📊 文章属性: {attrs_str}',
                            'type': 'info',
                            'isAttributeLog': True,
                            'articleId': article_id
                        })
                    except Exception as e:
                        log_callback({
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'message': f'[{timestamp}] 获取文章属性失败: {e}',
                            'type': 'warning'
                        })
                
                # 生成评论
                prompt = f"{default_prompt}\n\n文章标题: {article_title}\n文章内容: {article_text[:500]}\n\n评论:"
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{timestamp}] 正在调用模型生成评论...',
                    'type': 'info'
                })
                
                comment_content, _ = call_model(
                    selected_model, 
                    api_key, 
                    prompt, 
                    'comment',
                    secret_key=models_config.get(selected_model, {}).get('secretKey'),
                    base_url=models_config.get(selected_model, {}).get('baseUrl'),
                    model_name=models_config.get(selected_model, {}).get('modelName'),
                    max_tokens=models_config.get(selected_model, {}).get('maxTokens'),
                    temperature=models_config.get(selected_model, {}).get('temperature'),
                    operation_type='悬赏评论',
                    default_prompt=default_prompt
                )
                
                comment_content = comment_content.strip()
                # 检查返回的内容是否为空
                if not comment_content:
                    log_callback({
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'message': f'[{timestamp}] 模型返回空内容，使用默认评论',
                        'type': 'warning'
                    })
                    comment_content = "分析到位，学习了"
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{timestamp}] 生成的评论内容: {comment_content[:80]}...',
                    'type': 'info'
                })
                
                # 发布评论
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{timestamp}] 正在发布评论到雪球...',
                    'type': 'info'
                })
                comment_result = post_topic_comment(article_id, comment_content, cookie)
                
                if comment_result['success']:
                    success_count += 1
                    results.append({
                        "articleId": article_id,
                        "success": True,
                        "comment": comment_content,
                        "message": comment_result['message']
                    })
                    log_callback({
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'message': f'[{timestamp}] ✅ 文章 {article_id}: 评论成功 - {comment_content}',
                        'type': 'success'
                    })
                else:
                    failed_count += 1
                    results.append({
                        "articleId": article_id,
                        "success": False,
                        "comment": comment_content,
                        "message": comment_result['message']
                    })
                    log_callback({
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'message': f'[{timestamp}] ❌ 文章 {article_id}: 评论失败 - {comment_result["message"]}',
                        'type': 'error'
                    })
                
                if idx < len(article_ids) - 1:
                    time.sleep(2)  # 避免请求过快
                
            except Exception as e:
                failed_count += 1
                results.append({
                    "articleId": article_id,
                    "success": False,
                    "message": f"处理失败: {str(e)}"
                })
                log_callback({
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'message': f'[{time.strftime("%H:%M:%S")}] ❌ 处理文章 {article_id} 异常: {str(e)}',
                    'type': 'error'
                })
                import traceback
                traceback.print_exc()
        
        log_callback({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'[{time.strftime("%H:%M:%S")}] ========== 悬赏评论任务完成 ==========',
            'type': 'info'
        })
        log_callback({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'[{time.strftime("%H:%M:%S")}] 总计: 成功 {success_count} 篇，失败 {failed_count} 篇',
            'type': 'info'
        })
        
        return {
            'totalArticles': len(article_ids),
            'successCount': success_count,
            'failedCount': failed_count,
            'results': results
        }
        
    except Exception as e:
        log_callback({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'message': f'悬赏评论任务异常: {str(e)}',
            'type': 'error'
        })
        import traceback
        traceback.print_exc()
        return {'totalArticles': 0, 'successCount': 0, 'failedCount': 0}

# ==================== 话题文章搜索相关API ====================
@app.route('/api/search-topic-articles', methods=['POST'])
def search_topic_articles():
    """搜索话题下的文章"""
    try:
        data = request.json
        topic_names = data.get("topics", [])
        max_count = data.get("maxCount", 100)
        
        if not topic_names or len(topic_names) == 0:
            return jsonify({
                "success": False,
                "message": "请至少选择一个话题"
            }), 400
        
        # 获取默认用户的cookie
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        users = users_data.get("users", [])
        
        cookie = None
        for user in users:
            if user.get("id") == default_user_id and user.get("cookie"):
                cookie = user.get("cookie")
                break
        
        if not cookie:
            return jsonify({
                "success": False,
                "message": "请先配置默认用户"
            }), 400
        
        print(f"开始搜索话题文章，话题: {topic_names}, 数量: {max_count}")
        
        articles = get_topic_articles(topic_names, cookie, max_count)
        
        return jsonify({
            "success": True,
            "data": {
                "articles": articles,
                "count": len(articles)
            },
            "message": f"搜索成功，共找到 {len(articles)} 篇文章"
        })
        
    except Exception as e:
        print(f"搜索话题文章异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"搜索失败: {str(e)}"
        }), 500

# ==================== 话题文章评论相关API ====================
def post_topic_comment(article_id, comment_content, cookie):
    """发布话题文章评论"""
    print(f"[{time.strftime('%H:%M:%S')}] ========== 开始发布评论 ==========")
    print(f"[{time.strftime('%H:%M:%S')}] 文章ID: {article_id}")
    print(f"[{time.strftime('%H:%M:%S')}] 评论内容: {comment_content[:100]}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie
    }
    
    session = requests.Session()
    
    try:
        # 1. 文本审核
        print(f"[{time.strftime('%H:%M:%S')}] 步骤1: 文本审核...")
        text_check_url = "https://xueqiu.com/statuses/text_check.json"
        text_check_data = {
            "text": f"<p>{comment_content}</p>",
            "type": "3"
        }
        text_check_response = session.post(text_check_url, headers=headers, data=text_check_data, timeout=10)
        print(f"[{time.strftime('%H:%M:%S')}] 文本审核响应状态码: {text_check_response.status_code}")
        if text_check_response.status_code != 200:
            print(f"[{time.strftime('%H:%M:%S')}] 文本审核失败")
            return {"success": False, "message": "文本审核失败"}
        
        time.sleep(0.5)
        
        # 2. 获取会话token
        print(f"[{time.strftime('%H:%M:%S')}] 步骤2: 获取会话token...")
        token_url = "https://xueqiu.com/provider/session/token.json"
        token_params = {
            "api_path": "/statuses/reply.json",
            "_": int(time.time() * 1000)
        }
        token_response = session.get(token_url, headers=headers, params=token_params, timeout=10)
        print(f"[{time.strftime('%H:%M:%S')}] 获取token响应状态码: {token_response.status_code}")
        if token_response.status_code != 200:
            print(f"[{time.strftime('%H:%M:%S')}] 获取token失败")
            return {"success": False, "message": "获取token失败"}
        
        token_data = token_response.json()
        session_token = token_data.get("session_token", "")
        if session_token:
            print(f"[{time.strftime('%H:%M:%S')}] 获取到的session_token: {session_token[:20]}...")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] 获取到的session_token: (空)")
        if not session_token:
            print(f"[{time.strftime('%H:%M:%S')}] 未获取到session_token")
            return {"success": False, "message": "未获取到session_token"}
        
        time.sleep(0.5)
        
        # 3. 发布评论
        print(f"[{time.strftime('%H:%M:%S')}] 步骤3: 发布评论...")
        reply_url = "https://xueqiu.com/statuses/reply.json"
        reply_data = {
            "comment": f"<p>{comment_content}</p>",
            "forward": "1",
            "id": article_id,
            "post_source": "htl",
            "post_position": "pc_home_feedcard",
            "session_token": session_token
        }
        print(f"[{time.strftime('%H:%M:%S')}] 准备发布评论，请求数据: {reply_data}")
        reply_response = session.post(reply_url, headers=headers, data=reply_data, timeout=10)
        print(f"[{time.strftime('%H:%M:%S')}] 发布评论响应状态码: {reply_response.status_code}")
        
        if reply_response.status_code == 200:
            reply_data_result = reply_response.json()
            print(f"[{time.strftime('%H:%M:%S')}] 发布评论响应内容: {reply_data_result}")
            if "id" in reply_data_result:
                print(f"[{time.strftime('%H:%M:%S')}] ========== 评论发布成功，评论ID: {reply_data_result.get('id')} ==========")
                return {"success": True, "message": "评论发布成功", "comment_id": reply_data_result.get('id')}
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 评论发布失败: 响应格式异常")
                return {"success": False, "message": "评论发布失败: 响应格式异常"}
        else:
            print(f"[{time.strftime('%H:%M:%S')}] 评论发布请求失败，状态码: {reply_response.status_code}")
            return {"success": False, "message": f"评论发布请求失败，状态码: {reply_response.status_code}"}
            
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 发布评论异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": f"发布评论请求失败: {str(e)}"}

@app.route('/api/start-topic-comments', methods=['POST'])
def start_topic_comments():
    """启动话题评论任务"""
    global topic_comments_instance
    
    try:
        with topic_comments_lock:
            if topic_comments_instance and topic_comments_instance.is_running:
                return jsonify({
                    "success": False,
                    "message": "已有话题评论任务在运行"
                }), 400
            
            data = request.json
            article_ids = data.get("articleIds", [])
            selected_model = data.get("selectedModel", "ark")
            models_config = data.get("models", {})
            articles = data.get("articles", [])
            
            if not article_ids or len(article_ids) == 0:
                return jsonify({
                    "success": False,
                    "message": "请至少选择一篇文章"
                }), 400
            
            # 清空日志和状态
            topic_comments_logs.clear()
            topic_comments_status.update({
                'isRunning': True,
                'processedArticles': 0,
                'successComments': 0,
                'failedAttempts': 0
            })
            
            # 定义日志回调函数
            def log_callback(log_entry):
                topic_comments_logs.append(log_entry)
                topic_comments_status['processedArticles'] = len(topic_comments_logs)
            
            # 创建任务实例并启动
            topic_comments_instance = TopicCommenterTask()
            topic_comments_instance.start(
                article_ids=article_ids,
                selected_model=selected_model,
                models_config=models_config,
                articles=articles,
                log_callback=log_callback
            )
            
            return jsonify({
                "success": True,
                "message": "话题评论任务已启动"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"启动话题评论任务失败: {str(e)}"
        }), 500

@app.route('/api/stop-topic-comments', methods=['POST'])
def stop_topic_comments():
    """停止话题评论任务"""
    global topic_comments_instance
    
    try:
        with topic_comments_lock:
            if topic_comments_instance:
                topic_comments_instance.stop()
                return jsonify({
                    "success": True,
                    "message": "话题评论任务已停止"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "没有运行中的话题评论任务"
                }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"停止话题评论任务失败: {str(e)}"
        }), 500

@app.route('/api/topic-comments-status', methods=['GET'])
def get_topic_comments_status():
    """获取话题评论任务状态"""
    try:
        return jsonify({
            "success": True,
            "data": topic_comments_status
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取状态失败: {str(e)}"
        }), 500

@app.route('/api/topic-comments-logs', methods=['GET'])
def get_topic_comments_logs():
    """获取话题评论任务日志"""
    try:
        return jsonify({
            "success": True,
            "data": topic_comments_logs
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取日志失败: {str(e)}"
        }), 500

@app.route('/api/comment-topic-articles', methods=['POST'])
def comment_topic_articles():
    """对话题文章发表评论（保留旧接口）"""
    return jsonify({
        "success": False,
        "message": "请使用新的接口 /api/start-topic-comments"
    }), 400

# ==================== 悬赏问答文章相关API ====================
@app.route('/api/fetch-reward-articles', methods=['POST'])
def fetch_reward_articles():
    """获取悬赏问答文章"""
    try:
        data = request.json
        max_count = data.get("maxCount", 50)
        
        # 获取默认用户的cookie
        users_data = load_users()
        default_user_id = users_data.get("defaultUserId")
        users = users_data.get("users", [])
        
        cookie = None
        for user in users:
            if user.get("id") == default_user_id and user.get("cookie"):
                cookie = user.get("cookie")
                break
        
        if not cookie:
            return jsonify({
                "success": False,
                "message": "请先配置默认用户"
            }), 400
        
        print(f"[{time.strftime('%H:%M:%S')}] 开始获取悬赏问答文章，数量: {max_count}")
        
        articles = get_reward_articles(cookie, max_count)
        
        print(f"[{time.strftime('%H:%M:%S')}] 为每篇文章获取详细的悬赏信息...")
        
        # 为每篇文章获取详细的悬赏信息
        for idx, article in enumerate(articles):
            try:
                article_id = article.get('id')
                # 检查文章ID是否是有效数字
                if isinstance(article_id, str) and article_id.startswith('reward_html_'):
                    print(f"[{time.strftime('%H:%M:%S')}] 文章 {idx+1}: ID={article_id} 是HTML解析的假ID，跳过获取详细信息")
                    article['rewardExpired'] = True
                    article['canComment'] = False
                    article['rewardAmount'] = article.get('reward_amount', 0)
                    article['rewardRemaining'] = 0
                    article['rewardAnswerCount'] = 0
                    continue
                
                print(f"[{time.strftime('%H:%M:%S')}] 文章 {idx+1}: 获取 ID={article_id} 的详细信息...")
                stats = get_article_stats(article_id, cookie)
                
                # 更新文章信息 - 使用API返回的真实数据
                article['rewardExpired'] = stats.get('rewardExpired', False)
                article['canComment'] = not stats.get('rewardExpired', True)
                article['rewardAmount'] = stats.get('rewardAmount', article.get('reward_amount', 0))
                article['rewardCount'] = stats.get('rewardCount', article.get('reward_count', 0))
                article['viewCount'] = stats.get('viewCount', 0)
                article['likeCount'] = stats.get('likeCount', 0)
                article['replyCount'] = stats.get('replyCount', 0)
                
                # 使用API返回的真实剩余金额
                article['rewardRemaining'] = stats.get('rewardRemaining', article.get('rewardAmount', 0))
                article['rewardAnswerCount'] = article.get('rewardCount', 0)
                article['rewardState'] = stats.get('rewardState', '')
                
                status_text = "进行中" if not article['rewardExpired'] else "已结束"
                print(f"[{time.strftime('%H:%M:%S')}]   文章 {idx+1}: 悬赏{status_text}, 金额¥{article['rewardAmount']}, 剩余¥{article['rewardRemaining']}, 回答{article['rewardAnswerCount']}个")
                
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] 获取文章 {idx+1} 详细信息失败: {e}")
                article['rewardExpired'] = True
                article['canComment'] = False
                article['rewardAmount'] = article.get('reward_amount', 0)
                article['rewardRemaining'] = 0
                article['rewardAnswerCount'] = 0
        
        print(f"[{time.strftime('%H:%M:%S')}] 悬赏问答文章获取完成，共获取 {len(articles)} 篇文章")
        
        return jsonify({
            "success": True,
            "data": {
                "articles": articles,
                "count": len(articles)
            },
            "message": f"获取成功，共找到 {len(articles)} 篇悬赏文章"
        })
        
    except Exception as e:
        print(f"获取悬赏问答文章异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"获取失败: {str(e)}"
        }), 500

@app.route('/api/start-reward-comments', methods=['POST'])
def start_reward_comments():
    """启动悬赏评论任务"""
    global reward_comments_instance
    
    try:
        with reward_comments_lock:
            if reward_comments_instance and reward_comments_instance.is_running:
                return jsonify({
                    "success": False,
                    "message": "已有悬赏评论任务在运行"
                }), 400
            
            data = request.json
            article_ids = data.get("articleIds", [])
            selected_model = data.get("selectedModel", "ark")
            models_config = data.get("models", {})
            articles = data.get("articles", [])
            
            if not article_ids or len(article_ids) == 0:
                return jsonify({
                    "success": False,
                    "message": "请至少选择一篇文章"
                }), 400
            
            # 清空日志和状态
            reward_comments_logs.clear()
            reward_comments_status.update({
                'isRunning': True,
                'processedArticles': 0,
                'successComments': 0,
                'failedAttempts': 0
            })
            
            # 定义日志回调函数
            def log_callback(log_entry):
                reward_comments_logs.append(log_entry)
                reward_comments_status['processedArticles'] = len(reward_comments_logs)
            
            # 创建任务实例并启动
            reward_comments_instance = RewardCommenterTask()
            reward_comments_instance.start(
                article_ids=article_ids,
                selected_model=selected_model,
                models_config=models_config,
                articles=articles,
                log_callback=log_callback
            )
            
            return jsonify({
                "success": True,
                "message": "悬赏评论任务已启动"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"启动悬赏评论任务失败: {str(e)}"
        }), 500

@app.route('/api/stop-reward-comments', methods=['POST'])
def stop_reward_comments():
    """停止悬赏评论任务"""
    global reward_comments_instance
    
    try:
        with reward_comments_lock:
            if reward_comments_instance:
                reward_comments_instance.stop()
                return jsonify({
                    "success": True,
                    "message": "悬赏评论任务已停止"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "没有运行中的悬赏评论任务"
                }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"停止悬赏评论任务失败: {str(e)}"
        }), 500

@app.route('/api/reward-comments-status', methods=['GET'])
def get_reward_comments_status():
    """获取悬赏评论任务状态"""
    try:
        return jsonify({
            "success": True,
            "data": reward_comments_status
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取状态失败: {str(e)}"
        }), 500

@app.route('/api/reward-comments-logs', methods=['GET'])
def get_reward_comments_logs():
    """获取悬赏评论任务日志"""
    try:
        return jsonify({
            "success": True,
            "data": reward_comments_logs
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取日志失败: {str(e)}"
        }), 500

@app.route('/api/comment-reward-articles', methods=['POST'])
def comment_reward_articles():
    """对悬赏问答文章发表评论（保留旧接口）"""
    return jsonify({
        "success": False,
        "message": "请使用新的接口 /api/start-reward-comments"
    }), 400

@app.route('/api/model-operations', methods=['GET'])
def get_model_operations():
    """获取模型操作日志"""
    try:
        import os
        import json
        
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        log_file = os.path.join(logs_dir, 'model_operations.json')
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
        
        return jsonify({
            "success": True,
            "data": logs
        })
        
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 获取模型操作日志异常: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"获取失败: {str(e)}"
        }), 500

if __name__ == '__main__':
    # 在生产环境中，应该使用gunicorn或uwsgi等WSGI服务器
    # 这里使用Flask内置的开发服务器仅用于开发和测试
    app.run(host='0.0.0.0', port=5001, debug=True)
