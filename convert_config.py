#!/usr/bin/env python3
"""
转换配置文件为新格式
"""

import json
import os

config_file = 'backend/config.json'

# 读取当前配置
with open(config_file, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 转换为新格式
new_config = {
    'selectedModel': 'ark',
    'models': {
        'ark': {
            'apiKey': config.get('arkApiKey', '')
        },
        'openai': {
            'apiKey': '',
            'baseUrl': 'https://api.openai.com/v1'
        },
        'baidu': {
            'apiKey': '',
            'secretKey': ''
        },
        'alibaba': {
            'apiKey': '',
            'baseUrl': ''
        }
    },
    'xueQiuCookie': config.get('xueQiuCookie', ''),
    'dailyLimit': config.get('dailyLimit', 60),
    'delayMin': config.get('delayMin', 30),
    'delayMax': config.get('delayMax', 120),
    'testMode': config.get('testMode', False)
}

# 保存新配置
with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(new_config, f, ensure_ascii=False, indent=2)

print('配置文件已转换为新格式')
print(f'火山引擎API Key: {new_config["models"]["ark"]["apiKey"]}')
