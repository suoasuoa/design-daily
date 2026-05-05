#!/usr/bin/env python3
"""
Design Daily — 数据积累器
=========================
每天3次从 RSS + G-Mark API 抓取新数据，去重合并到 brand_pool.json。
不依赖 Playwright，可以在 GitHub Actions 中直接运行。

用法:
  python3 accumulate.py               # 默认模式：积累新数据
  python3 accumulate.py --dry-run     # 预览：只打印新数据条数，不写入
"""

import json, os, re, sys, ssl, hashlib, datetime
from xml.etree import ElementTree
from collections import defaultdict

import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POOL_PATH = os.path.join(BASE_DIR, "brand_pool.json")

# 宽松的 SSL 上下文（在 macOS 和 GH Actions 上都能用）
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# ─── 品类关键词映射 ─────────────────────────────────────
# key: 品类名
# value: (must_keywords, any_keywords, exclude_keywords)
#   must_keywords: 标题必须包含这些词（优先级高）
#   any_keywords:   标题包含任意一个即可
#   exclude_keywords: 排除包含这些词的结果

CATEGORY_RULES = [
    ("创意礼盒", {
        "any": ["stationery", "文具", "pen", "pencil", "notebook", "note book",
                "planner", "desk accessory", "paper", "journal", "办公用品",
                "letter", "envelope", "stamp", "fountain", "sketchbook",
                "胶带", "贴纸", "便签", "订书机", "剪刀", "stationary"],
        "exclude": ["digital", "app", "software", "game", "music"]
    }),
    ("创意厨具", {
        "any": ["kitchen", "cookware", "cooking", "pan", "pot", "knife", "cutlery",
                "utensil", "chef", "kitchen tool", "kitchenware", "cutting board",
                "chef's", "cook", "bakeware", "baking", "rolling pin", "砧板",
                "厨具", "刀具", "锅", "菜板", "厨房"],
        "exclude": ["toy", "kids", "children"]
    }),
    ("氛围灯", {
        "any": ["lamp", "lighting", "light", "lantern", "chandelier", "sconce",
                "glow", "ambient", "floor lamp", "table lamp", " pendant ",
                "luminaires", "luminaire", "light fixture", "bulb", "LED",
                "台灯", "落地灯", "吊灯", "氛围灯", "灯泡"],
        "exclude": ["phone", "photography", "camera", "flash"]
    }),
    ("水杯", {
        "any": ["cup", "mug", "water bottle", "glass", "tumbler", "flask",
                "drinkware", "teacup", "teapot", "coffee cup", "travel mug",
                "stainless steel bottle", "hydration", "保温杯", "水杯",
                "马克杯", "陶瓷杯", "玻璃杯", "水壶"],
        "exclude": ["wine", "whisky", "whiskey", "beer", "bottle opener",
                     "cleaning", "soap"]
    }),
    ("创意礼盒", {
        "any": ["gift box", "gift set", "packaging", "gift packaging",
                "gift bag", "礼盒", "包装", "礼品盒", "礼袋", "gift wrap",
                "bundle", "kit", "set", "collection", "series",
                "subscription box", "surprise box", "surprise bag",
                "advent calendar"],
        "exclude": ["tool kit", "tool set", "drill", "screwdriver",
                     "dinner set", "plate set"]
    }),
    ("装置艺术", {
        "any": ["installation", "sculpture", "art installation", "exhibit",
                "public art", "interactive art", "kinetic", "装置艺术",
                "雕塑", "installed", "immersive", "projection art",
                "light installation", "sound installation"],
        "exclude": ["digital art", "nft", "photography", "painting", "print"]
    }),
    ("充电宝", {
        "any": ["power bank", "battery pack", "portable charger",
                "magsafe battery", "charging", "充电宝", "移动电源",
                "wireless charger", "charger", "charging station",
                "power station"],
        "exclude": ["earphone", "headphone", "speaker", "phone", "tablet",
                     "watch", "laptop charger"]
    }),
    ("手机壳", {
        "any": ["phone case", "phone cover", "case for", "手机壳",
                "protective case", "cover for iphone", "cover for samsung"],
        "exclude": ["laptop case", "tablet case", "headphone case",
                     "drill case", "storage case", "bookcase", "watch case"]
    }),
    ("帽子", {
        "any": ["hat", "cap", "headwear", "beanie", "visor", "sun hat",
                "bucket hat", "baseball cap", "snapback", "帽子",
                "棒球帽", "渔夫帽", "毛线帽", "遮阳帽"],
        "exclude": ["bottle cap", "camera", "lens cap"]
    }),
    ("T恤", {
        "any": ["t-shirt", "tee shirt", "tshirt", "graphic tee",
                "t shirt", "cotton tee", "t-shirt", "短袖", "t恤"],
        "exclude": ["bed sheet", "curtain", "towel", "fabric"]
    }),
    ("卫衣", {
        "any": ["hoodie", "sweatshirt", "zip hoodie", "卫衣", "帽衫",
                "连帽卫衣", "pullover"],
        "exclude": []
    }),
    ("Polo衫", {
        "any": ["polo shirt", "polo", "polo neck", "golf shirt",
                "polo衫", "polo 衫"],
        "exclude": ["polo hat", "sport"]
    }),
    ("冲锋衣", {
        "any": ["jacket", "outdoor jacket", "rain jacket", "windbreaker",
                "shell jacket", "ski jacket", "mountain jacket",
                "冲锋衣", "夹克", "防风衣", "羽绒服", "down jacket",
                "softshell", "hardshell", "parka"],
        "exclude": ["earphone", "headphone", "speaker", "case", "phone"]
    }),
    ("收纳包", {
        "any": ["bag", "backpack", "organizer", "storage bag", "pouch",
                "tote", "messenger bag", "duffel", "背包", "收纳",
                "手袋", "手提袋", "shoulder bag", "crossbody",
                "腰包", "斜挎包", "洗漱包", "化妆包", "旅行袋",
                "收纳包", "托特包", "邮差包"],
        "exclude": ["plastic bag", "shopping bag", "tea bag"]
    }),
    ("卡包", {
        "any": ["card holder", "wallet", "card case", "card wallet",
                "卡包", "钱包", "名片夹", "信用卡夹", "钱夹",
                "business card", "card sleeve", "card carrier",
                "card slot", "card organizer"],
        "exclude": ["phone case", "phone cover", "watch", "sim card",
                     "sd card", "memory card"]
    }),
    ("日历", {
        "any": ["calendar", "desk calendar", "wall calendar",
                "planner", "日历", "月历", "年历", "台历",
                "挂历", "日历架", "日历本"],
        "exclude": ["advent calendar"]
    }),
    ("创意桌搭", {
        "any": ["desk", "monitor", "monitor arm", "desk lamp",
                "mouse pad", "mouse mat", "keyboard", "wrist rest",
                "monitor stand", "laptop stand", "desk shelf",
                "desk mat", "cable management", "桌搭", "桌面",
                "显示器支架", "键盘", "鼠标垫", "升降桌",
                "桌垫", "桌面收纳"],
        "exclude": ["dining", "coffee table", "dinner", "kitchen table"]
    }),
    ("钥匙扣水壶", {
        "any": ["keychain", "key ring", "key holder", "钥匙扣",
                "carabiner", "钥匙链", "钥匙圈"],
        "exclude": []
    }),
    ("中秋礼盒", {
        "any": ["mooncake", "mid autumn", "mid-autumn",
                "moon festival", "中秋", "月饼"],
        "exclude": []
    }),
    ("端午礼盒", {
        "any": ["zongzi", "dragon boat", "端午", "粽子"],
        "exclude": []
    }),
]


