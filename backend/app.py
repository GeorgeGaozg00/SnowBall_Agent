from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from commenter import XueQiuCommenter
from following_fetcher import FollowingListFetcher
from following_commenter import process_following_comments
import threading
import time
import os
import json

app = Flask(__name__, static_folder='..')
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
        
        if not config.get('arkApiKey'):
            print("错误: 缺少火山引擎API Key")
            return jsonify({
                "success": False,
                "message": "缺少火山引擎API Key"
            }), 400
        
        if not config.get('xueQiuCookie'):
            print("错误: 缺少雪球Cookie")
            return jsonify({
                "success": False,
                "message": "缺少雪球Cookie"
            }), 400
        
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
                ark_api_key=config['arkApiKey'],
                xueqiu_cookie=config['xueQiuCookie'],
                log_callback=log_callback
            )
            
            # 启动评论任务
            daily_limit = config.get('dailyLimit', 30)
            delay_min = config.get('delayMin', 30)
            delay_max = config.get('delayMax', 120)
            test_mode = config.get('testMode', False)
            task_type = config.get('taskType', 'hot')
            
            # 打印任务启动信息，便于调试
            print(f"启动评论任务: {task_type}, 每日限制: {daily_limit}, 延迟: {delay_min}-{delay_max}秒, 测试模式: {test_mode}")
            
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
    
    try:
        # 检查热门帖/推荐帖评论任务状态
        commenter = None
        with commenter_lock:
            commenter = commenter_instance
        
        if commenter:
            return jsonify({
                "success": True,
                "isRunning": commenter.is_running,
                "taskType": "commenting",
                "data": commenter.get_stats(),
                "logs": commenter.get_logs()[-20:],  # 返回最近20条日志
                "message": "获取运行状态成功"
            })
        
        # 检查关注者评论任务状态
        following_commenter = None
        with following_commenter_lock:
            following_commenter = following_commenter_instance
        
        if following_commenter:
            # 无论任务是否运行，都返回关注者评论任务的状态和日志
            return jsonify({
                "success": True,
                "isRunning": following_commenter.is_running,
                "taskType": "following",
                "data": following_comments_status,
                "logs": following_comments_logs[-20:],  # 返回最近20条日志
                "message": "获取运行状态成功"
            })
        
        # 如果没有运行中的任务，也没有评论器实例，返回空状态
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
        config = request.json
        
        # 验证参数
        if not config:
            return jsonify({
                "success": False,
                "message": "请求体不能为空"
            }), 400
        
        if not config.get('xueQiuCookie'):
            return jsonify({
                "success": False,
                "message": "缺少雪球Cookie"
            }), 400
        
        # 创建关注列表获取器实例
        fetcher = FollowingListFetcher(config['xueQiuCookie'])
        
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
        following_file = os.path.join(os.path.dirname(__file__), 'following_list.json')
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
        following_file = os.path.join(os.path.dirname(__file__), 'following_list.json')
        
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
        data = request.json
        xue_qiu_cookie = data.get('xueQiuCookie')
        
        if not xue_qiu_cookie:
            return jsonify({
                "success": False,
                "message": "缺少Cookie"
            }), 400
        
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
        following_file = os.path.join(os.path.dirname(__file__), 'following_list.json')
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

@app.route('/api/config', methods=['GET'])
def load_config():
    """加载配置文件"""
    try:
        config_file = os.path.join(os.path.dirname(__file__), 'config.json')
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            return jsonify({
                "success": True,
                "exists": True,
                "data": config_data,
                "message": "配置加载成功"
            })
        else:
            return jsonify({
                "success": True,
                "exists": False,
                "data": {},
                "message": "配置文件不存在，将使用默认配置"
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
        
        config_file = os.path.join(os.path.dirname(__file__), 'config.json')
        
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

if __name__ == '__main__':
    # 在生产环境中，应该使用gunicorn或uwsgi等WSGI服务器
    # 这里使用Flask内置的开发服务器仅用于开发和测试
    app.run(host='0.0.0.0', port=5001, debug=False)
