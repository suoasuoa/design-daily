"""
Good Design Award (G-Mark) Scraper
Uses the public g-mark.io REST API via Playwright's browser context
(bypasses Python SSL cert issues by using Chromium's cert store).
"""

import json
import time
import sys
import os
import asyncio
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

API_BASE = "https://g-mark.io/api/award/winners"

RELEVANT_CATEGORIES = {
    "Tableware": "e2b54b33-7fb4-4ca5-a01f-e2e9455f27f4",
    "Kitchen & Cookware": "564c5670-de86-4071-b4f0-5ab2e631ffb1",
    "Home Accessories": "718c34de-ed43-4a63-a32d-0a5d206a71d7",
    "Furniture": "43f25cf4-8590-40c4-8b43-227debb718fd",
    "Stationery": "dfa9af5e-b58b-4e4a-8501-33f6300d0754",
    "Home Electronics": "7ffee4ed-5ec9-4aec-93aa-4688b319da15",
    "Sports & Hobbies": "2f972782-2d00-45d5-987d-950f86f6b486",
    "Personal Accessories": "539a7547-911e-457b-b1a1-a0e7671fe81e",
    "Kids & Education": "cc3e6e19-9fce-4010-b304-63cf1095a9f8",
    "Health & Beauty": "0514b32b-6179-467c-8b35-6f0a43ac4d89",
}

GALLERY_CATEGORIES = {
    "Tableware": "创意厨具",
    "Kitchen & Cookware": "创意厨具",
    "Home Accessories": "生活杂货",
    "Furniture": "生活家具",
    "Stationery": "文创文具",
    "Home Electronics": "科技数码",
    "Sports & Hobbies": "运动户外",
    "Personal Accessories": "时尚配饰",
    "Kids & Education": "母婴亲子",
    "Health & Beauty": "健康美妆",
}

def convert_item(content, category_name):
    proper_en = (content.get("properName") or {}).get("en", "") or ""
    proper_ja = (content.get("properName") or {}).get("ja", "") or ""
    general_en = (content.get("generalName") or {}).get("en", "") or ""
    company_en = (content.get("businessOwner") or {}).get("en", "") or ""
    company_ja = (content.get("businessOwner") or {}).get("ja", "") or ""
    outline_en = (content.get("outline") or {}).get("en", "") or ""
    outline_ja = (content.get("outline") or {}).get("source", "") or ""
    
    title = proper_en or proper_ja or general_en or "Unknown"
    
    reason = outline_en or outline_ja
    if not reason:
        reason = f"Good Design Award · {company_en or company_ja}"
    else:
        reason = f"Good Design Award · {reason[:200]}"
    
    gallery_url = f"https://www.g-mark.org/gallery/winners/{content['id']}?years={content['year']}"
    mapped_cat = GALLERY_CATEGORIES.get(category_name, "生活杂货")
    
    tags = [mapped_cat, "Good Design Award", "获奖"]
    
    score = 8.5
    likes = 800
    awards = content.get("awards") or []
    award_names = []
    if isinstance(awards, list):
        for a in awards:
            name = (a.get("name") or {}).get("en", "")
            if name:
                award_names.append(name)
                if "Gold" in name or "Grand" in name:
                    score = 9.2
                    likes = 2500
                elif "Silver" in name:
                    score = 8.8
                    likes = 1500
    
    if award_names:
        tags.append(", ".join(award_names[:2]))
    
    image_url = f"https://award-attachments.g-mark.io/winners/{content['year']}/{content['id']}/main.jpg?size=medium"
    
    return {
        "title": title,
        "reason": reason[:300],
        "source": "Good Design Award",
        "category": mapped_cat,
        "creator": company_en or company_ja or "Good Design Award",
        "score": score,
        "likes": likes,
        "url": gallery_url,
        "image": image_url,
        "tags": tags,
        "award": award_names,
    }


async def scrape_gmark(years=None, items_per_category=30):
    if years is None:
        years = [2024, 2025]
    
    all_items = []
    print(f"🎯 Scraping Good Design Award (years={years}, max {items_per_category}/category)")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        async def api_get(url):
            resp = await context.request.get(url, headers={
                "Accept": "*/*",
            })
            return {"ok": resp.ok, "json": await resp.json()}
        
        for cat_name, cat_id in RELEVANT_CATEGORIES.items():
            print(f"  📁 {cat_name}...", end=" ", flush=True)
            count = 0
            for year in years:
                page_num = 1
                while count < items_per_category:
                    url = (f"{API_BASE}?page={page_num}&size=50"
                           f"&winnerCategoryId={cat_id}"
                           f"&years={year}"
                           f"&sort=year%2Cdesc&sort=awardNo%2Casc")
                    
                    try:
                        resp = await api_get(url)
                        if not resp.get("ok"):
                            break
                        data = resp["json"]
                    except Exception as e:
                        print(f"API error: {e}")
                        break
                    
                    hits = data.get("_embedded", {}).get("searchHitList", [])
                    if not hits:
                        break
                    
                    for hit in hits:
                        content = hit["content"]
                        all_items.append(convert_item(content, cat_name))
                        count += 1
                        if count >= items_per_category:
                            break
                    
                    total_pages = data.get("page", {}).get("totalPages", 1)
                    if page_num >= total_pages:
                        break
                    page_num += 1
                    await asyncio.sleep(0.3)
            
            print(f"{count} items")
        
        await browser.close()
    
    print(f"\n✅ Total: {len(all_items)} items from Good Design Award")
    return all_items


async def main():
    items = await scrape_gmark(years=[2025], items_per_category=5)
    print(f"\nSample:")
    for item in items[:2]:
        print(json.dumps(item, ensure_ascii=False, indent=2))
        print("---")
    
    with open("/tmp/gmark_results.json", "w") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Saved /tmp/gmark_results.json ({len(items)} items)")


if __name__ == "__main__":
    asyncio.run(main())
