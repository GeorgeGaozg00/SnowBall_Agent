# 雪球API功能文档

本文档整理了雪球平台常用API功能的实现方法。

---

## 1. 通过cookie获得用户基本信息

### 文件位置
- `backend/following_fetcher.py` - FollowingListFetcher.get_current_user_id()
- `backend/app.py` - 启动时检查用户cookie有效性

### 实现方法

```python
import requests
import re
import base64
import json

def get_user_info_from_cookie(cookie_str):
    """
    通过Cookie获取用户基本信息
    
    Args:
        cookie_str: Cookie字符串
        
    Returns:
        dict: 用户信息，包含user_id, screen_name, profile_image等
    """
    headers = {
        "Cookie": cookie_str,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://xueqiu.com",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # 方法1: 从JWT token中提取用户ID
    token_match = re.search(r'xq_id_token=([^;]+)', cookie_str)
    if token_match:
        token = token_match.group(1)
        parts = token.split('.')
        if len(parts) >= 2:
            try:
                payload = parts[1] + '=' * ((4 - len(parts[1]) % 4) % 4)
                decoded_payload = base64.urlsafe_b64decode(payload).decode('utf-8')
                user_data = json.loads(decoded_payload)
                if 'uid' in user_data:
                    return {
                        'user_id': str(user_data['uid']),
                        'source': 'jwt_token'
                    }
            except Exception as e:
                print(f"解析JWT token失败: {str(e)}")
    
    # 方法2: 访问个人中心页面
    session = requests.Session()
    response = session.get("https://xueqiu.com/center", headers=headers, timeout=10)
    
    if response.status_code == 200:
        # 从页面中提取用户ID
        match = re.search(r'/u/(\d+)', response.text)
        if match:
            user_id = match.group(1)
            
            # 获取用户详细信息
            user_detail_url = f"https://xueqiu.com/v4/user/show.json?user_id={user_id}"
            user_response = session.get(user_detail_url, headers=headers)
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                return {
                    'user_id': user_id,
                    'screen_name': user_data.get('screen_name', ''),
                    'profile_image': user_data.get('profile_image', ''),
                    'description': user_data.get('description', ''),
                    'source': 'api'
                }
            
            return {
                'user_id': user_id,
                'source': 'page'
            }
    
    return None
```

### API端点
- `https://xueqiu.com/center` - 个人中心页面
- `https://xueqiu.com/v4/user/show.json` - 用户信息API

---

## 2. 通过用户UID获取用户关注列表

### 文件位置
- `backend/following_fetcher.py` - FollowingListFetcher.get_following_list()

### 实现方法

```python
import requests

def get_user_following_list(user_id, cookie_str, size=200):
    """
    获取指定用户的关注列表
    
    Args:
        user_id: 用户UID
        cookie_str: Cookie字符串
        size: 每次请求获取的用户数量
        
    Returns:
        list: 关注用户列表
    """
    headers = {
        "Cookie": cookie_str,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"https://xueqiu.com/u/{user_id}",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    url = "https://xueqiu.com/friendships/friends.json"
    params = {
        "uid": user_id,
        "page": 1,
        "size": size
    }
    
    session = requests.Session()
    response = session.get(url, headers=headers, params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        users = data.get("friends", [])
        
        # 格式化用户信息
        formatted_list = []
        for user in users:
            profile_image_url = user.get('profile_image_url', '')
            photo_domain = user.get('photo_domain', 'http://xavatar.imedao.com/')
            
            if profile_image_url:
                first_image = profile_image_url.split(',')[0] if ',' in profile_image_url else profile_image_url
                if first_image.startswith('http'):
                    full_image_url = first_image
                else:
                    full_image_url = f"{photo_domain}{first_image}"
            else:
                full_image_url = ''
            
            formatted_list.append({
                'uid': user.get('id'),
                'screen_name': user.get('screen_name', '未知用户'),
                'profile_image': full_image_url,
                'description': user.get('description', '') or ''
            })
        
        return formatted_list
    
    return []
```

### API端点
- `https://xueqiu.com/friendships/friends.json` - 关注列表API

---

## 3. 通过UID获取该用户的文章

