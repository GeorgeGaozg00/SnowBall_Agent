#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型适配器 - 统一的AI模型调用接口
"""

import time
import requests
import re

# 模型配置
MODEL_CONFIGS = {
    "ark": {
        "api_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "model_name": "doubao-seed-2-0-pro-260215",
        "temperature": 0.8,
        "max_tokens_article": 2000,
        "max_tokens_comment": 500,
        "max_tokens_discussion": 500,
        "max_tokens_analysis": 2000,
        "timeout": 120
    },
    "openai": {
        "api_url": "https://api.openai.com/v1/chat/completions",
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens_article": 2000,
        "max_tokens_comment": 500,
        "max_tokens_discussion": 500,
        "max_tokens_analysis": 2000,
        "timeout": 60
    },
    "baidu": {
        "api_url": "",
        "model_name": "ernie-bot",
        "temperature": 0.7,
        "max_tokens_article": 2000,
        "max_tokens_comment": 500,
        "max_tokens_discussion": 500,
        "max_tokens_analysis": 2000,
        "timeout": 60
    },
    "alibaba": {
        "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model_name": "qwen-turbo",
        "temperature": 0.7,
        "max_tokens_article": 4000,
        "max_tokens_comment": 2000,
        "max_tokens_discussion": 2000,
        "max_tokens_analysis": 4000,
        "timeout": 60
    },
    "deepseek": {
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "model_name": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens_article": 2000,
        "max_tokens_comment": 500,
        "max_tokens_discussion": 500,
        "max_tokens_analysis": 2000,
        "timeout": 60
    },
    "gemini": {
        "api_url": "https://generativelanguage.googleapis.com/v1beta",
        "model_name": "gemini-2.5-flash",
        "temperature": 0.7,
        "max_tokens_article": 4000,
        "max_tokens_comment": 2000,
        "max_tokens_discussion": 2000,
        "max_tokens_analysis": 4000,
        "timeout": 60
    },
    "claude": {
        "api_url": "https://oneapi.hk/v1/chat/completions",
        "model_name": "claude-sonnet-4-6",
        "temperature": 0.7,
        "max_tokens_article": 4000,
        "max_tokens_comment": 2000,
        "max_tokens_discussion": 2000,
        "max_tokens_analysis": 4000,
        "timeout": 120
    }
}

def convert_text_to_html(text):
    """将纯文本转换为HTML格式"""
    if not text:
        return text
    
    lines = text.split('\n')
    result_lines = []
    in_list = False
    list_type = None
    
    for line in lines:
        stripped = line.strip()
        
        if re.match(r'^#{1,6}\s', stripped):
            if in_list:
                result_lines.append(f'</{list_type}>')
                in_list = False
                list_type = None
            level = len(re.match(r'^#{1,6}', stripped).group())
            content = stripped[level:].strip()
            result_lines.append(f'<h{level}>{content}</h{level}>')
        
        elif re.match(r'^\d+\.\s', stripped):
            if in_list and list_type != 'ol':
                result_lines.append(f'</{list_type}>')
                in_list = False
            
            if not in_list:
                result_lines.append('<ol>')
                in_list = True
                list_type = 'ol'
            
            content = re.sub(r'^\d+\.\s', '', stripped)
            result_lines.append(f'<li>{content}</li>')
        
        elif re.match(r'^[-*]\s', stripped):
            if in_list and list_type != 'ul':
                result_lines.append(f'</{list_type}>')
                in_list = False
            
            if not in_list:
                result_lines.append('<ul>')
                in_list = True
                list_type = 'ul'
            
            content = re.sub(r'^[-*]\s', '', stripped)
            result_lines.append(f'<li>{content}</li>')
        
        else:
            if in_list:
                result_lines.append(f'</{list_type}>')
                in_list = False
                list_type = None
            
            if stripped:
                result_lines.append(f'<p>{stripped}</p>')
    
    if in_list:
        result_lines.append(f'</{list_type}>')
    
    return '\n'.join(result_lines)

def _call_ark(config, api_key, prompt, post_type):
    """调用火山引擎API"""
    url = config.get("api_url", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
    model_name = config.get("model_name", "doubao-seed-2-0-pro-260215")
    temperature = config.get("temperature", 0.8)
    
    max_tokens_key = f"max_tokens_{post_type}"
    max_tokens = config.get(max_tokens_key, 500)
    timeout = config.get("timeout", 120)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=timeout, proxies={'http': None, 'https': None})
    result = response.json()
    
    if 'choices' not in result:
        raise Exception(f"API调用失败: {result.get('error', {}).get('message', '未知错误')}")
    
    content = result['choices'][0]['message']['content']
    
    title = None
    if post_type == 'article' and '标题：' in content:
        parts = content.split('\n\n', 1)
        if len(parts) > 1:
            title_line = parts[0]
            if '标题：' in title_line:
                title = title_line.replace('标题：', '').strip()
                content = parts[1].strip()
    
    content = convert_text_to_html(content)
    
    return content, title

def _call_openai(config, api_key, prompt, post_type, base_url=None):
    """调用OpenAI兼容API"""
    default_url = config.get("api_url", "https://api.openai.com/v1/chat/completions")
    
    if base_url:
        base_url = base_url.rstrip('/')
        if '/chat/completions' not in base_url:
            url = f"{base_url}/chat/completions"
        else:
            url = base_url
    else:
        url = default_url
    
    model_name = config.get("model_name", "gpt-4")
    temperature = config.get("temperature", 0.7)
    
    max_tokens_key = f"max_tokens_{post_type}"
    max_tokens = config.get(max_tokens_key, 500)
    timeout = config.get("timeout", 60)
    
    print(f"[{time.strftime('%H:%M:%S')}] _call_openai - url: {url}, model: {model_name}, post_type: {post_type}, max_tokens: {max_tokens}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=timeout, proxies={'http': None, 'https': None})
        print(f"[{time.strftime('%H:%M:%S')}] _call_openai - response status code: {response.status_code}")
        print(f"[{time.strftime('%H:%M:%S')}] _call_openai - response text: {response.text[:200]}")
        result = response.json()
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] _call_openai - 请求或解析失败: {str(e)}")
        raise
    
    if 'choices' not in result:
        raise Exception(f"API调用失败: {result.get('error', {}).get('message', '未知错误')}")
    
    content = result['choices'][0]['message']['content']
    
    title = None
    if post_type == 'article' and '标题：' in content:
        parts = content.split('\n\n', 1)
        if len(parts) > 1:
            title_line = parts[0]
            if '标题：' in title_line:
                title = title_line.replace('标题：', '').strip()
                content = parts[1].strip()
    
    content = convert_text_to_html(content)
    
    return content, title

def _call_baidu(config, api_key, secret_key, prompt, post_type):
    """调用百度API"""
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions"
    model_name = config.get("model_name", "ernie-bot")
    temperature = config.get("temperature", 0.7)
    
    max_tokens_key = f"max_tokens_{post_type}"
    max_tokens = config.get(max_tokens_key, 500)
    timeout = config.get("timeout", 60)
    
    auth_url = "https://aip.baidubce.com/oauth/2.0/token"
    auth_data = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": secret_key
    }
    auth_response = requests.post(auth_url, data=auth_data, timeout=timeout, proxies={'http': None, 'https': None})
    access_token = auth_response.json().get('access_token')
    
    if not access_token:
        raise Exception("获取百度API访问令牌失败")
    
    url = f"{url}?access_token={access_token}"
    headers = {"Content-Type": "application/json"}
    
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=timeout, proxies={'http': None, 'https': None})
    result = response.json()
    
    if 'error_code' in result:
        raise Exception(f"API调用失败: {result.get('error_msg', '未知错误')}")
    
    content = result['result']
    
    title = None
    if post_type == 'article' and '标题：' in content:
        parts = content.split('\n\n', 1)
        if len(parts) > 1:
            title_line = parts[0]
            if '标题：' in title_line:
                title = title_line.replace('标题：', '').strip()
                content = parts[1].strip()
    
    content = convert_text_to_html(content)
    
    return content, title

def _call_alibaba(config, api_key, prompt, post_type, base_url=None):
    """调用阿里云API"""
    url = base_url or config.get("api_url", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
    model_name = config.get("model_name", "qwen-turbo")
    temperature = config.get("temperature", 0.7)
    
    max_tokens_key = f"max_tokens_{post_type}"
    max_tokens = config.get(max_tokens_key, 500)
    timeout = config.get("timeout", 60)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=timeout, proxies={'http': None, 'https': None})
    result = response.json()
    
    if 'choices' not in result:
        raise Exception(f"API调用失败: {result.get('error', {}).get('message', '未知错误')}")
    
    content = result['choices'][0]['message']['content']
    
    title = None
    if post_type == 'article' and '标题：' in content:
        parts = content.split('\n\n', 1)
        if len(parts) > 1:
            title_line = parts[0]
            if '标题：' in title_line:
                title = title_line.replace('标题：', '').strip()
                content = parts[1].strip()
    
    content = convert_text_to_html(content)
    
    return content, title

def _call_gemini(config, api_key, prompt, post_type, base_url=None):
    """调用Gemini API"""
    base_url = base_url or config.get("api_url", "https://generativelanguage.googleapis.com/v1beta")
    model_name = config.get("model_name", "gemini-2.5-flash")
    temperature = config.get("temperature", 0.7)
    
    max_tokens_key = f"max_tokens_{post_type}"
    max_tokens = config.get(max_tokens_key, 500)
    timeout = config.get("timeout", 60)
    
    print(f"[{time.strftime('%H:%M:%S')}] _call_gemini - base_url: {base_url}, model: {model_name}, post_type: {post_type}, max_tokens: {max_tokens}")
    
    url = f"{base_url}/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    
    print(f"[{time.strftime('%H:%M:%S')}] _call_gemini - 正在发送请求到: {url}")
    
    try:
        print(f"[{time.strftime('%H:%M:%S')}] _call_gemini - 发送请求（无代理）...")
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        print(f"[{time.strftime('%H:%M:%S')}] _call_gemini - response status code: {response.status_code}")
        print(f"[{time.strftime('%H:%M:%S')}] _call_gemini - response text: {response.text[:200]}")
        result = response.json()
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] _call_gemini - 请求或解析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    
    if 'error' in result:
        raise Exception(f"API调用失败: {result.get('error', {}).get('message', '未知错误')}")
    
    content = result['candidates'][0]['content']['parts'][0]['text']
    
    title = None
    if post_type == 'article' and '标题：' in content:
        parts = content.split('\n\n', 1)
        if len(parts) > 1:
            title_line = parts[0]
            if '标题：' in title_line:
                title = title_line.replace('标题：', '').strip()
                content = parts[1].strip()
    
    content = convert_text_to_html(content)
    
    return content, title

def call_ark_api_with_logs(api_key, prompt, task_name='分析文章'):
    """调用火山引擎API（带详细日志）"""
    print(f"\n[{time.strftime('%H:%M:%S')}] ========== Ark API 调用开始 ==========")
    print(f"[{time.strftime('%H:%M:%S')}] 任务: {task_name}")
    print(f"[{time.strftime('%H:%M:%S')}] API URL: https://ark.cn-beijing.volces.com/api/v3/chat/completions")
    
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "doubao-seed-2-0-pro-260215",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 2000
    }
    
    try:
        print(f"[{time.strftime('%H:%M:%S')}] 正在发送请求...")
        response = requests.post(url, headers=headers, json=data, timeout=120, proxies={'http': None, 'https': None})
        result = response.json()
        
        if 'error' in result:
            error_msg = result.get('error', {}).get('message', '未知错误')
            print(f"[{time.strftime('%H:%M:%S')}] API调用失败: {error_msg}")
            raise Exception(f"API调用失败: {error_msg}")
        
        content = result['choices'][0]['message']['content']
        print(f"[{time.strftime('%H:%M:%S')}] 返回内容长度: {len(content)} 字符")
        print(f"[{time.strftime('%H:%M:%S')}] 返回内容（前500字符）: {content[:500]}...")
        print(f"[{time.strftime('%H:%M:%S')}] ========== Ark API 调用成功 ==========\n")
        
        return content.strip()
        
    except requests.exceptions.Timeout:
        print(f"[{time.strftime('%H:%M:%S')}] API调用超时")
        print(f"[{time.strftime('%H:%M:%S')}] ========== Ark API 调用失败（超时） ==========\n")
        raise Exception("API调用超时")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] API调用异常: {str(e)}")
        print(f"[{time.strftime('%H:%M:%S')}] ========== Ark API 调用失败 ==========\n")
        raise

def call_model(model_type, api_key, prompt, post_type='discussion', extra_config=None, secret_key=None, base_url=None, model_name=None):
    """
    统一模型调用接口
    
    Args:
        model_type: 模型类型 (ark, openai, baidu, alibaba, deepseek, gemini)
        api_key: API密钥
        prompt: 提示词
        post_type: 内容类型 (article, comment, discussion)
        extra_config: 额外配置（会覆盖默认配置）
        secret_key: 百度API的secret_key
        base_url: 自定义API基础URL
        model_name: 自定义模型名称（如 gemini-2.5-flash）
    
    Returns:
        (content, title): 返回内容和标题（如果是article类型）
    """
    print(f"[{time.strftime('%H:%M:%S')}] ========== 调用模型: {model_type} ==========")
    print(f"[{time.strftime('%H:%M:%S')}] 内容类型: {post_type}")
    print(f"[{time.strftime('%H:%M:%S')}] 提交的提示词长度: {len(prompt)} 字符")
    print(f"[{time.strftime('%H:%M:%S')}] 提示词前300字符: {prompt[:300]}...")
    print(f"[{time.strftime('%H:%M:%S')}] base_url: {base_url or '使用默认'}")
    if model_name:
        print(f"[{time.strftime('%H:%M:%S')}] model_name: {model_name}")
    
    config = MODEL_CONFIGS.get(model_type, MODEL_CONFIGS['ark']).copy()
    if model_name:
        config['model_name'] = model_name
    if extra_config:
        config.update(extra_config)
    
    if model_type == 'ark':
        print(f"[{time.strftime('%H:%M:%S')}] 执行 _call_ark")
        result = _call_ark(config, api_key, prompt, post_type)
    elif model_type == 'openai':
        print(f"[{time.strftime('%H:%M:%S')}] 执行 _call_openai")
        result = _call_openai(config, api_key, prompt, post_type, base_url)
    elif model_type == 'baidu':
        print(f"[{time.strftime('%H:%M:%S')}] 执行 _call_baidu")
        result = _call_baidu(config, api_key, secret_key, prompt, post_type)
    elif model_type == 'alibaba':
        print(f"[{time.strftime('%H:%M:%S')}] 执行 _call_alibaba")
        result = _call_alibaba(config, api_key, prompt, post_type, base_url)
    elif model_type == 'deepseek':
        print(f"[{time.strftime('%H:%M:%S')}] 执行 _call_openai (deepseek)")
        result = _call_openai(config, api_key, prompt, post_type, base_url)
    elif model_type == 'gemini':
        print(f"[{time.strftime('%H:%M:%S')}] 执行 _call_gemini")
        result = _call_gemini(config, api_key, prompt, post_type, base_url)
    else:
        print(f"[{time.strftime('%H:%M:%S')}] 未知模型类型，默认使用 _call_ark")
        result = _call_ark(config, api_key, prompt, post_type)
    
    content, title = result
    print(f"[{time.strftime('%H:%M:%S')}] 模型返回内容长度: {len(content)} 字符")
    print(f"[{time.strftime('%H:%M:%S')}] 模型返回内容前200字符: {content[:200]}...")
    if title:
        print(f"[{time.strftime('%H:%M:%S')}] 标题: {title}")
    print(f"[{time.strftime('%H:%M:%S')}] ========== 模型调用完成: {model_type} ==========\n")
    return result

def get_model_config(model_type):
    """获取模型配置"""
    return MODEL_CONFIGS.get(model_type, MODEL_CONFIGS['ark']).copy()

def list_available_models():
    """列出所有可用的模型"""
    return list(MODEL_CONFIGS.keys())
