
# ======================================================================
# 网络爬虫：随机UA + 重试机制 + 多级降级提取
# ======================================================================

import urllib.parse, time

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

def rnd_ua():
    return USER_AGENTS[random.randint(0, len(USER_AGENTS) - 1)]


def fetch_url(url, timeout=8, retries=2):
    """抓取URL，支持重试和随机UA"""
    last_err = ""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': rnd_ua(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            })
            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            return resp.read(300000).decode('utf-8', errors='ignore')
        except Exception as e:
            last_err = str(e)[:60]
            if attempt < retries:
                time.sleep(1 + random.random())
    print(f"    \u26a0\ufe0f fetch失败(重试{retries}次): {url[:50]}... {last_err}")
    return None


def safe_og_image(url, timeout=6):
    """获取OG图片: og:image > twitter:image > 首张img"""
    try:
        html = fetch_url(url, timeout=timeout, retries=1)
        if not html:
            return ""
        # Level 1: og:image (property)
        m = re.search(r'<meta[^>]+property=[\"'']og:image[\"''][^>]+content=[\"'']([^\"'']+)[\"'']', html)
        if m: return m.group(1)
        # Level 2: og:image reversed attr
        m = re.search(r'<meta[^>]+content=[\"'']([^\"'']+)[\"''][^>]+property=[\"'']og:image[\"'']', html)
        if m: return m.group(1)
        # Level 3: twitter:image
        m = re.search(r'<meta[^>]+name=[\"'']twitter:image[\"''][^>]+content=[\"'']([^\"'']+)[\"'']', html)
        if m: return m.group(1)
        # Level 4: first img
        m = re.search(r'<img[^>]+src=[\"'']([^\"'']+)[\"''][^>]*>', html)
        if m:
            img = m.group(1)
            if img.startswith("//"): img = "https:" + img
            if img.startswith("http"): return img
        return ""
    except:
        return ""


# ======================================================================
# Pinterest 爬虫：多级降级提取
# ======================================================================

PINTEREST_KW = [
    ("creative cup design","水杯"),("ambient light design","氛围灯"),
    ("kitchen design ideas","创意厨具"),("desk organizer ideas","创意桌搭"),
    ("hat design ideas","帽子"),("sweatshirt design","卫衣"),
    ("t-shirt design","T恤"),("polo shirt design","Polo衫"),
    ("gift box packaging","创意礼盒"),("mooncake packaging","中秋礼盒"),
    ("dragon boat gift","端午礼盒"),("art installation","装置艺术"),
    ("phone case art","手机壳"),("power bank design","充电宝"),
    ("card holder","卡包"),("calendar design","日历"),
    ("water bottle design","钥匙扣水壶"),("rain jacket","冲锋衣"),
    ("storage organizer","收纳包"),("tea set design","水杯"),
]

def scrape_pinterest(max_total=60):
    results = []
    seen = set()
    for kw, cat in PINTEREST_KW:
        if len(results) >= max_total:
            break
        url = f"https://www.pinterest.com/search/pins/?q={urllib.parse.quote(kw)}"
        html = fetch_url(url)
        if not html:
            continue
        pins = set()
        # Level 1: JSON-LD
        for m in re.finditer(r'<script[^>]*type=[\"'']application/ld\+json[\"''][^>]*>(.*?)</script>', html, re.DOTALL):
            try:
                ld = json.loads(m.group(1))
                if isinstance(ld, dict):
                    for key in ("name", "headline"):
                        val = ld.get(key, "")
                        if isinstance(val, str) and len(val) > 5 and val not in seen:
                            pins.add(val)
                elif isinstance(ld, list):
                    for item in ld:
                        if isinstance(item, dict):
                            val = item.get("name", "")
                            if isinstance(val, str) and len(val) > 5 and val not in seen:
                                pins.add(val)
            except:
                pass
        # Level 2: pin_title
        for m in re.finditer(r'\"pin_title\":\"([^\"]+)\"', html):
            t = m.group(1)
            if len(t) > 4 and t not in seen:
                pins.add(t)
        # Level 3: alt text
        for m in re.finditer(r'<img[^>]+alt=[\"'']([^\"'']+)[\"'']', html):
            alt = m.group(1)
            if len(alt) > 8 and len(alt) < 80 and alt not in seen:
                pins.add(alt)
        if pins:
            print(f"    \U0001f4cc Pinterest [{kw}]: {len(pins)} 条")
        for title in list(pins)[:8]:
            clean = title.replace("\\u0026", "&").replace("\\n", " ")[:45]
            if clean in seen:
                continue
            seen.add(clean)
            score = 7.5 + (random.random() - 0.3) * 0.8
            results.append({
                "title": f"Pinterest \u00b7 {clean}",
                "category": cat,
                "desc": f"来自Pinterest的设计灵感: {title[:60]}",
                "url": f"https://www.pinterest.com/search/pins/?q={urllib.parse.quote(title[:30])}",
                "source": "Pinterest", "likes": random.randint(300, 3000),
                "score": round(min(score, 9.3), 1), "creator": "Pinterest",
                "tags": [cat, "Pinterest", "社交精选"], "image": ""
            })
    return results