# ─── 选品评分模块 ──────────────────────────────────────
# 5 个维度，每项 0~10 分，总分 < 35 过滤
# 当前阶段：关键词规则初筛（文本评分占位）
# 后续阶段：接入 DeepSeek + Playwright 精细化评分

SCORE_DIMENSIONS = ["intuitive", "broad_appeal", "usefulness", "creativity", "emotional"]

SCORE_LABELS = {
    "intuitive": "直观度",
    "broad_appeal": "打击面",
    "usefulness": "实用性",
    "creativity": "创意价值",
    "emotional": "情绪价值",
}

# 各维度产品/描述关键词（匹配到任意一个即加分）
SCORE_HIGH = {
    "intuitive": [
        # 常见产品名词——有具体可见形态
        "cup", "mug", "bottle", "lamp", "light", "bag", "hat", "cap",
        "t-shirt", "hoodie", "sweatshirt", "chair", "table", "shelf",
        "clock", "watch", "wallet", "case", "keychain", "charger",
        "pen", "pencil", "calendar", "backpack", "speaker", "glass",
        "水杯", "杯子", "灯", "包", "帽子", "手机壳", "钱包", "灯",
        "马克杯", "保温杯", "背包", "时钟", "充电宝", "扬声器", "音箱",
        "pouch", "organizer", "tote", "kettle", "teapot", "mug",
    ],
    "broad_appeal": [
        # 大众高频产品——每个人都会用到的
        "cup", "bottle", "water", "bag", "hat", "t-shirt", "hoodie",
        "phone", "charger", "wallet", "keychain", "chair", "table",
        "lamp", "light", "clock", "pen", "pencil", "paper", "box",
        "packaging", "pack", "bag", "shoe", "jacket", "backpack",
        "水杯", "水瓶", "包", "帽子", "T恤", "手机", "充电器", "钱包",
        "灯", "灯", "椅子", "桌子", "笔", "本", "盒", "包装",
        "tea", "coffee", "水壶", "茶具", "水杯", "收纳",
    ],
    "usefulness": [
        # 实用相关的词——功能、便携、收纳、工具
        "organizer", "storage", "holder", "stand", "rack", "tool",
        "portable", "lightweight", "foldable", "adjustable", "compact",
        "kitchen", "cookware", "tool", "utensil", "container", "tray",
        "收纳", "整理", "支架", "座", "架", "工具", "便携", "折叠",
        "可调节", "多功能", "收纳盒", "置物架", "分格", "配",
        "built-in", "integrated", "reusable", "easy", "quick", "convenient",
        "多合一", "套装", "两用", "模块化", "模块",
    ],
    "creativity": [
        # 创意价值——奖项、创新词、有趣的设计描述
        "award", "award-winning", "award winning", "innovative", "unique",
        "creative", "original", "breakthrough", "patented", "design",
        "limited edition", "handcrafted", "handmade", "artisan",
        "iF design", "red dot", "good design", "winner", "gold",
        "奖", "获奖", "金奖", "iF", "创新", "独特", "创意",
        "recycled", "sustainable", "eco-friendly", "环保", "可持续",
        "collapsible", "transforms", "converts", "modular", "customizable",
        "minimalist", "modern", "organic", "natural", "sculptural",
    ],
    "emotional": [
        # 情绪价值——温馨、幽默、惊喜、美感
        "warm", "cozy", "cute", "fun", "funny", "delight", "playful",
        "surprising", "beautiful", "elegant", "charming", "sweet",
        "peaceful", "calm", "zen", "relax", "soothing", "gentle",
        "nostalgic", "retro", "vintage", "classic", "timeless",
        "温馨", "可爱", "有趣", "幽默", "惊喜", "温暖", "治愈",
        "治愈系", "暖心", "心动", "优雅", "精致", "美",
        "luxurious", "premium", "质感", "高级", "好看",
    ],
}