### 文件位置
- `backend/following_commenter.py` - FollowingCommenterTask.get_user_posts()

### 实现方法

```python
import requests
import json
from datetime import datetime

def get_user_articles(user_id, cookie_str, count=20):
    """
    获取指定用户的文章列表
    
    Args:
        user_id: 用户UID
        cookie_str: Cookie字符串
        count: 获取文章数量
        
    Returns:
        list: 文章列表
    """
    # 先访问首页建立会话
    session = requests.Session()
    home_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Cookie": cookie_str
    }
    
    session.get("https://xueqiu.com/", headers=home_headers, timeout=10)
    
    # 获取用户文章
    api_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://xueqiu.com/u/{user_id}",
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie_str
    }
    
    url = f"https://xueqiu.com/v4/statuses/user_timeline.json"
    params = {
        "user_id": user_id,
        "page": 1,
        "count": count
    }
    
    response = session.get(url, headers=api_headers, params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        statuses = data.get("statuses", [])
        
        articles = []
        for status in statuses:
            created_at = status.get("created_at")
            if created_at:
                created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            else:
                created_time = "未知"
            
            content = status.get("text", "")
            if not content:
                content = status.get("description", "")
            
            articles.append({
                "id": status.get("id"),
                "title": status.get("title") or "无标题 (可能是短贴)",
                "content": content,
                "like_count": status.get("like_count", 0),
                "reply_count": status.get("reply_count", 0),
                "retweet_count": status.get("retweet_count", 0),
                "view_count": status.get("view_count", 0),
                "fav_count": status.get("fav_count", 0),
                "is_column": status.get("is_column", False),
                "created_at": created_time,
                "user_id": user_id
            })
        
        return articles
    
    return []
```

### API端点
- `https://xueqiu.com/v4/statuses/user_timeline.json` - 用户时间线API

---

## 4. 通过文章ID获取文章属性

### 文件位置
- `backend/article_utils.py` - get_article_from_url(), get_article_full_attributes()

### 实现方法

```python
import requests
from datetime import datetime

def get_article_attributes(article_id, cookie_str):
    """
    通过文章ID获取文章完整属性
    
    Args:
        article_id: 文章ID
        cookie_str: Cookie字符串
        
    Returns:
        dict: 文章完整属性
    """
    # 完整的浏览器请求流程
    session = requests.Session()
    
    # 步骤1: 访问首页建立会话
    home_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    if cookie_str:
        home_headers["Cookie"] = cookie_str
    
    session.get("https://xueqiu.com/", headers=home_headers, timeout=10)
    
    # 步骤2: 获取文章详情
    api_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://xueqiu.com/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie_str
    }
    
    api_url = f"https://xueqiu.com/statuses/show.json?id={article_id}"
    response = session.get(api_url, headers=api_headers)
    
    if response.status_code != 200:
        return None
    
    data = response.json()
    
    # 解析文章信息
    created_at = data.get("created_at")
    if created_at:
        created_time = datetime.fromtimestamp(created_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
    else:
        created_time = "未知"
    
    # 获取完整内容
    content = data.get("text", "")
    if not content:
        content = data.get("description", "")
    
    # 解析打赏/悬赏信息
    offer = data.get("offer")
    reward_info = {"类型": "无", "是否开启": False}
    
    if offer and isinstance(offer, dict):
        amount = offer.get("amount", 0)
        balance = offer.get("balance", 0)
        state = offer.get("state", "")
        
        reward_info = {
            "类型": "悬赏",
            "是否开启": True,
            "状态": "进行中" if state == "NORMAL" else state,
            "总金额(元)": round(amount / 100, 2),
            "剩余金额(元)": round(balance / 100, 2)
        }
    else:
        is_reward_enabled = data.get("can_reward", False)
        if is_reward_enabled:
            reward_info = {
                "类型": "打赏",
                "是否开启": True,
                "打赏人数": data.get("reward_count", 0),
                "累计金额(元)": round(data.get("reward_amount", 0) / 100, 2)
            }
    
    article_info = {
        "ID": data.get("id"),
        "标题": data.get("title") or "无标题 (可能是短贴)",
        "内容": content,
        "属性": {
            "点赞数": data.get("like_count", 0),
            "评论数": data.get("reply_count", 0),
            "转发数": data.get("retweet_count", 0),
            "阅读数": data.get("view_count", 0),
            "收藏数": data.get("fav_count", 0),
            "是否专栏": "是" if data.get("is_column", False) else "否",
            "是否原创声明": "是" if data.get("is_original_declare", False) else "否",
            "创建时间": created_time
        },
        "打赏/悬赏信息": reward_info
    }
    
    return article_info
```

