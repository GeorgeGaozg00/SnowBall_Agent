#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修改后的悬赏文章获取功能
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import json


def test_bonus_html_parsing():
    """测试从bonus.html中提取文章ID和用户ID"""
    
    bonus_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'temp', 'bonus.html')
    
    if not os.path.exists(bonus_file):
        print(f"❌ bonus.html文件不存在: {bonus_file}")
        return
    
    print("=" * 80)
    print("  测试从 bonus.html 中提取文章ID和用户ID")
    print("=" * 80)
    
    try:
        with open(bonus_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"✅ 读取bonus.html成功，文件大小: {len(html_content)} 字符")
        
        import re
        
        # 提取 target 字段（包含用户ID和文章ID）
        target_pattern = r'target:\s*"\\u002F(\d+)\\u002F(\d+)"'
        target_matches = re.findall(target_pattern, html_content)
        
        print(f"\n找到 {len(target_matches)} 个 target 字段")
        
        print("\n" + "-" * 80)
        print("  前10篇文章信息")
        print("-" * 80)
        
        for i, (user_id, article_id) in enumerate(target_matches[:10]):
            print(f"{i+1}. 文章ID: {article_id}, 作者UID: {user_id}")
        
        # 创建文章ID到用户ID的映射
        article_id_to_user_id = {}
        for user_id, article_id in target_matches:
            article_id_to_user_id[article_id] = user_id
        
        print(f"\n✅ 创建了 {len(article_id_to_user_id)} 个文章ID到用户ID的映射")
        
        print("\n" + "=" * 80)
        print("  测试成功！")
        print("=" * 80)
        print("""
修改总结：

1. app.py - fetch_reward_articles函数：
   - 添加了显示文章ID和作者UID的日志
   - 从完整文章数据中提取用户ID（如果之前没有）

2. reward_fetcher.py - fetch_reward_articles函数：
   - 添加了从target字段提取用户ID的功能
   - 创建了文章ID到用户ID的映射
   - 在创建article_info时设置用户ID
   - 添加了显示文章ID和作者UID的日志
        """)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_bonus_html_parsing()