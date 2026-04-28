#!/usr/bin/env python3
"""🎭 选项2：Chrome CDP 模式连接抓取
你保持 Chrome 打开小红书/抖音，我连接你的真实浏览器抓取数据

使用方法：
  1. 先关闭所有 Chrome
  2. 终端运行（你的 Mac 上）：
     /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
  
  3. 然后运行这个脚本：
     python3 cdp_scraper.py --xhs "水杯设计"
"""
import json, os, sys, time, re, random
from datetime import datetime
from playwright.sync_api import sync_playwright

DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(DIR, 'data')
os.makedirs(DATA, exist_ok=True)

def connect_chrome(port=9222):
    """连接到本地已打开的 Chrome 实例"""
    p = sync_playwright()
    p.start()
    browser = p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
    return p, browser

def list_tabs(browser):
    """列出所有已打开的标签页"""
    contexts = browser.contexts
    all_pages = []
    for ctx in contexts:
        all_pages.extend(ctx.pages)
    return all_pages

def find_xhs_tab(browser):
    """找小红书标签页"""
    for page in list_tabs(browser):
        if 'xiaohongshu' in page.url:
            return page
    return None

def find_dy_tab(browser):
    """找抖音标签页"""
    for page in list_tabs(browser):
        if 'douyin' in page.url:
            return page
    return None

def scrape_xhs_from_page(page, keyword, max_items=10):
    """从小红书已登录页面提取搜索结果"""
    print(f'\n🔍 搜索: {keyword}')
    
    # 直接导航到搜索
    encoded = ''.join(f'%{hex(ord(c))[2:].upper()}' for c in keyword)
    page.goto(f'https://www.xiaohongshu.com/search_result?keyword={encoded}', 
              wait_until='domcontentloaded', timeout=20000)
    
    items = []
    all_requests = []
    
    def on_response(response):
        url = response.url
        if '/api/sns/web/' in url:
            try:
                body = response.json()
                all_requests.append({'url': url, 'data': body})
            except:
                pass
    
    page.on('response', on_response)
    
    time.sleep(5)
    
    # 滚动加载
    for _ in range(5):
        page.evaluate('window.scrollBy(0, 800)')
        time.sleep(1)
    
    # 从 API 响应中解析
    for req in all_requests:
        body = req['data']
        flat = json.dumps(body, ensure_ascii=False)
        
        # 找笔记
        def find_notes(obj, depth=0):
            if depth > 4:
                return []
            found = []
            if isinstance(obj, dict):
                if 'display_title' in obj or 'title' in obj:
                    found.append(obj)
                for v in obj.values():
                    found.extend(find_notes(v, depth + 1))
            elif isinstance(obj, list):
                for v in obj:
                    found.extend(find_notes(v, depth + 1))
            return found
        
        notes = find_notes(body)
        for note in notes:
            title = note.get('display_title', '') or note.get('title', '') or ''
            note_id = note.get('id', '') or note.get('note_id', '') or ''
            user = note.get('user', {})
            author = user.get('nickname', '') if isinstance(user, dict) else ''
            img = note.get('cover', {}) or note.get('image', '') or ''
            cover_url = img.get('url', '') if isinstance(img, dict) else (img if isinstance(img, str) else '')
            
            if title:
                note_url = f'https://www.xiaohongshu.com/explore/{note_id}' if note_id else ''
                items.append({
                    'title': title[:80],
                    'url': note_url,
                    'image': cover_url[:200] if cover_url else '',
                    'reason': f'小红书热门 · {title[:30]}',
                    'source': '小红书',
                    'creator': author or '小红书用户',
                    'score': 7.5,
                    'tags': ['小红书', '热门推荐']
                })
    
    # 如果 API 没抓到，从页面文本爬
    if not items:
        page_text = page.inner_text('body')
        lines = [l.strip() for l in page_text.split('\n') if 6 < len(l.strip()) < 60]
        non_ui = [l for l in lines if not any(k in l for k in [
            '首页', '搜索', '登录', '注册', '©', '京ICP', '电话', '地址', '协议'
        ])]
        for l in non_ui[:max_items]:
            items.append({
                'title': l[:80],
                'url': page.url,
                'reason': f'小红书 · {l[:30]}',
                'source': '小红书',
                'creator': '小红书用户',
                'score': 7.0,
                'tags': ['小红书']
            })
    
    # 去重
    seen = set()
    deduped = []
    for item in items:
        key = item.get('url', '') or item['title'][:20]
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    
    print(f'  找到 {len(deduped)} 条')
    return deduped[:max_items]

