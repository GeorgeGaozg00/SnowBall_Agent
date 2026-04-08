#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析bonus.html文件，找出文章ID和用户ID的关系
"""

import os
import re
import json


def analyze_bonus_html():
    """分析bonus.html文件"""
    
    bonus_file = os.path.join(os.path.dirname(__file__), '..', 'backend', 'temp', 'bonus.html')
    
    if not os.path.exists(bonus_file):
        print(f"❌ bonus.html文件不存在: {bonus_file}")
        return
    
    print("=" * 80)
    print("  分析 bonus.html 文件中的文章数据结构")
    print("=" * 80)
    
    try:
        with open(bonus_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"✅ 读取bonus.html成功，文件大小: {len(html_content)} 字符")
        
        # 查找所有 target 字段
        target_pattern = r'target:\s*"\\u002F(\d+)\\u002F(\d+)"'
        target_matches = re.findall(target_pattern, html_content)
        
        print(f"\n找到 {len(target_matches)} 个 target 字段")
        
        # 显示前10个
        print("\n" + "-" * 80)
        print("  前10个 target 字段示例")
        print("-" * 80)
        for i, (user_id, article_id) in enumerate(target_matches[:10]):
            print(f"{i+1}. 用户ID: {user_id}, 文章ID: {article_id}")
        
        # 查找文章对象的 id 字段
        id_pattern = r'id:\s*(\d+)'
        id_matches = re.findall(id_pattern, html_content)
        
        print(f"\n找到 {len(id_matches)} 个 id 字段")
        
        # 现在让我们尝试找到包含 id、user_id 和 target 的完整对象
        print("\n" + "=" * 80)
        print("  查找包含 id, user_id, target 的完整文章对象示例")
        print("=" * 80)
        
        # 查找包含这三个字段的区域
        # 使用更复杂的模式来匹配文章对象
        article_pattern = r'\{[^}]*id:\s*(\d+)[^}]*user_id:\s*(\w+)[^}]*target:\s*"\\u002F(\d+)\\u002F(\d+)"[^}]*\}'
        
        # 先找更简单的模式
        simple_pattern = r'id:\s*(\d+)[^}]{0,500}user_id:\s*(\w+)[^}]{0,500}target:\s*"\\u002F(\d+)\\u002F(\d+)"'
        
        matches = list(re.finditer(simple_pattern, html_content, re.DOTALL))
        
        print(f"找到 {len(matches)} 个匹配的文章对象")
        
        if matches:
            print("\n" + "-" * 80)
            print("  详细分析")
            print("-" * 80)
            
            for i, match in enumerate(matches[:3]):
                article_id_from_id = match.group(1)
                user_id_var = match.group(2)
                user_id_from_target = match.group(3)
                article_id_from_target = match.group(4)
                
                print(f"\n示例 {i+1}:")
                print(f"  从 id 字段: {article_id_from_id}")
                print(f"  从 user_id 字段: {user_id_var} (变量名)")
                print(f"  从 target 字段:")
                print(f"    用户ID: {user_id_from_target}")
                print(f"    文章ID: {article_id_from_target}")
                
                # 验证文章ID是否一致
                if article_id_from_id == article_id_from_target:
                    print(f"  ✅ 文章ID一致: {article_id_from_id}")
                else:
                    print(f"  ⚠️  文章ID不一致: {article_id_from_id} vs {article_id_from_target}")
        
        # 让我们尝试找到 id、user_id、target 的关系
        print("\n" + "=" * 80)
        print("  数据结构总结")
        print("=" * 80)
        print("""
从 bonus.html 中发现的文章数据结构：

1. 每篇文章包含以下关键字段：
   - id: 文章ID（数字）
   - user_id: 用户ID（可能是变量名，也可能是数字）
   - target: 格式为 "\\\\u002F{user_id}\\\\u002F{article_id}"

2. target 字段解码后的格式：
   - 原始: "target: \\"\\u002F8152922548\\u002F195620634\\""
   - 解码后: "target: \\"/8152922548/195620634\\""
   - 格式: "/{用户ID}/{文章ID}"

3. 结论：
   - 如果只有文章ID，无法直接通过 statuses/show.json API（会被WAF拦截）
   - 但通过访问文章页面 https://xueqiu.com/1/{article_id} 可以获取到HTML
   - 从HTML的 target 字段中可以同时获取到用户ID
   - 一旦有了用户ID和文章ID，就可以使用其他API获取完整数据
        """)
        
        # 实际测试
        print("\n" + "=" * 80)
        print("  测试：从文章ID推导用户ID的方法")
        print("=" * 80)
        print("""
方法：
1. 访问文章页面: https://xueqiu.com/1/{article_id}
2. 从HTML中提取 window.__NUXT__ 数据
3. 在数据中查找 target 字段
4. 从 target 字段解析出用户ID
5. 使用用户ID和文章ID调用其他API

注意：这个方法可能也会被WAF拦截，但比直接调用 statuses/show.json 更可能成功
        """)
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    analyze_bonus_html()