# ======================================================================
# Behance 爬虫：多级降级提取
# ======================================================================

BEHANCE_KW = [
    ("packaging design","创意礼盒"),("industrial design","创意礼盒"),
    ("water bottle design","水杯"),("lighting design","氛围灯"),
    ("desk organizer","创意桌搭"),("streetwear","卫衣"),
    ("t-shirt graphic","T恤"),("art installation","装置艺术"),
    ("phone case","手机壳"),("power bank","充电宝"),
    ("wallet design","卡包"),("calendar design","日历"),
    ("kitchen design","创意厨具"),("festival packaging","中秋礼盒"),
    ("gift box","创意礼盒"),("minimalist product","创意礼盒"),
    ("outdoor jacket","冲锋衣"),("polo shirt","Polo衫"),
    ("hat collection","帽子"),("storage design","收纳包"),
]

def scrape_behance(max_total=40):
    results = []
    seen = set()
    for kw, cat in BEHANCE_KW:
        if len(results) >= max_total:
            break
        url = f"https://www.behance.net/search/projects/?search={urllib.parse.quote(kw)}"
        html = fetch_url(url)
        if not html:
            continue
        projects = set()
        # Level 1: projectName (API JSON)
        for m in re.finditer(r'\"projectName\":\"([^\"]+)\"', html):
            name = m.group(1)
            if len(name) > 4 and name not in seen:
                projects.add(name)
        # Level 2: ProjectCoverNeue-title (SSR)
        for m in re.finditer(r'ProjectCoverNeue-title[^>]*>(.*?)<', html):
            name = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if len(name) > 4 and name not in seen:
                projects.add(name)
        if projects:
            print(f"    \U0001f3af Behance [{kw}]: {len(projects)} 条")
        for name in list(projects)[:6]:
            clean = name.replace("\\u0026", "&").replace("\\n", " ")[:45]
            if clean in seen:
                continue
            seen.add(clean)
            score = 7.3 + (random.random() - 0.3) * 0.7
            results.append({
                "title": f"Behance \u00b7 {clean}",
                "category": cat,
                "desc": f"来自Behance的设计项目: {name[:60]}",
                "url": url,
                "source": "Behance", "likes": random.randint(200, 2000),
                "score": round(min(score, 9.2), 1), "creator": "Behance",
                "tags": [cat, "Behance", "设计项目"], "image": ""
            })
    return results


# ======================================================================
# 主函数
# ======================================================================

def main():
    items = list(BRAND_ITEMS)
    fresh_p = 0
    fresh_b = 0

    if os.environ.get("GITHUB_ACTIONS") == "true":
        print("\U0001f4e1 GitHub Actions 模式: 开始实时爬取...")
        print("  \U0001f4cc 爬取 Pinterest...")
        try:
            pins = scrape_pinterest(60)
            for p in pins:
                if not any(i["title"] == p["title"] for i in items):
                    items.append(p)
                    fresh_p += 1
        except Exception as e:
            print(f"  \u274c Pinterest 爬取失败: {e}")

        print("  \U0001f3af 爬取 Behance...")
        try:
            bh = scrape_behance(40)
            for b in bh:
                if not any(i["title"] == b["title"] for i in items):
                    items.append(b)
                    fresh_b += 1
        except Exception as e:
            print(f"  \u274c Behance 爬取失败: {e}")

        print(f"  \u2705 爬取结果: +{fresh_p}Pinterest +{fresh_b}Behance 共{len(items)}条")
    else:
        print("\U0001f3e0 本地环境: 仅品牌数据（跳过在线爬取）")

    random.shuffle(items)
    items.sort(key=lambda x: x.get("score", 0), reverse=True)

    src_c = Counter(i["source"] for i in items)
    cat_c = Counter(i["category"] for i in items)
    has_img = sum(1 for i in items if i.get("image"))

    result = {
        "date": datetime.date.today().isoformat(),
        "timestamp": datetime.datetime.now().isoformat(),
        "stats": {"total": len(items), "by_source": dict(src_c), "by_category": dict(cat_c)},
        "items": items
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "latest.json"), "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(os.path.join(os.path.dirname(__file__), "data.js"), "w") as f:
        f.write(f"const digestData = {json.dumps(result, ensure_ascii=False)};")

    print(f"\u2705 完成! {len(items)}条 {len(src_c)}来源 {len(cat_c)}品类 {has_img}有图 +{fresh_p}P +{fresh_b}B")
    for s, n in sorted(src_c.items(), key=lambda x: -x[1]):
        print(f"   {s}: {n}")

if __name__ == "__main__":
    main()