def scrape_dy_from_page(page, keyword, max_items=10):
    """从抖音已登录页面提取搜索结果"""
    print(f'\n🔍 抖音搜索: {keyword}')
    
    encoded = ''.join(f'%{hex(ord(c))[2:].upper()}' for c in keyword)
    page.goto(f'https://www.douyin.com/search/{encoded}?type=general',
              wait_until='domcontentloaded', timeout=20000)
    time.sleep(5)
    
    # 滚动
    for _ in range(3):
        page.evaluate('window.scrollBy(0, 800)')
        time.sleep(1)
    
    body = page.inner_text('body')
    lines = [l.strip() for l in body.split('\n') if 4 < len(l.strip()) < 80]
    non_ui = [l for l in lines if not any(k in l for k in [
        '抖音', '搜索', '登录', '注册', '精选', '推荐', '直播', '京ICP', '©', '广告'
    ])]
    
    items = []
    for l in non_ui[:max_items]:
        items.append({
            'title': l[:80],
            'url': page.url,
            'reason': f'抖音设计 · {l[:30]}',
            'source': '抖音',
            'creator': '抖音创作者',
            'score': 7.0,
            'tags': ['抖音']
        })
    
    print(f'  找到 {len(items)} 条')
    return items

def save_items(items, source_name):
    """保存到 data/ 目录并合并"""
    src_file = os.path.join(DATA, f'source_{source_name}.json')
    existing = []
    if os.path.exists(src_file):
        with open(src_file, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    
    existing_urls = set(i.get('url','')+i.get('title','')[:30] for i in existing)
    new = [i for i in items if (i.get('url','')+i.get('title','')[:30]) not in existing_urls]
    combined = existing + new
    
    with open(src_file, 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    
    print(f'  💾 {source_name}: {len(new)} 条新增, {len(combined)} 条总计')
    return new


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--xhs', help='小红书关键词，逗号分隔')
    parser.add_argument('--dy', help='抖音关键词，逗号分隔')
    parser.add_argument('--port', type=int, default=9222, help='Chrome 调试端口')
    args = parser.parse_args()
    
    print('🚀 连接你的 Chrome 浏览器...')
    print('   请先运行: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222')
    print('   并确保已登录小红书和抖音\n')
    
    p, browser = connect_chrome(args.port)
    
    try:
        tabs = list_tabs(browser)
        print(f'📑 已打开 {len(tabs)} 个标签页')
        
        # 找小红书
        xhs_page = find_xhs_tab(browser)
        dy_page = find_dy_tab(browser)
        
        if xhs_page:
            print(f'✅ 找到小红书: {xhs_page.url[:60]}')
        if dy_page:
            print(f'✅ 找到抖音: {dy_page.url[:60]}')
        
        if args.xhs and xhs_page:
            kws = [k.strip() for k in args.xhs.split(',')]
            for kw in kws:
                items = scrape_xhs_from_page(xhs_page, kw)
                save_items(items, '小红书')
                time.sleep(2)
        
        if args.dy and dy_page:
            kws = [k.strip() for k in args.dy.split(',')]
            for kw in kws:
                items = scrape_dy_from_page(dy_page, kw)
                save_items(items, '抖音')
                time.sleep(2)
        
        if not args.xhs and not args.dy:
            print('\n用法示例:')
            print('  python3 cdp_scraper.py --xhs "水杯设计,收纳包"')
            print('  python3 cdp_scraper.py --dy "杯子设计"')
            print('  python3 cdp_scraper.py --xhs "水杯" --dy "水杯"')
    
    finally:
        browser.close()
        p.stop()

if __name__ == '__main__':
    main()
