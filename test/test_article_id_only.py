#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试只使用文章ID获取文章属性的方法
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import requests
import json
import time
import re
from bs4 import BeautifulSoup
from article_utils import get_article_full_attributes


def print_separator(title):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_article_page_scraping(article_id, cookie):
    """
    方法1：直接访问文章页面，从HTML中提取数据
    
    Args:
        article_id: 文章ID
        cookie: 雪球Cookie
    """
    print_separator("方法1：直接访问文章页面提取数据")
    
    try:
        session = requests.Session()
        session.trust_env = False
        
        # 请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://xueqiu.com/",
            "Cookie": cookie
        }
        
        # 先访问首页建立会话
        session.get("https://xueqiu.com/", headers=headers, timeout=10)
        time.sleep(0.5)
        
        # 访问文章页面
        article_url = f"https://xueqiu.com/1/{article_id}"
        print(f"访问文章页面: {article_url}")
        
        response = session.get(article_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ 页面访问成功")
            
            # 尝试从script标签中提取数据
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tags = soup.find_all('script')
            
            article_data = None
            
            for script in script_tags:
                script_text = script.string
                if script_text:
                    # 查找 window.__INITIAL_STATE__ 或 window.__NUXT__
                    if '__INITIAL_STATE__' in script_text or '__NUXT__' in script_text:
                        print("找到包含数据的script标签")
                        
                        # 尝试提取JSON数据
                        json_matches = re.findall(r'\{.*"id".*\}', script_text, re.DOTALL)
                        if json_matches:
                            for json_str in json_matches[:3]:
                                try:
                                    data = json.loads(json_str)
                                    if isinstance(data, dict) and 'id' in data:
                                        article_data = data
                                        break
                                except:
                                    continue
            
            if article_data:
                print("✅ 成功从页面提取文章数据")
                print(f"文章ID: {article_data.get('id')}")
                
                # 使用get_article_full_attributes提取属性
                article_info = get_article_full_attributes(article_data)
                
                article_attrs = article_info.get("属性", {})
                reward_info = article_info.get("打赏/悬赏信息", {})
                
                attrs_str = f"点赞: {article_attrs.get('点赞数', 0)} | 评论: {article_attrs.get('评论数', 0)} | 转发: {article_attrs.get('转发数', 0)} | 阅读: {article_attrs.get('阅读数', 0)} | 收藏: {article_attrs.get('收藏数', 0)} | 专栏: {article_attrs.get('是否专栏', '否')} | 原创: {article_attrs.get('是否原创声明', '否')} | 时间: {article_attrs.get('创建时间', '未知')} | 打赏: {reward_info.get('类型', '无')}"
                
                print(f"\n📊 文章属性: {attrs_str}")
                return article_data
            else:
                print("⚠️  未能从页面提取文章数据")
                return None
        else:
            print(f"❌ 页面访问失败，状态码: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_bonus_html(article_id):
    """
    方法2：从已保存的bonus.html中查找文章
    
    Args:
        article_id: 文章ID
    """
    print_separator("方法2：从已保存的bonus.html中查找文章")
    
    bonus_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'temp', 'bonus.html')
    
    if not os.path.exists(bonus_file):
        print(f"⚠️  bonus.html文件不存在: {bonus_file}")
        return None
    
    try:
        with open(bonus_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"✅ 读取bonus.html成功")
        
        # 在HTML中查找包含指定文章ID的部分
        article_pattern = rf'id:\s*{article_id}'
        matches = re.findall(r'\{[^{}]*id:\s*' + re.escape(str(article_id)) + r'[^{}]*\}', html_content)
        
        if matches:
            print(f"✅ 在bonus.html中找到文章ID {article_id}")
            
            # 尝试提取完整的文章数据
            # 这需要更复杂的解析，因为数据是压缩的JavaScript
            print(f"找到 {len(matches)} 个匹配项")
            
            # 尝试解析第一个匹配项
            try:
                # 简单清理一下，把JavaScript对象转换为JSON
                json_str = matches[0]
                # 替换单引号为双引号
                json_str = re.sub(r"'", '"', json_str)
                # 替换变量名（如 x:, y:）为字符串
                json_str = re.sub(r'(\w+):', r'"\1":', json_str)
                
                data = json.loads(json_str)
                print(f"✅ 成功解析文章数据")
                print(f"文章ID: {data.get('id')}")
                return data
            except Exception as e:
                print(f"⚠️  直接解析失败: {e}")
                print("数据是压缩的JavaScript格式，需要更复杂的解析")
                return None
        else:
            print(f"❌ 在bonus.html中未找到文章ID {article_id}")
            return None
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    # 从配置文件加载Cookie
    config_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'config', 'users.json')
    
    cookie = None
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            default_user_id = users_data.get('defaultUserId')
            users = users_data.get('users', [])
            default_user = next((u for u in users if u.get('id') == default_user_id), None)
            if default_user and default_user.get('cookie'):
                cookie = default_user.get('cookie')
                print(f"✅ 从配置文件加载Cookie成功")
        except Exception as e:
            print(f"从配置文件加载Cookie失败: {e}")
    
    if not cookie:
        print("❌ 错误: 请配置默认用户")
        return
    
    # 测试文章ID
    article_id = "382305373"
    
    print("\n" + "=" * 80)
    print(f"  测试只使用文章ID获取文章属性: {article_id}")
    print("=" * 80)
    
    # 方法2：从bonus.html中查找
    test_bonus_html(article_id)
    
    # 方法1：直接访问文章页面
    test_article_page_scraping(article_id, cookie)
    
    print("\n" + "=" * 80)
    print("  总结")
    print("=" * 80)
    print("\n只使用文章ID获取文章属性的方法：")
    print("1. 直接访问文章页面 https://xueqiu.com/1/{article_id}，从HTML中提取数据")
    print("2. 使用 statuses/show.json?id={article_id} API（可能被WAF拦截）")
    print("3. 从悬赏问答页面（bonus.html）中提取数据")
    print("\n但最可靠的方法还是：")
    print("- 通过话题搜索获取文章时保存完整数据")
    print("- 通过用户时间线获取文章时保存完整数据")
    print("- 后续处理时优先使用已保存的完整数据")


if __name__ == "__main__":
    main()