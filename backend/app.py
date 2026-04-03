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
        
        # 提取 API Key（支持新旧格式）
        ark_api_key = None
        if config.get('arkApiKey'):
            # 旧格式
            ark_api_key = config['arkApiKey']
        elif config.get('models'):
            # 新格式
            selected_model = config.get('selectedModel', 'ark')
            if selected_model == 'ark' and config['models'].get('ark'):
                ark_api_key = config['models']['ark'].get('apiKey')
        
        if not ark_api_key:
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
                ark_api_key=ark_api_key,
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
        # 检查热门帖/推荐帖评论任务状态（优先检查正在运行的任务）
        commenter = None
        with commenter_lock:
            commenter = commenter_instance
        
        # 如果热门帖/推荐帖任务正在运行，返回其状态
        if commenter and commenter.is_running:
            return jsonify({
                "success": True,
                "isRunning": True,
                "taskType": "commenting",
                "data": commenter.get_stats(),
                "logs": commenter.get_logs()[-20:],  # 返回最近20条日志
                "message": "获取运行状态成功"
            })
        
        # 检查关注者评论任务状态
        following_commenter = None
        with following_commenter_lock:
            following_commenter = following_commenter_instance
        
        # 如果关注者评论任务正在运行，返回其状态
        if following_commenter and following_commenter.is_running:
            return jsonify({
                "success": True,
                "isRunning": True,
                "taskType": "following",
                "data": following_comments_status,
                "logs": following_comments_logs[-20:],  # 返回最近20条日志
                "message": "获取运行状态成功"
            })
        
        # 如果关注者评论任务存在但已停止，仍然返回其状态（用于显示最终结果）
        if following_commenter:
            return jsonify({
                "success": True,
                "isRunning": False,
                "taskType": "following",
                "data": following_comments_status,
                "logs": following_comments_logs[-20:],  # 返回最近20条日志
                "message": "获取运行状态成功"
            })
        
        # 如果热门帖/推荐帖任务存在但已停止，仍然返回其状态
        if commenter:
            return jsonify({
                "success": True,
                "isRunning": False,
                "taskType": "commenting",
                "data": commenter.get_stats(),
                "logs": commenter.get_logs()[-20:],  # 返回最近20条日志
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

@app.route('/api/generate-content', methods=['POST'])
def generate_content():
    """生成AI内容 - 两轮交互"""
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
        
        if not api_key:
            return jsonify({
                "success": False,
                "message": "缺少AI API Key"
            }), 400
        
        print(f"[{time.strftime('%H:%M:%S')}] ========== 开始两轮交互生成内容 ==========")
        
        # ========== 第一轮：生成雪球风格的详细提示词 ==========
        print(f"[{time.strftime('%H:%M:%S')}] 【第一轮】正在生成雪球风格的详细提示词...")
        
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
        
        # 第一轮调用
        if selected_model == 'ark':
            detailed_prompt, _ = call_ark_api(api_key, first_round_prompt, 'discussion')
        elif selected_model == 'openai':
            detailed_prompt, _ = call_openai_api(api_key, first_round_prompt, 'discussion', models.get('openai', {}).get('baseUrl'))
        elif selected_model == 'baidu':
            detailed_prompt, _ = call_baidu_api(api_key, models.get('baidu', {}).get('secretKey'), first_round_prompt, 'discussion')
        elif selected_model == 'alibaba':
            detailed_prompt, _ = call_alibaba_api(api_key, first_round_prompt, 'discussion', models.get('alibaba', {}).get('baseUrl'))
        else:
            return jsonify({
                "success": False,
                "message": f"不支持的模型: {selected_model}"
            }), 400
        
        print(f"[{time.strftime('%H:%M:%S')}] 【第一轮】详细提示词生成成功")
        print(f"[{time.strftime('%H:%M:%S')}] 生成的提示词预览: {detailed_prompt[:100]}...")
        
        # ========== 第二轮：根据详细提示词生成正式文章 ==========
        print(f"[{time.strftime('%H:%M:%S')}] 【第二轮】正在根据详细提示词生成正式文章...")
        
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
        
        # 第二轮调用
        if selected_model == 'ark':
            content, title = call_ark_api(api_key, second_round_prompt, post_type)
        elif selected_model == 'openai':
            content, title = call_openai_api(api_key, second_round_prompt, post_type, models.get('openai', {}).get('baseUrl'))
        elif selected_model == 'baidu':
            content, title = call_baidu_api(api_key, models.get('baidu', {}).get('secretKey'), second_round_prompt, post_type)
        elif selected_model == 'alibaba':
            content, title = call_alibaba_api(api_key, second_round_prompt, post_type, models.get('alibaba', {}).get('baseUrl'))
        
        print(f"[{time.strftime('%H:%M:%S')}] 【第二轮】正式文章生成成功")
        print(f"[{time.strftime('%H:%M:%S')}] ========== 两轮交互完成 ==========")
        
        return jsonify({
            "success": True,
            "content": content,
            "title": title,
            "detailedPrompt": detailed_prompt  # 返回详细提示词供用户查看
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
        xueqiu_cookie = data.get('xueQiuCookie', '')
        
        if not content:
            return jsonify({
                "success": False,
                "message": "内容不能为空"
            }), 400
        
        if not xueqiu_cookie:
            return jsonify({
                "success": False,
                "message": "缺少雪球Cookie"
            }), 400
        
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

# AI模型调用函数
def call_ark_api(api_key, prompt, post_type):
    """调用火山引擎API"""
    import requests
    
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "doubao-seed-2-0-pro-260215",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 2000 if post_type == 'article' else 500
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=120)
    result = response.json()
    
    if 'choices' not in result:
        raise Exception(f"API调用失败: {result.get('error', {}).get('message', '未知错误')}")
    
    content = result['choices'][0]['message']['content']
    
    # 提取标题（如果是长文）
    title = None
    if post_type == 'article' and '标题：' in content:
        parts = content.split('\n\n', 1)
        if len(parts) > 1:
            title_line = parts[0]
            if '标题：' in title_line:
                title = title_line.replace('标题：', '').strip()
                content = parts[1].strip()
    
    return content, title

def call_openai_api(api_key, prompt, post_type, base_url='https://api.openai.com/v1'):
    """调用OpenAI API"""
    import requests
    
    url = f"{base_url}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 2000 if post_type == 'article' else 500
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=120)
    result = response.json()
    
    if 'choices' not in result:
        raise Exception(f"API调用失败: {result.get('error', {}).get('message', '未知错误')}")
    
    content = result['choices'][0]['message']['content']
    
    # 提取标题（如果是长文）
    title = None
    if post_type == 'article' and '标题：' in content:
        parts = content.split('\n\n', 1)
        if len(parts) > 1:
            title_line = parts[0]
            if '标题：' in title_line:
                title = title_line.replace('标题：', '').strip()
                content = parts[1].strip()
    
    return content, title

def call_baidu_api(api_key, secret_key, prompt, post_type):
    """调用百度文心一言API"""
    import requests
    
    # 获取access token
    token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    token_response = requests.post(token_url)
    access_token = token_response.json().get('access_token')
    
    if not access_token:
        raise Exception("获取百度access token失败")
    
    # 调用API
    url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={access_token}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=120)
    result = response.json()
    
    if 'result' not in result:
        raise Exception(f"API调用失败: {result.get('error_msg', '未知错误')}")
    
    content = result['result']
    
    # 提取标题（如果是长文）
    title = None
    if post_type == 'article' and '标题：' in content:
        parts = content.split('\n\n', 1)
        if len(parts) > 1:
            title_line = parts[0]
            if '标题：' in title_line:
                title = title_line.replace('标题：', '').strip()
                content = parts[1].strip()
    
    return content, title

def call_alibaba_api(api_key, prompt, post_type, base_url=''):
    """调用阿里通义千问API"""
    import requests
    
    if not base_url:
        base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "qwen-turbo",
        "input": {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        },
        "parameters": {
            "max_tokens": 2000 if post_type == 'article' else 500,
            "temperature": 0.8
        }
    }
    
    response = requests.post(base_url, headers=headers, json=data, timeout=120)
    result = response.json()
    
    if 'output' not in result:
        raise Exception(f"API调用失败: {result.get('message', '未知错误')}")
    
    content = result['output']['text']
    
    # 提取标题（如果是长文）
    title = None
    if post_type == 'article' and '标题：' in content:
        parts = content.split('\n\n', 1)
        if len(parts) > 1:
            title_line = parts[0]
            if '标题：' in title_line:
                title = title_line.replace('标题：', '').strip()
                content = parts[1].strip()
    
    return content, title