### API端点
- `https://xueqiu.com/statuses/show.json` - 文章详情API

---

## 5. 对文章进行点评（发布评论）

### 文件位置
- `backend/commenter.py` - Commenter.post_comment()
- `backend/following_commenter.py` - post_comment()

### 实现方法

```python
import requests
import time

def publish_comment(article_id, content, cookie_str):
    """
    对文章发布评论
    
    Args:
        article_id: 文章ID
        content: 评论内容
        cookie_str: Cookie字符串
        
    Returns:
        dict: 包含success, message, comment_id字段
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_str
    }
    
    session = requests.Session()
    
    # 步骤1: 文本审核
    text_check_url = "https://xueqiu.com/statuses/text_check.json"
    text_check_data = {
        "text": f"<p>{content}</p>",
        "type": "3"
    }
    
    try:
        text_check_response = session.post(text_check_url, headers=headers, data=text_check_data)
        if text_check_response.status_code != 200:
            return {"success": False, "message": "文本审核失败"}
    except Exception as e:
        return {"success": False, "message": f"文本审核请求失败: {str(e)}"}
    
    time.sleep(1)
    
    # 步骤2: 获取会话token
    token_url = "https://xueqiu.com/provider/session/token.json"
    token_params = {
        "api_path": "/statuses/reply.json",
        "_": int(time.time() * 1000)
    }
    
    try:
        token_response = session.get(token_url, headers=headers, params=token_params)
        if token_response.status_code != 200:
            return {"success": False, "message": "获取token失败"}
        
        token_data = token_response.json()
        session_token = token_data.get("session_token", "")
        if not session_token:
            return {"success": False, "message": "未获取到session_token"}
    except Exception as e:
        return {"success": False, "message": f"获取token请求失败: {str(e)}"}
    
    time.sleep(1)
    
    # 步骤3: 发布评论
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
            if "id" in reply_data:
                return {
                    "success": True, 
                    "message": "评论发布成功", 
                    "comment_id": reply_data.get('id')
                }
            else:
                return {"success": False, "message": "评论发布失败: 响应格式异常"}
        else:
            return {"success": False, "message": f"评论发布请求失败，状态码: {reply_response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"发布评论请求失败: {str(e)}"}
```

### API端点
- `https://xueqiu.com/statuses/text_check.json` - 文本审核API
- `https://xueqiu.com/provider/session/token.json` - 获取会话token API
- `https://xueqiu.com/statuses/reply.json` - 发布评论API

---

## 6. 点赞

### 文件位置
- `backend/following_commenter.py` - like_post()

### 实现方法

```python
import requests

def like_article(article_id, cookie_str):
    """
    对文章进行点赞
    
    Args:
        article_id: 文章ID
        cookie_str: Cookie字符串
        
    Returns:
        dict: 包含success和message字段
    """
    headers = {
        "Cookie": cookie_str,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://xueqiu.com",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    
    url = "https://xueqiu.com/statuses/like.json"
    data = {
        "id": article_id
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("is_liked", False):
                return {"success": True, "message": "点赞成功"}
            else:
                return {"success": False, "message": "点赞失败"}
        else:
            return {"success": False, "message": f"点赞请求失败，状态码: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"点赞请求失败: {str(e)}"}
```

### API端点
- `https://xueqiu.com/statuses/like.json` - 点赞API

---

## 7. 发表长文/讨论/专栏文章

### 文件位置
- `backend/app.py` - publish_post()

### 实现方法

