#!/usr/bin/env python3
"""🎭 Playwright 爬虫 —— 小红书/抖音（需登录平台）
用浏览器 Cookie 登录后抓取实际搜索内容

使用方法：
  1. 先确保 cookies.json 里有最新的 Cookie（通过控制面板更新）
  2. python3 scrape_playwright.py --xhs "搜索关键词"
  3. python3 scrape_playwright.py --dy "搜索关键词"

输出: data/目录下的 JSON 文件
"""
import json, os, re, sys
from datetime import datetime
from playwright.sync_api import sync_playwright
import time, random

DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(DIR, 'data')
COOKIE_FILE = os.path.join(DIR, 'cookies.json')
os.makedirs(DATA, exist_ok=True)

# 搜索关键词配置
CATEGORIES = {
    "水杯": ["创意水杯设计", "马克杯设计", "ins水杯"],
    "创意厨具": ["厨房设计好物", "创意厨具厨房神器"],
    "卡包": ["卡包设计", "极简卡包", "创意卡包"],
    "收纳包": ["收纳包设计", "创意收纳神器"],
    "钥匙扣水壶": ["便携水壶设计", "户外水壶推荐"],
    "氛围灯": ["氛围灯设计", "创意台灯灯具"],
    "日历": ["创意日历设计", "桌面日历推荐"],
    "冲锋衣": ["冲锋衣设计", "户外冲锋衣推荐"],
    "帽子": ["帽子设计", "棒球帽设计"],
    "T恤": ["T恤设计", "印花T恤创意"],
    "卫衣": ["卫衣设计", "连帽卫衣设计"],
    "Polo衫": ["Polo衫设计", "polo衫推荐"],
    "充电宝": ["充电宝设计", "便携充电宝推荐"],
    "手机壳": ["手机壳设计", "创意手机壳"],
    "创意桌搭": ["桌面搭建设计", "创意桌搭好物"],
}

def load_cookies():
    with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def scrape_xhs(keywords, max_items=10):
    """小红书搜索 + 提取笔记内容"""
    cookies = load_cookies()['xiaohongshu']
    all_items = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1440, 'height': 900},
            locale='zh-CN',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        # 监听 API 响应
        api_results = []
        def on_response(response):
            if 'edith.xiaohongshu.com/api' in response.url:
                try:
                    body = response.json()
                    flat = json.dumps(body, ensure_ascii=False)
                    if 'display_title' in flat or 'note_card' in flat:
                        api_results.append(body)
                except:
                    pass
        
        page.on('response', on_response)
        
        for kw in keywords:
            try:
                # 先访问首页注入 Cookie
                page.goto('https://www.xiaohongshu.com', wait_until='domcontentloaded', timeout=15000)
                time.sleep(1)
                
                for c in cookies:
                    n, v = c['name'].replace("'","\\'"), c['value'].replace("'","\\'")
                    try:
                        page.evaluate(f"document.cookie = '{n}={v}; path=/; domain={c['domain']}'")
                    except: pass
                
                time.sleep(0.5)
                
                # 搜索
                encoded = ''.join(f'%{hex(ord(c))[2:].upper()}' for c in kw)
                page.goto(f'https://www.xiaohongshu.com/search_result?keyword={encoded}',
                          wait_until='domcontentloaded', timeout=20000)
                
                # 等待 JS 渲染内容
                time.sleep(5)
                
                # 滚动以触发加载
                for _ in range(3):
                    page.evaluate('window.scrollBy(0, 500)')
                    time.sleep(1)
                
                # 提取页面中的笔记标题
                page_text = page.inner_text('body')
                
                # 从 API 响应中提取
                if api_results:
                    items_from_api = extract_xhs_from_api(api_results)
                    all_items.extend(items_from_api)
                    api_results.clear()
                    print(f'  📌 {kw}: {len(items_from_api)} 条 (API)')
                    if len(all_items) >= max_items:
                        break
                    continue
                
                # 从页面文本提取
                items_from_page = extract_xhs_from_text(page_text)
                all_items.extend(items_from_page)
                print(f'  📌 {kw}: {len(items_from_page)} 条 (page)')
                
            except Exception as e:
                print(f'  ❌ {kw}: {str(e)[:50]}')
            
            time.sleep(random.uniform(1, 2))
            if len(all_items) >= max_items:
                break
        
        browser.close()
    
    return all_items

def extract_xhs_from_api(api_results):
    """从小红书 API 响应中提取笔记"""
    items = []
    for body in api_results:
        if not isinstance(body, dict):
            continue
        flat = json.dumps(body, ensure_ascii=False)
        
        # 尝试找笔记卡片
        for record in [body]:
            data = record
            # 搜嵌套
            def find_notes(obj, depth=0):
                if depth > 3:
                    return []
                found = []
                if isinstance(obj, dict):
                    # 检查是不是笔记
                    if 'display_title' in obj:
                        found.append(obj)
                    for v in obj.values():
                        found.extend(find_notes(v, depth + 1))
                elif isinstance(obj, list):
                    for v in obj:
                        found.extend(find_notes(v, depth + 1))
                return found
            
            notes = find_notes(record)
            for note in notes:
                title = note.get('display_title', '') or note.get('title', '') or ''
                note_id = note.get('id', '') or note.get('note_id', '') or ''
                user = note.get('user', {})
                if isinstance(user, dict):
                    author = user.get('nickname', '') or user.get('nick_name', '')
                else:
                    author = ''
                
                if title:
                    note_url = f'https://www.xiaohongshu.com/explore/{note_id}' if note_id else ''
                    items.append({
                        'title': title[:80],
                        'url': note_url,
                        'reason': f'小红书热门 · {title[:40]}',
                        'source': '小红书',
                        'creator': author or '小红书用户',
                        'score': 7.5,
                        'tags': ['小红书', '热门推荐']
                    })
    
    return items