SCORE_LOW = {
    "intuitive": ["installation", "sculpture", "abstract", "conceptual",
                  "装置", "抽象"],
    "broad_appeal": ["industrial", "medical", "surgical", "laboratory",
                     "factory", "工业", "医疗", "实验室"],
    "usefulness": ["decorative", "ornamental", "sculpture", "art",
                   "装饰", "纯装饰"],
    "creativity": [],
    "emotional": [],
}


def score_item(title="", desc=""):
    """对产品进行5维评分，返回 {dim: score, total: int}
    
    每维默认 6 分（略高于中性），按关键词 ± 调整。
    过滤线：总分 < 35（5维 × 7 的平均水平）
    """
    text = (title + " " + desc).lower()
    scores = {}
    
    for dim in SCORE_DIMENSIONS:
        base = 6  # 默认中等偏上
        # 每命中一个 high 关键词 +1.5 分（最多+4分）
        high_hits = sum(1 for w in SCORE_HIGH[dim] if w.lower() in text)
        base += min(int(high_hits * 1.5), 4)
        # low 关键词 -1.5 分（最多-3分）
        low_hits = sum(1 for w in SCORE_LOW[dim] if w.lower() in text)
        base -= min(int(low_hits * 1.5), 3)
        # 钳制到 0-10
        scores[dim] = max(0, min(10, base))
    
    scores["total"] = sum(scores[d] for d in SCORE_DIMENSIONS)
    return scores


