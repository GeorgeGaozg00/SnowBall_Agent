#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关注列表评论器：自动为所有关注用户的帖子生成并发布评论
"""

import json
import time
import requests
import random
import os
from article_utils import get_article_full_attributes
from model_adapter import call_model

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config', 'defaultConfig.json')
FOLLOWING_LIST_FILE = os.path.join(BASE_DIR, 'config', 'following_list.json')


def load_config():
    """加载配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置失败: {e}")
        return None


def load_following_list():
    """加载关注列表"""
    try:
        with open(FOLLOWING_LIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载关注列表失败: {e}")
        return None


def get_user_posts(user_uid, cookie_str, max_posts=10):
    """获取用户最近发表的文章"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": f"https://xueqiu.com/u/{user_uid}",
        "Cookie": cookie_str,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    
    all_posts = []
    page = 1
    page_size = 20
    
    while len(all_posts) < max_posts:
        api_url = "https://xueqiu.com/statuses/user_timeline.json"
        params = {
            "user_id": user_uid,
            "page": page,
            "count": page_size,
            "max_id": 0
        }
        
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            statuses = data.get('statuses', [])
            
            if not statuses:
                break
            
            for status in statuses:
                if isinstance(status, dict):
                    post_data = {
                        'id': status.get('id'),
                        'title': status.get('title', ''),
                        'description': status.get('description', ''),
                        'text': status.get('text', ''),
                        'created_at': status.get('created_at'),
                        'author_uid': user_uid,
                        'view_count': status.get('view_count', 0),
                        'reply_count': status.get('reply_count', 0),
                        'like_count': status.get('like_count', 0),
                        'retweet_count': status.get('retweet_count', 0),
                        'fav_count': status.get('fav_count', 0),
                        'is_column': status.get('is_column', False),
                        'is_original_declare': status.get('is_original_declare', False),
                        'offer': status.get('offer'),
                        'can_reward': status.get('can_reward', False),
                        'reward_count': status.get('reward_count', 0),
                        'reward_user_count': status.get('reward_user_count', 0),
                        'reward_amount': status.get('reward_amount', 0)
                    }
                    all_posts.append(post_data)
                    
                    if len(all_posts) >= max_posts:
                        break
            
            page += 1
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"  获取帖子失败: {e}")
            break
    
    return all_posts[:max_posts]


def generate_comment_with_ai(article_title, article_content, api_key, selected_model='ark', base_url=None, secret_key=None, model_name=None):
    """使用AI API生成评论，使用文章标题和内容"""
    
    # 构建提示词，包含文章标题和内容
    content_preview = article_content[:500] if article_content else ""
    prompt = f"你是资深投资者，写1-2句理性雪球评论，专业简洁。文章标题：{article_title} 内容：{content_preview} 评论："
    
    try:
        content, _ = call_model(
            model_type=selected_model,
            api_key=api_key,
            prompt=prompt,
            post_type='comment',
            base_url=base_url,
            secret_key=secret_key,
            model_name=model_name,
            operation_type='关注者评论',
            default_prompt=prompt
        )
        # 检查返回的内容是否为空
        content = content.strip()
        if not content:
            print("  模型返回空内容，使用默认评论")
            return "分析到位，学习了"
        return content
    except Exception as e:
        print(f"  生成评论失败: {str(e)}")
        return "分析到位，学习了"


def post_comment(article_id, content, cookie_str):
    """使用雪球API发布评论"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "Referer": "https://xueqiu.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": cookie_str
    }
    
    # 1. 文本审核
    try:
        text_check_url = "https://xueqiu.com/statuses/text_check.json"
        text_check_data = {
            "text": f"<p>{content}</p>",
            "type": "3"
        }
        text_check_response = requests.post(text_check_url, headers=headers, data=text_check_data)
        if text_check_response.status_code != 200:
            return {"success": False, "message": "文本审核失败"}
    except Exception as e:
        return {"success": False, "message": f"文本审核请求失败: {str(e)}"}
    
    time.sleep(1)
    
    # 2. 获取会话token
    try:
        token_url = "https://xueqiu.com/provider/session/token.json"
        token_params = {
            "api_path": "/statuses/reply.json",
            "_": int(time.time() * 1000)
        }
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
    try:
        reply_url = "https://xueqiu.com/statuses/reply.json"
        reply_data = {
            "comment": f"<p>{content}</p>",
            "forward": "1",
            "id": article_id,
            "post_source": "htl",
            "post_position": "pc_home_feedcard",
            "session_token": session_token
        }
        reply_response = requests.post(reply_url, headers=headers, data=reply_data)
        if reply_response.status_code == 200:
            reply_data = reply_response.json()
            if "id" in reply_data:
                return {"success": True, "message": "评论发布成功", "comment_id": reply_data.get('id')}
            else:
                return {"success": False, "message": "评论发布失败: 响应格式异常"}
        else:
            return {"success": False, "message": f"评论发布请求失败，状态码: {reply_response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"发布评论请求失败: {str(e)}"}


def like_post(post_id, cookie_str):
    """
    点赞帖子
    
    Args:
        post_id: 帖子ID
        cookie_str: Cookie字符串
    
    Returns:
        dict: 包含success和message字段
    """
    try:
        # 构建请求头
        headers = {
            "Cookie": cookie_str,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://xueqiu.com",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        
        # 点赞API
        url = f"https://xueqiu.com/statuses/like.json"
        
        # 请求参数
        data = {
            "id": post_id
        }
        
        response = requests.post(url, headers=headers, data=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') or result.get('liked'):
                return {"success": True, "message": "点赞成功"}
            else:
                return {"success": False, "message": f"点赞失败: {result.get('error_description', '未知错误')}"}
        else:
            return {"success": False, "message": f"点赞请求失败，状态码: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"点赞请求失败: {str(e)}"}


def process_following_comments(selected_users=None, posts_per_user=10, test_mode=False, action_type='comment', log_callback=None, stop_event=None):
    """处理关注列表评论/点赞"""
    # 日志列表
    logs = []
    
    def add_log(message, type='info', details=None):
        """添加日志"""
        timestamp = time.strftime('%H:%M:%S')
        log_entry = {
            "timestamp": timestamp,
            "message": message,
            "type": type,
            "details": details
        }
        logs.append(log_entry)
        print(f"[{timestamp}] [{type.upper()}] {message}")
        
        # 实时回调日志
        if log_callback:
            log_callback(log_entry)
    
    def check_stop():
        """检查是否应该停止"""
        if stop_event and stop_event.is_set():
            add_log("任务被用户停止", "warning")
            return True
        return False
    
    # 加载配置
    add_log("正在加载配置...")
    config = load_config()
    if not config:
        add_log("无法加载配置", "error")
        return {"success": False, "message": "无法加载配置", "logs": logs}
    
    cookie_str = config.get('xueQiuCookie')
    if not cookie_str:
        add_log("缺少Cookie", "error")
        return {"success": False, "message": "缺少Cookie", "logs": logs}
    
    # 获取选中的模型和API Key
    selected_model = config.get('selectedModel', 'ark')
    models = config.get('models', {})
    
    # 根据选中的模型获取API Key、base_url、secret_key和model_name
    api_key = None
    base_url = None
    secret_key = None
    model_name = None
    
    if selected_model == 'ark':
        api_key = models.get('ark', {}).get('apiKey')
    elif selected_model == 'openai':
        api_key = models.get('openai', {}).get('apiKey')
        base_url = models.get('openai', {}).get('baseUrl')
    elif selected_model == 'baidu':
        api_key = models.get('baidu', {}).get('apiKey')
        secret_key = models.get('baidu', {}).get('secretKey')
    elif selected_model == 'alibaba':
        api_key = models.get('alibaba', {}).get('apiKey')
        base_url = models.get('alibaba', {}).get('baseUrl')
    elif selected_model == 'deepseek':
        api_key = models.get('deepseek', {}).get('apiKey')
        base_url = models.get('deepseek', {}).get('baseUrl')
    elif selected_model == 'gemini':
        api_key = models.get('gemini', {}).get('apiKey')
        base_url = models.get('gemini', {}).get('baseUrl')
        model_name = models.get('gemini', {}).get('modelName')
    elif selected_model == 'claude':
        api_key = models.get('claude', {}).get('apiKey')
        base_url = models.get('claude', {}).get('baseUrl')
        model_name = models.get('claude', {}).get('modelName')
    else:
        api_key = None
    
    if not api_key:
        add_log("缺少AI API Key", "error")
        return {"success": False, "message": "缺少AI API Key", "logs": logs}
    
    # 使用传入的selected_users或加载关注列表
    # 加载关注列表数据以获取当前用户ID
    following_data = load_following_list()
    if following_data:
        my_uid = following_data.get('userId')
    else:
        my_uid = None
    
    if selected_users and len(selected_users) > 0:
        add_log(f"使用传入的 {len(selected_users)} 个关注用户")
        following_list = selected_users
    else:
        # 加载关注列表
        add_log("正在加载关注列表...")
        if not following_data:
            add_log("无法加载关注列表", "error")
            return {"success": False, "message": "无法加载关注列表", "logs": logs}
        
        following_list = following_data.get('followingList', [])
        add_log(f"找到 {len(following_list)} 个关注用户")
    
    total_users = len(following_list)
    
    if total_users == 0:
        add_log("没有要处理的关注用户", "warning")
        return {"success": True, "message": "没有要处理的用户", "logs": logs, "stats": {"total_users": 0, "total_posts": 0, "total_comments": 0, "success_rate": "0%"}, "results": []}
    
    # 统计信息
    total_users_processed = 0
    total_posts_processed = 0
    total_comments_success = 0
    results = []
    
    # 处理每个用户
    for i, user in enumerate(following_list, 1):
        # 检查是否应该停止
        if check_stop():
            add_log("正在停止任务...", "warning")
            break
        
        user_uid = user.get('uid')
        user_name = user.get('screen_name')
        
        add_log(f"处理用户 {i}/{total_users}: {user_name} (UID: {user_uid})")
        
        # 获取用户最近的帖子
        add_log(f"  获取最近 {posts_per_user} 个帖子...")
        posts = get_user_posts(user_uid, cookie_str, posts_per_user)
        
        if not posts:
            add_log("  未找到帖子", "warning")
            results.append({
                "user": user_name,
                "uid": user_uid,
                "posts": 0,
                "success": 0,
                "message": "未找到帖子"
            })
            # 延迟
            delay = random.uniform(10, 15)
            add_log(f"  等待 {delay:.1f} 秒...")
            time.sleep(delay)
            continue
        
        add_log(f"  成功获取 {len(posts)} 个帖子")
        
        # 处理每个帖子
        user_comments_success = 0
        for j, post in enumerate(posts, 1):
            # 检查是否应该停止
            if check_stop():
                add_log("正在停止任务...", "warning")
                break
            
            add_log(f"  处理帖子 {j}/{len(posts)}")
            add_log(f"  帖子ID: {post['id']}")
            
            # 获取文章完整属性
            article_info = get_article_full_attributes(post)
            
            # 记录文章标题
            add_log(f"  文章标题: {article_info['标题'][:50]}...")
            
            # 记录所有文章属性作为一行日志，使用鲜艳颜色
            attrs = article_info['属性']
            reward_info = article_info['打赏/悬赏信息']
            
            # 构建属性字符串
            attrs_str = f"点赞: {attrs['点赞数']} | 评论: {attrs['评论数']} | 转发: {attrs['转发数']} | 阅读: {attrs['阅读数']} | 收藏: {attrs['收藏数']} | 专栏: {attrs['是否专栏']} | 原创: {attrs['是否原创声明']} | 时间: {attrs['创建时间']} | 打赏: {reward_info['类型']}"
            
            # 使用info类型但前端可以根据内容识别为需要鲜艳颜色的日志
            add_log(f"  📊 文章属性: {attrs_str}", "info", {
                "articleId": article_info['ID'],
                "isAttributeLog": True
            })
            
            if action_type == 'like':
                # 点赞模式
                if test_mode:
                    add_log("  测试模式：跳过点赞")
                    post_result = {"success": True, "message": "测试模式，未实际点赞"}
                else:
                    add_log(f"  点赞帖子 (ID: {post['id']})...")
                    post_result = like_post(post['id'], cookie_str)
                    add_log(f"  点赞API响应: {post_result}")
                
                if post_result.get('success'):
                    add_log(f"  ✅ 点赞成功 (帖子ID: {post['id']})")
                    user_comments_success += 1
                    total_comments_success += 1
                else:
                    add_log(f"  ❌ 点赞失败: {post_result.get('message')}", "error")
            else:
                # 评论模式
                # 直接使用已经获取的文章信息生成评论
                article_title = article_info['标题']
                article_content = article_info['内容']
                
                add_log("  生成评论...")
                comment = generate_comment_with_ai(
                    article_title, 
                    article_content, 
                    api_key, 
                    selected_model=selected_model, 
                    base_url=base_url, 
                    secret_key=secret_key,
                    model_name=model_name
                )
                add_log(f"  评论: {comment}")
                
                # 发布评论
                if test_mode:
                    add_log("  测试模式：跳过发布评论")
                    post_result = {"success": True, "message": "测试模式，未实际发布"}
                else:
                    add_log("  发布评论...")
                    post_result = post_comment(post['id'], comment, cookie_str)
                
                if post_result.get('success'):
                    add_log("  ✅ 评论发布成功")
                    if not test_mode:
                        add_log(f"  评论ID: {post_result.get('comment_id')}")
                    user_comments_success += 1
                    total_comments_success += 1
                else:
                    add_log(f"  ❌ 评论发布失败: {post_result.get('message')}", "error")
            
            # 帖子之间的延迟
            delay = random.uniform(8, 12)
            add_log(f"  等待 {delay:.1f} 秒...")
            time.sleep(delay)
        
        total_users_processed += 1
        total_posts_processed += len(posts)
        
        results.append({
            "user": user_name,
            "uid": user_uid,
            "posts": len(posts),
            "success": user_comments_success,
            "message": f"成功发布 {user_comments_success}/{len(posts)} 条评论"
        })
        
        add_log(f"  用户 {user_name} 处理完成")
        action_text = "点赞" if action_type == 'like' else "评论"
        add_log(f"  成功{action_text} {user_comments_success}/{len(posts)} 条帖子")
        
        # 用户之间的延迟
        if i < total_users:
            # 检查是否应该停止
            if check_stop():
                add_log("正在停止任务...", "warning")
                break
            delay = random.uniform(15, 25)
            add_log(f"\n等待 {delay:.1f} 秒后处理下一个用户...")
            time.sleep(delay)
    
    action_text = "点赞" if action_type == 'like' else "评论"
    add_log(f"关注列表{action_text}处理完成")
    add_log(f"处理用户数: {total_users_processed}")
    add_log(f"处理帖子数: {total_posts_processed}")
    add_log(f"成功{action_text}: {total_comments_success}")
    add_log(f"成功率: {total_comments_success/total_posts_processed*100:.1f}%" if total_posts_processed > 0 else "0%")
    
    return {
        "success": True,
        "message": f"关注列表{action_text}处理完成",
        "stats": {
            "total_users": total_users_processed,
            "total_posts": total_posts_processed,
            "total_comments": total_comments_success,
            "success_rate": f"{total_comments_success/total_posts_processed*100:.1f}%" if total_posts_processed > 0 else "0%"
        },
        "results": results,
        "logs": logs
    }


if __name__ == "__main__":
    # 测试模式
    result = process_following_comments(posts_per_user=2, test_mode=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
