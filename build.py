#!/usr/bin/env python3
"""Build generate.py: brand items + spider code"""
import json

# 1. 读取品牌数据
with open('/Users/xuebao/.openclaw/workspace/design-daily/data/latest.json') as f:
    d = json.load(f)
brands_json = json.dumps(d['items'], ensure_ascii=False, indent=2)

# 2. 读头部（去掉 BRAND_ITEMS = [] 这一行）
with open('/Users/xuebao/.openclaw/workspace/design-daily/generate_head.py') as f:
    head = f.read()

# 3. 拼接：head + "BRAND_ITEMS = " + JSON + spider
full = head + 'BRAND_ITEMS = ' + brands_json + '\n'

with open('/Users/xuebao/.openclaw/workspace/design-daily/spider_code.py') as f:
    spider = f.read()
full += spider

with open('/Users/xuebao/.openclaw/workspace/design-daily/generate.py', 'w') as f:
    f.write(full)

print(f'generate.py: {len(full)} chars, {len(d["items"])} items')