def score_to_emoji(total):
    """把总分转为 Emoji 标签"""
    if total >= 45: return "⭐"
    if total >= 40: return "👍"
    if total >= 35: return "✅"
    if total >= 27: return "👀"
    return "❌"


def guess_category(title, desc=""):
    """根据标题+描述关键词猜测品类"""
    text = (title + " " + desc).lower()
    
    # 1. 先试 must 规则
    for cat, rules in CATEGORY_RULES:
        if rules.get("must"):
            if all(k.lower() in text for k in rules["must"]):
                return cat
    
    # 2. any 关键词匹配
    best_cat = None
    best_score = 0
    
    for cat, rules in CATEGORY_RULES:
        score = 0
        for kw in rules.get("any", []):
            if kw.lower() in text:
                score += 1
        # 排除关键词
        excluded = False
        for ekw in rules.get("exclude", []):
            if ekw.lower() in text:
                excluded = True
                break
        if excluded:
            continue
        
        if score > best_score:
            best_score = score
            best_cat = cat
    
    if best_score >= 1 and best_cat:
        return best_cat
    
    return None


def fetch_rss(url):
    """抓取 RSS 并返回 item 列表"""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; DesignDigestBot/1.0)"
    })
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=20) as resp:
            raw = resp.read().decode(errors="replace")
    except Exception as e:
        print(f"  ⚠️  RSS 抓取失败: {url} → {type(e).__name__}")
        return []
    
    # 清理 XML 前导垃圾
    start = raw.find("<?xml")
    if start > 0:
        raw = raw[start:]
    elif start < 0:
        start = raw.find("<rss")
        if start > 0:
            raw = raw[start:]
    
    try:
        root = ElementTree.fromstring(raw)
    except Exception as e:
        print(f"  ⚠️  RSS 解析失败: {str(e)[:60]}")
        return []
    
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc_raw = item.findtext("description") or ""
        desc = re.sub(r"<[^>]+>", "", desc_raw).strip()[:200]
        pub_date = item.findtext("pubDate") or item.findtext("dc:date") or ""
        
        if title and len(title) > 5:
            items.append({
                "title": title[:80],
                "url": link,
                "desc": desc,
                "pub_date": pub_date,
            })
    
    return items


def rss_item_to_brand(item, source_name):
    """把 RSS item 转成 brand_pool 格式"""
    cat = guess_category(item["title"], item["desc"])
    if not cat:
        return None
    
    # 评分
    sc = score_item(item["title"], item["desc"])
    if sc["total"] < 35:
        return None  # 总分不足，过滤
    
    # 生成唯一 ID（用于去重）
    uid = hashlib.md5(f"{source_name}:{item['url']}".encode()).hexdigest()[:12]
    
    brand = {
        "id": uid,
        "title": item["title"],
        "reason": item["desc"][:200] or f"{source_name} · 精选设计文章",
        "source": source_name,
        "category": cat,
        "creator": source_name,
        "score": round(sc["total"] / 5, 1),  # 平均分转回 0-10 标尺
        "likes": 0,
        "url": item["url"],
        "image": "",
        "tags": [cat, source_name, "设计文章"],
        "added": datetime.date.today().isoformat(),
        # 保留评分明细（供后续分析用）
        "_scores": {SCORE_LABELS[d]: sc[d] for d in SCORE_DIMENSIONS},
        "_score_total": sc["total"],
    }
    return brand


