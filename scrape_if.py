"""
iF Design Award Scraper — Corrected API format
"""
import json, asyncio
from playwright.async_api import async_playwright
from collections import defaultdict

# User 19 categories → iF category IDs
IF_CAT_MAP = {
    "水杯": 761,           # Beverages Packaging
    "氛围灯": 129,          # Lighting
    "创意礼盒": 766,        # Consumer Products Packaging
    "装置艺术": 760,        # Installations
    "创意厨具": 548,        # Tableware/Cookware
    "中秋礼盒": 766,        # Consumer Products Packaging
    "帽子": 247,            # Textiles/Walls/Floor
    "创意桌搭": 135,        # Home Furniture
    "端午礼盒": 766,        # Consumer Products Packaging
    "充电宝": 673,          # Tools
    "日历": 317,            # Publishing
    "T恤": 247,             # Textiles/Walls/Floor
    "卫衣": 247,            # Textiles/Walls/Floor
    "卡包": 615,            # Luggage/Bags
    "手机壳": 736,          # Personal Use
    "收纳包": 615,          # Luggage/Bags
    "Polo衫": 247,          # Textiles/Walls/Floor
    "冲锋衣": 10082,        # Sports/Outdoor
    "钥匙扣水壶": 761,      # Beverages Packaging
}


async def scrape_if(cat_map, max_per_cat=30):
    all_items = []
    seen_titles = defaultdict(set)
    cat_results = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://ifdesign.com/en/winner-ranking/winner-overview?awardId=2&sort=random&yearId=0",
                        wait_until="networkidle", timeout=30000)
        await asyncio.sleep(1)
        # Accept cookies
        try:
            btn = await page.query_selector("button:has-text('ACCEPT ALL')")
            if btn:
                await btn.click()
                await asyncio.sleep(1)
        except:
            pass
        
        for user_cat, if_cat_id in sorted(cat_map.items()):
            print(f"📦 {user_cat} (iF={if_cat_id})...", end=" ", flush=True)
            items = []
            offset = 0
            limit = 18
            total = None
            
            while len(items) < max_per_cat:
                url = f"/api/search/entry/{offset}/{limit}?order=random&language=en"
                data = await page.evaluate("""async ({url, catId}) => {
                    const r = await fetch(url, {
                        method: 'POST',
                        credentials: 'include',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            "award":2,"categories":[catId],"countries":[],
                            "range":0,"find":"","disciplines":[],
                            "isGoldAward":false,"yearId":0
                        })
                    });
                    return await r.json();
                }""", {"url": url, "catId": if_cat_id})
                
                entry_items = data.get("items", [])
                if not entry_items:
                    break
                
                if total is None:
                    total = data.get("count", 0)
                
                for e in entry_items:
                    title = e.get("name", "Unknown")
                    if title in seen_titles[user_cat]:
                        continue
                    seen_titles[user_cat].add(title)
                    
                    designer = e.get("designer") or e.get("clients") or []
                    creator = ""
                    if e.get("clients"):
                        creator = e["clients"][0]
                    elif e.get("designer"):
                        creator = e["designer"][0]
                    else:
                        creator = "iF Design Award"
                    
                    desc = e.get("description", "") or ""
                    reason = f"iF Design Award · {desc[:250]}" if desc else f"iF Design Award · {title}"
                    
                    img = e.get("primaryMedia", "") or ""
                    is_gold = e.get("goldAward", False)
                    score = 9.2 if is_gold else 8.5
                    likes = 2000 if is_gold else 800
                    entry_id = e.get("id", "")
                    
                    items.append({
                        "title": title,
                        "reason": reason[:300],
                        "source": "iF设计奖",
                        "category": user_cat,
                        "creator": creator,
                        "score": score,
                        "likes": likes,
                        "url": f"https://ifdesign.com/en/winner-ranking/project/{entry_id}/{offset}" if entry_id else "",
                        "image": img,
                        "tags": [user_cat, "iF Design Award", "获奖"],
                        "award": ["iF Gold Award"] if is_gold else ["iF Design Award"],
                    })
                
                offset += len(entry_items)
                if total and offset >= total:
                    break
                await asyncio.sleep(0.3)
            
            cat_results[user_cat] = {"count": total, "scraped": len(items)}
            print(f"{len(items)}条 (共{total})", flush=True)
            all_items.extend(items)
        
        await browser.close()
    
    return all_items, cat_results


def merge_into_pool(pool_path, new_items):
    pool = json.load(open(pool_path, encoding='utf-8'))
    before = len(pool)
    
    existing_keys = set()
    for i in pool:
        existing_keys.add((i["title"], i["creator"]))
    
    added = 0
    for i in new_items:
        key = (i["title"], i["creator"])
        if key not in existing_keys:
            pool.append(i)
            existing_keys.add(key)
            added += 1
    
    print(f"\n📊 Pool: {before} → {len(pool)} (+{added} from iF)")
    with open(pool_path, 'w', encoding='utf-8') as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)
    
    return pool, added


async def main():
    print(f"🔍 Scraping iF Design Award for {len(IF_CAT_MAP)} categories...")
    items, cat_results = await scrape_if(IF_CAT_MAP, max_per_cat=30)
    
    print(f"\n{'='*40}")
    print(f"✅ Total iF items: {len(items)}")
    print("\nPer category:")
    for c, r in sorted(cat_results.items(), key=lambda x: -x[1]['scraped']):
        print(f"  {c}: {r['scraped']}条 (共{r['count']}条)")
    
    # Save raw
    with open("/tmp/if_results.json", "w") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"\n📁 Raw results: /tmp/if_results.json ({len(items)}条)")
    
    # Merge
    pool, added = merge_into_pool("/tmp/design-daily/brand_pool.json", items)
    
    # Stats
    from collections import Counter
    cats = Counter(i['category'] for i in pool)
    srcs = Counter(i['source'] for i in pool)
    print(f"\nSources: {dict(srcs)}")
    print(f"\nFinal categories ({len(cats)}):")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")


if __name__ == "__main__":
    asyncio.run(main())