def extract_xhs_from_text(page_text):
    """从页面文本中提取笔记"""
    items = []
    # 找长的标题行
    lines = page_text.split('\n')
    for line in lines:
        line = line.strip()
        if len(line) > 6 and len(line) < 80 and not any(k in line for k in ['首页', '关注', '推荐', '搜索', '登录', '注册', 'Copyright', '©', '京ICP']):
            # 看起来像标题
            items.append({
                'title': line[:80],
                'url': 'https://www.xiaohongshu.com',
                'reason': f'小红书设计推荐 · {line[:30]}',
                'source': '小红书',
                'creator': '小红书用户',
                'score': 7.5,
                'tags': ['小红书', '热门推荐']
            })
    
    # 去重
    seen = set()
    deduped = []
    for item in items:
        key = item['title'][:20]
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    
    return deduped[:8]

def scrape_douyin(keywords, max_items=10):
    """抖音搜索"""
    cookies = load_cookies()['douyin']
    all_items = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1440, 'height': 900},
            locale='zh-CN',
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        for kw in keywords:
            try:
                # 首页注入 Cookie
                page.goto('https://www.douyin.com', wait_until='domcontentloaded', timeout=15000)
                time.sleep(1)
                
                for c in cookies:
                    n, v = c['name'].replace("'","\\'"), c['value'].replace("'","\\'")
                    try:
                        page.evaluate(f"document.cookie = '{n}={v}; path=/; domain={c['domain']}'")
                    except: pass
                
                time.sleep(0.5)
                
                # 搜索
                encoded = ''.join(f'%{hex(ord(c))[2:].upper()}' for c in f'{kw} 设计')
                page.goto(f'https://www.douyin.com/search/{encoded}?type=general',
                          wait_until='domcontentloaded', timeout=20000)
                time.sleep(5)
                
                # 滚动
                for _ in range(3):
                    page.evaluate('window.scrollBy(0, 500)')
                    time.sleep(1)
                
                # 提取内容
                body = page.inner_text('body')
                lines = [l.strip() for l in body.split('\n') if len(l.strip()) > 4]
                non_ui_lines = [l for l in lines if not any(k in l for k in [
                    '抖音', '搜索', '登录', '注册', '关注', '精选', '推荐', 
                    '直播', '京ICP', 'Copyright', '©', '广告投放', '协议', '隐私'
                ])]
                
                for l in non_ui_lines[:5]:
                    all_items.append({
                        'title': l[:80],
                        'url': 'https://www.douyin.com',
                        'reason': f'抖音设计 · {l[:30]}',
                        'source': '抖音',
                        'creator': '抖音创作者',
                        'score': 7.0,
                        'tags': ['抖音']
                    })
                
                print(f'  📌 {kw}: {len(non_ui_lines)} 条')
                
            except Exception as e:
                print(f'  ❌ {kw}: {str(e)[:50]}')
            
            time.sleep(random.uniform(1, 2))
            if len(all_items) >= max_items:
                break
        
        browser.close()
    
    return all_items


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Playwright 爬虫')
    parser.add_argument('--xhs', help='小红书关键词')
    parser.add_argument('--dy', help='抖音关键词')
    parser.add_argument('--all', action='store_true', help='扫描所有品类')
    args = parser.parse_args()
    
    if args.all:
        print('🎭 Playwright 全品类扫描...')
        
        # 小红书扫描
        print('\n━━━ 小红书扫描 ━━━')
        all_xhs = []
        for cat, kws in list(CATEGORIES.items())[:5]:  # 先试5个品类
            print(f'\n🔍 {cat}:')
            items = scrape_xhs(kws, max_items=5)
            for item in items:
                item['category'] = cat
            all_xhs.extend(items)
            time.sleep(2)
        
        # 抖音扫描 (先2个)
        print('\n━━━ 抖音扫描 ━━━')
        all_dy = []
        for cat, kws in list(CATEGORIES.items())[:3]:
            print(f'\n🔍 {cat}:')
            items = scrape_douyin(kws, max_items=3)
            for item in items:
                item['category'] = cat
            all_dy.extend(items)
            time.sleep(2)
        
        # 合并保存
        all_items = all_xhs + all_dy
        print(f'\n✅ 总计 {len(all_items)} 条')
        
        with open(os.path.join(DATA, 'playwright_results.json'), 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        
    elif args.xhs:
        items = scrape_xhs([args.xhs], max_items=20)
        print(f'\n✅ 小红书: {len(items)} 条')
        for item in items[:5]:
            print(f'  📌 {item["title"][:50]}')
    
    elif args.dy:
        items = scrape_douyin([args.dy], max_items=20)
        print(f'\n✅ 抖音: {len(items)} 条')
        for item in items[:5]:
            print(f'  📌 {item["title"][:50]}')
    
    else:
        print('用法:')
        print('  python3 scrape_playwright.py --xhs "水杯设计"')
        print('  python3 scrape_playwright.py --dy "杯子设计"')
        print('  python3 scrape_playwright.py --all')


if __name__ == '__main__':
    main()
