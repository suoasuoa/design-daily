"""
Good Design Award (G-Mark) Scraper — corrected version
======================================================
Uses the public g-mark.io REST API via Playwright's browser context.
Important: The API's `winnerCategoryId` filter is broken (ignored server-side).
Instead, we fetch all winners and use each item's embedded `winnerCategory.name.en`.

Usage:
  python3 scrape_gmark.py                    # Fetch 100 items (2024-2025)
  python3 scrape_gmark.py --max 200          # Fetch up to 200 items
  python3 scrape_gmark.py --years 2025       # Single year only
"""

import json, asyncio, sys
from playwright.async_api import async_playwright
from collections import defaultdict

API_BASE = "https://g-mark.io/api/award/winners"

CATEGORY_MAP = {
    "Personal Accessories": "时尚配饰",
    "Home Accessories": "生活杂货",
    "Kitchen & Cookware": "创意厨具",
    "Tableware": "创意厨具",
    "Furniture": "生活家具",
    "Stationery": "文创文具",
    "Home Electronics": "科技数码",
    "Sports & Hobbies": "运动户外",
    "Kids & Education": "母婴亲子",
    "Health & Beauty": "健康美妆",
    "Smartphone": "科技数码",
    "Computer & Peripherals": "科技数码",
    "Audio Equipment": "科技数码",
    "Camera": "科技数码",
    "Lighting": "氛围灯",
    "Toy & Hobby": "母婴亲子",
    "Garden & Outdoor": "运动户外",
    "Office Equipment": "文创文具",
    "Bath & Toilet": "生活杂货",
    "Bedding": "生活家具",
}


def parse_args():
    max_items = 100
    years = [2024, 2025]
    outfile = "/tmp/gmark_results.json"
    
    for a in sys.argv[1:]:
        if a.startswith("--max="):
            max_items = int(a.split("=")[1])
        elif a.startswith("--years="):
            parts = a.split("=")[1]
            years = [int(y) for y in parts.split(",")]
        elif a.startswith("--out="):
            outfile = a.split("=")[1]
    
    return max_items, years, outfile


def convert_item(c):
    wc = c.get("winnerCategory") or {}
    gm_cat = (wc.get("name") or {}).get("en", "") or ""
    mapped_cat = CATEGORY_MAP.get(gm_cat, "生活杂货")
    
    proper = (c.get("properName") or {}).get("en", "") or ""
    proper_ja = (c.get("properName") or {}).get("ja", "") or ""
    general = (c.get("generalName") or {}).get("en", "") or ""
    title = proper or proper_ja or general or "Unknown"
    
    outline = (c.get("outline") or {}).get("en", "") or ""
    outline_ja = c.get("outline", {}).get("source", "") if c.get("outline") else ""
    reason = outline or outline_ja
    if reason:
        reason = f"Good Design Award · {reason[:250]}"
    else:
        company = (c.get("businessOwner") or {}).get("en", "") or ""
        reason = f"Good Design Award · {company or title}"
    
    company = (c.get("businessOwner") or {}).get("en", "") or ""
    company_ja = (c.get("businessOwner") or {}).get("ja", "") or ""
    
    awards_list = c.get("awards") or []
    award_names = []
    score = 8.5
    likes = 800
    if isinstance(awards_list, list):
        for a in awards_list:
            name = (a.get("name") or {}).get("en", "")
            if name:
                award_names.append(name)
                if "Gold" in name or "Grand" in name:
                    score = 9.2
                    likes = 2500
                elif "Silver" in name:
                    score = 8.8
                    likes = 1500
    
    url = f"https://www.g-mark.org/gallery/winners/{c['id']}?years={c['year']}"
    img = f"https://award-attachments.g-mark.io/winners/{c['year']}/{c['id']}/main.jpg?size=medium"
    
    tags = [mapped_cat, "Good Design Award", "获奖"]
    if award_names:
        tags.append(", ".join(award_names[:2]))
    
    return {
        "title": title,
        "reason": reason[:300],
        "source": "Good Design Award",
        "category": mapped_cat,
        "creator": company or company_ja or "Good Design Award",
        "score": score,
        "likes": likes,
        "url": url,
        "image": img,
        "tags": tags,
        "award": award_names,
    }


async def scrape_gmark(years=None, max_items=100):
    if years is None:
        years = [2024, 2025]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        seen_ids = set()
        all_items = []
        
        for year in years:
            page_num = 1
            while len(all_items) < max_items:
                url = f"{API_BASE}?page={page_num}&size=100&years={year}"
                resp = await context.request.get(url, headers={"Accept": "*/*"})
                if not resp.ok:
                    break
                data = await resp.json()
                hits = data.get("_embedded", {}).get("searchHitList", [])
                if not hits:
                    break
                
                for hit in hits:
                    c = hit["content"]
                    if c["id"] in seen_ids:
                        continue
                    seen_ids.add(c["id"])
                    all_items.append(convert_item(c))
                
                total_pages = data.get("page", {}).get("totalPages", 1)
                if page_num >= total_pages:
                    break
                page_num += 1
                await asyncio.sleep(0.2)
        
        await browser.close()
    
    return all_items


async def main():
    max_items, years, outfile = parse_args()
    print(f"🎯 Fetching Good Design Award (years={years}, max={max_items})")
    items = await scrape_gmark(years=years, max_items=max_items)
    print(f"\n✅ Total: {len(items)} items")
    
    cats = defaultdict(int)
    for i in items:
        cats[i["category"]] += 1
    print("\nCategory distribution:")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")
    
    with open(outfile, "w") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"\n📁 Saved to {outfile}")


if __name__ == "__main__":
    asyncio.run(main())