def fetch_gmark(max_items=50):
    """从 G-Mark API 获取最新数据"""
    print(f"  🏆 G-Mark API...")
    
    gmark_cat_map = {
        "Kitchen & Cookware": "创意厨具",
        "Tableware": "创意厨具",
        "Lighting": "氛围灯",
        "Home Accessories": "收纳包",
        "Stationery": "创意礼盒",
        "Furniture": "创意桌搭",
        "Personal Accessories": "创意礼盒",
        "Home Electronics": "创意桌搭",
        "Sports & Hobbies": "冲锋衣",
        "Kids & Education": "创意礼盒",
        "Health & Beauty": "创意礼盒",
        "Smartphone": "手机壳",
        "Computer & Peripherals": "创意桌搭",
        "Audio Equipment": "创意厨具",
        "Camera": "收纳包",
        "Bath & Toilet": "水杯",
        "Bedding": "收纳包",
        "Garden & Outdoor": "冲锋衣",
        "Office Equipment": "创意桌搭",
        "Toy & Hobby": "创意礼盒",
    }
    
    seen_urls = set()
    items = []
    
    for year in [2025, 2024]:
        page = 1
        while len(items) < max_items:
            url = f"https://g-mark.io/api/award/winners?page={page}&size=100&years={year}"
            req = urllib.request.Request(url, headers={"Accept": "*/*"})
            try:
                with urllib.request.urlopen(req, context=CTX, timeout=15) as resp:
                    data = json.loads(resp.read())
            except Exception as e:
                print(f"    ⚠️  G-Mark page {page}: {type(e).__name__}")
                break
            
            hits = data.get("_embedded", {}).get("searchHitList", [])
            if not hits:
                break
            
            for hit in hits:
                c = hit["content"]
                gm_cat = ((c.get("winnerCategory") or {}).get("name") or {}).get("en", "")
                mapped = gmark_cat_map.get(gm_cat)
                if not mapped:
                    continue  # 只保留能映射到19品类的
                
                proper = (c.get("properName") or {}).get("en", "") or \
                         (c.get("properName") or {}).get("ja", "") or \
                         (c.get("generalName") or {}).get("en", "") or "Unknown"
                
                company = (c.get("businessOwner") or {}).get("en", "") or ""
                
                uid = c.get("id", "")
                if uid in seen_urls:
                    continue
                seen_urls.add(uid)
                
                img = f"https://award-attachments.g-mark.io/winners/{c['year']}/{uid}/main.jpg?size=medium"
                
                # 评分
                sc = score_item(proper, f"{gm_cat} {company} {c.get('outline','')}")
                if sc["total"] < 35:
                    continue  # 过滤低分
                
                items.append({
                    "title": proper[:80],
                    "reason": f"Good Design Award · {gm_cat} · {company}"[:200],
                    "source": "Good Design Award",
                    "category": mapped,
                    "creator": company or "Good Design Award",
                    "score": round(sc["total"] / 5, 1),
                    "likes": 0,
                    "url": f"https://www.g-mark.org/gallery/winners/{uid}?years={c['year']}",
                    "image": img,
                    "tags": [mapped, "Good Design Award", "获奖设计"],
                    "added": datetime.date.today().isoformat(),
                    "_scores": {SCORE_LABELS[d]: sc[d] for d in SCORE_DIMENSIONS},
                    "_score_total": sc["total"],
                })
            
            total_pages = data.get("page", {}).get("totalPages", 1)
            if page >= total_pages:
                break
            page += 1
    
    print(f"    ✅ 获取 {len(items)} 条（匹配19品类）")
    return items


def load_pool():
    """加载现有品牌池"""
    if not os.path.exists(POOL_PATH):
        print(f"  ⚠️  brand_pool.json 不存在，创建空池")
        return []
    with open(POOL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pool(pool):
    """保存品牌池"""
    with open(POOL_PATH, "w", encoding="utf-8") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)