# 雪球发帖函数
def publish_discussion_to_xueqiu(content, cookie):
    """发布讨论到雪球"""
    import requests
    
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
        result = response.json()
        print(f"发布讨论响应: {result}")
        
        if 'id' not in result:
            error_msg = result.get('error_description', '发布失败')
            print(f"发布失败原因: {error_msg}")
            raise Exception(error_msg)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
        print(f"完整响应内容: {response.text}")
        raise Exception(f"发布失败: {str(e)}")
    
    return result['id']

def publish_article_to_xueqiu(title, content, is_column, cookie):
    """发布长文到雪球"""
    import requests
    
    # 创建会话
    session = requests.Session()
    
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
    
    # 2. 访问mp页面
    print("访问mp页面...")
    mp_response = session.get("https://mp.xueqiu.com/write/", headers=headers)
    print(f"mp页面访问状态码: {mp_response.status_code}")
    
    # 3. 获取session_token
    print("获取session_token...")
    token_url = "https://mp.xueqiu.com/xq/provider/session/token.json?api_path=%2Fstatuses%2Fupdate.json"
    token_response = session.get(token_url, headers=headers)
    print(f"获取token状态码: {token_response.status_code}")
    
    if token_response.status_code != 200:
        # 尝试使用另一个token获取URL
        token_url = "https://xueqiu.com/provider/session/token.json?api_path=%2Fstatuses%2Fupdate.json"
        token_response = session.get(token_url, headers=headers)
        print(f"尝试另一个token URL，状态码: {token_response.status_code}")
        
        if token_response.status_code != 200:
            raise Exception(f"获取token失败，状态码: {token_response.status_code}")
    
    token_data = token_response.json()
    if "session_token" not in token_data:
        raise Exception("未获取到session_token")
    
    session_token = token_data["session_token"]
    print(f"获取session_token成功：{session_token[:16]}...")
    
    # 4. 发布长文
    print("发布长文...")
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
        "draft_id": "0"
    }
    
    if is_column:
        data['column'] = 1
    
    print(f"发布长文请求数据: {data}")
    response = session.post(post_url, data=data, headers=headers)
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text[:500]}")  # 显示前500个字符
    
    try:
        result = response.json()
        print(f"发布长文响应: {result}")
        
        if 'id' not in result:
            error_msg = result.get('error_description', '发布失败')
            print(f"发布失败原因: {error_msg}")
            raise Exception(error_msg)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {str(e)}")
        print(f"完整响应内容: {response.text}")
        raise Exception(f"发布失败: {str(e)}")
    
    return result['id']

if __name__ == '__main__':
    # 在生产环境中，应该使用gunicorn或uwsgi等WSGI服务器
    # 这里使用Flask内置的开发服务器仅用于开发和测试
    app.run(host='0.0.0.0', port=5001, debug=False)
