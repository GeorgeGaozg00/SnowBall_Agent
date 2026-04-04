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
        
        if not api_key:
            return jsonify({
                "success": False,
                "message": "缺少AI API Key"
            }), 400
        
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
        elif selected_model == 'deepseek':
            detailed_prompt, _ = call_openai_api(api_key, first_round_prompt, 'discussion', models.get('deepseek', {}).get('baseUrl'))
        elif selected_model == 'gemini':
            detailed_prompt, _ = call_gemini_api(api_key, first_round_prompt, 'discussion', models.get('gemini', {}).get('baseUrl'))
        else:
            return jsonify({
                "success": False,
                "message": f"不支持的模型: {selected_model}"
            }), 400
        
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
        
        if not api_key:
            return jsonify({
                "success": False,
                "message": "缺少AI API Key"
            }), 400
        
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
        elif selected_model == 'deepseek':
            content, title = call_openai_api(api_key, second_round_prompt, post_type, models.get('deepseek', {}).get('baseUrl'))
        elif selected_model == 'gemini':
            content, title = call_gemini_api(api_key, second_round_prompt, post_type, models.get('gemini', {}).get('baseUrl'))
        
        print(f"[{time.strftime('%H:%M:%S')}] 【第二轮】正式文章生成成功")
        
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

# 文本转HTML函数
def text_to_html(text):
    """将纯文本转换为HTML格式"""
    import re
    
    # 先处理Markdown格式的粗体和斜体
    # 处理粗体 **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # 处理斜体 *text*
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    
    # 处理列表
    lines = text.split('\n')
    in_list = False
    list_type = None
    result_lines = []
    
    for line in lines:
        stripped = line.strip()
        
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
    
    # 将纯文本转换为HTML格式
    content = text_to_html(content)
    
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
    
    # 将纯文本转换为HTML格式
    content = text_to_html(content)
    
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
    
    # 将纯文本转换为HTML格式
    content = text_to_html(content)
    
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
    
    # 将纯文本转换为HTML格式
    content = text_to_html(content)
    
    return content, title

def call_gemini_api(api_key, prompt, post_type, base_url='https://generativelanguage.googleapis.com/v1'):
    """调用Google Gemini API"""
    import requests
    
    # Gemini API使用不同的格式
    url = f"{base_url}/models/gemini-pro:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 2000 if post_type == 'article' else 500
        }
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=120)
    result = response.json()
    
    if 'candidates' not in result:
        error_msg = result.get('error', {}).get('message', '未知错误')
        raise Exception(f"API调用失败: {error_msg}")
    
    content = result['candidates'][0]['content']['parts'][0]['text']
    
    # 提取标题（如果是长文）
    title = None
    if post_type == 'article' and '标题：' in content:
        parts = content.split('\n\n', 1)
        if len(parts) > 1:
            title_line = parts[0]
            if '标题：' in title_line:
                title = title_line.replace('标题：', '').strip()
                content = parts[1].strip()
    
    # 将纯文本转换为HTML格式
    content = text_to_html(content)
    
    return content, title

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
PERSONAS_FILE = os.path.join(BASE_DIR, 'personas.json')

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

if __name__ == '__main__':
    # 在生产环境中，应该使用gunicorn或uwsgi等WSGI服务器
    # 这里使用Flask内置的开发服务器仅用于开发和测试
    app.run(host='0.0.0.0', port=5001, debug=True)