def main():
    dry_run = "--dry-run" in sys.argv
    
    print(f"📥 Design Daily — 数据积累器")
    print(f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    # 加载现有池
    pool = load_pool()
    existing_urls = set()
    existing_titles = set()
    existing_gmark_ids = set()  # 提取 G-Mark 奖项ID用于去重
    for item in pool:
        if item.get("url"):
            existing_urls.add(item["url"])
            # 提取 G-Mark 奖项 ID
            if "g-mark.org/gallery/winners/" in item["url"]:
                import re
                m = re.search(r'/winners/(\d+)', item["url"])
                if m:
                    existing_gmark_ids.add(m.group(1))
        existing_titles.add(item.get("title", "").lower().strip())
    
    print(f"📊 当前品牌池: {len(pool)} 条")
    print()
    
    all_new = []
    
    # ─── RSS 源 ───────────────────────────────
    print("━━━ RSS 设计博客 ━━━")
    rss_feeds = [
        ("Design Milk", "https://feeds.feedburner.com/design-milk"),
        ("Dezeen", "https://www.dezeen.com/design/feed/"),
        ("Yanko Design", "https://www.yankodesign.com/feed/"),
    ]
    
    for name, url in rss_feeds:
        articles = fetch_rss(url)
        if not articles:
            print(f"  📰 {name}: 无数据")
            continue
        
        matched = 0
        skipped = 0
        for art in articles:
            # 去重
            if art["url"] in existing_urls:
                continue
            if art["title"].lower().strip() in existing_titles:
                continue
            
            brand = rss_item_to_brand(art, name)
            if brand:
                all_new.append(brand)
                existing_urls.add(brand["url"])
                existing_titles.add(brand["title"].lower().strip())
                matched += 1
            else:
                skipped += 1
        
        print(f"  📰 {name}: {len(articles)}条 → 新增{matched}条, 跳过{skipped}条(品类不匹配)")
    
    # ─── G-Mark ───────────────────────────────
    print("\n━━━ Good Design Award ━━━")
    gmark_items = fetch_gmark(max_items=250)
    gmark_new = 0
    for item in gmark_items:
        if item["url"] in existing_urls:
            continue
        # 按奖项ID去重（防止URL格式差异）
        import re
        mid = re.search(r'/winners/(\d+)', item["url"])
        if mid and mid.group(1) in existing_gmark_ids:
            continue
        all_new.append(item)
        existing_urls.add(item["url"])
        if mid:
            existing_gmark_ids.add(mid.group(1))
        gmark_new += 1
    print(f"  🏆 G-Mark: {len(gmark_items)}条 → 新增{gmark_new}条")
    
    # ─── 结果 ───────────────────────────────
    print(f"\n{'='*40}")
    print(f"📊 本次新增: {len(all_new)} 条")
    
    # 品类分布
    cat_count = defaultdict(int)
    for item in all_new:
        cat_count[item["category"]] += 1
    print("\n品类分布:")
    for c, n in sorted(cat_count.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")
    
    # 评分分布
    if all_new:
        score_buckets = {"⭐ ≥45": 0, "👍 40-44": 0, "✅ 35-39": 0}
        for item in all_new:
            total = item.get("_score_total", 40)
            if total >= 45:
                score_buckets["⭐ ≥45"] += 1
            elif total >= 40:
                score_buckets["👍 40-44"] += 1
            else:
                score_buckets["✅ 35-39"] += 1
        print(f"\n评分分布:")
        for label, n in score_buckets.items():
            bar = "█" * max(1, n * 40 // max(1, max(score_buckets.values())))
            print(f"  {label}: {n:>4}  {bar}")
    
    if dry_run:
        print(f"\n🔍 预览模式，不写入")
        return
    
    if not all_new:
        print(f"\nℹ️  无新数据，跳过写入")
        return
    
    # 合并到池
    pool.extend(all_new)
    save_pool(pool)
    
    print(f"\n✅ 合并完成!")
    print(f"📁 品牌池: {len(pool)} 条 (新增 {len(all_new)})")
    
    # 来源统计
    src_count = defaultdict(int)
    for item in pool:
        src_count[item.get("source", "未知")] += 1
    print("来源分布:")
    for s, n in sorted(src_count.items(), key=lambda x: -x[1]):
        print(f"  {s}: {n}")


if __name__ == "__main__":
    main()