```python
import requests
import time

def publish_post(content, title='', post_type='discussion', is_column=False, cookie_str=''):
    """
    发布文章到雪球
    
    Args:
        content: 文章内容（HTML格式）
        title: 文章标题
        post_type: 文章类型 ('discussion' - 讨论, 'long' - 长文, 'column' - 专栏)
        is_column: 是否为专栏文章
        cookie_str: Cookie字符串
        
    Returns:
        dict: 包含success, message, post_id字段
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_str
    }
    
    session = requests.Session()
    
    # 步骤1: 访问首页建立会话
    session.get("https://xueqiu.com/", headers=headers, timeout=10)
    time.sleep(0.5)
    
    # 步骤2: 文本审核
    text_check_url = "https://xueqiu.com/statuses/text_check.json"
    text_check_data = {
        "text": content,
        "type": "1" if is_column else "2"
    }
    
    try:
        text_check_response = session.post(text_check_url, headers=headers, data=text_check_data)
        if text_check_response.status_code != 200:
            return {"success": False, "message": "文本审核失败"}
    except Exception as e:
        return {"success": False, "message": f"文本审核请求失败: {str(e)}"}
    
    time.sleep(1)
    
    # 步骤3: 获取会话token
    token_url = "https://xueqiu.com/provider/session/token.json"
    token_params = {
        "api_path": "/statuses/update.json",
        "_": int(time.time() * 1000)
    }
    
    try:
        token_response = session.get(token_url, headers=headers, params=token_params)
        if token_response.status_code != 200:
            return {"success": False, "message": "获取token失败"}
        
        token_data = token_response.json()
        session_token = token_data.get("session_token", "")
        if not session_token:
            return {"success": False, "message": "未获取到session_token"}
    except Exception as e:
        return {"success": False, "message": f"获取token请求失败: {str(e)}"}
    
    time.sleep(1)
    
    # 步骤4: 发布文章
    update_url = "https://xueqiu.com/statuses/update.json"
    update_data = {
        "description": content,
        "session_token": session_token
    }
    
    # 根据文章类型添加不同参数
    if title:
        update_data["title"] = title
    
    if is_column:
        update_data["is_column"] = "true"
    else:
        if post_type == 'long':
            update_data["is_long"] = "true"
    
    try:
        update_response = session.post(update_url, headers=headers, data=update_data)
        if update_response.status_code == 200:
            result = update_response.json()
            if "id" in result:
                return {
                    "success": True,
                    "message": "文章发布成功",
                    "post_id": result.get('id')
                }
            else:
                return {"success": False, "message": "文章发布失败: 响应格式异常"}
        else:
            return {"success": False, "message": f"文章发布请求失败，状态码: {update_response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"发布文章请求失败: {str(e)}"}
```

### API端点
- `https://xueqiu.com/statuses/text_check.json` - 文本审核API
- `https://xueqiu.com/provider/session/token.json` - 获取会话token API
- `https://xueqiu.com/statuses/update.json` - 发布文章API

### 文章类型说明
- **讨论**: `post_type='discussion'`, `is_column=False`
- **长文**: `post_type='long'`, `is_column=False` (添加 `is_long=true`)
- **专栏**: `post_type='column'`, `is_column=True` (添加 `is_column=true`)

---

## 通用请求头

所有API请求都建议使用以下完整的请求头：

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://xueqiu.com/",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://xueqiu.com",
    "Sec-Ch-Ua": '"Chromium";v="120", "Google Chrome";v="120", "Not A Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Cookie": cookie_str
}
```

## 注意事项

1. **Cookie有效期**: Cookie可能会过期，需要定期更新
2. **请求频率**: 注意控制请求频率，避免被限流
3. **文本审核**: 发布内容前必须先进行文本审核
4. **会话Token**: 发布操作需要先获取session_token
5. **完整请求流程**: 建议先访问首页建立会话，再执行API请求
6. **错误处理**: 所有API调用都需要完善的错误处理机制

---

## 参考文件

- `backend/article_utils.py` - 文章工具类
- `backend/commenter.py` - 评论功能
- `backend/following_commenter.py` - 关注者评论
- `backend/following_fetcher.py` - 关注列表获取
- `backend/app.py` - 主应用，包含发布文章等功能
