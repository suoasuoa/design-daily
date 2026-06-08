#!/usr/bin/env python3
"""Collect product cards from curated market/editorial listing pages."""

import argparse
import datetime as dt
import html
import json
import re
import ssl
from urllib.parse import urlencode, urljoin
import urllib.request

from insight_common import RAW_DIR, ensure_dirs, guess_category, load_json, stable_hash, today, write_json

CTX = ssl._create_unverified_context()

CURATED_PAGES = [
    {
        "source": "Uncrate",
        "url": "https://uncrate.com/gear/",
        "source_type": "market_reference",
    },
    {
        "source": "Uncrate",
        "url": "https://uncrate.com/tech/",
        "source_type": "market_reference",
    },
    {
        "source": "Uncrate",
        "url": "https://uncrate.com/style/",
        "source_type": "market_reference",
    },
    {
        "source": "Uncrate",
        "url": "https://uncrate.com/body/",
        "source_type": "market_reference",
    },
]

SHOPIFY_COLLECTIONS = [
    {
        "source": "Uncrate Shop",
        "url": "https://shop.uncrate.com/collections/bags",
        "source_type": "market_reference",
        "category": "收纳包",
    },
    {
        "source": "Uncrate Shop",
        "url": "https://shop.uncrate.com/collections/bags?page=2",
        "source_type": "market_reference",
        "category": "收纳包",
    },
    {
        "source": "Uncrate Shop",
        "url": "https://shop.uncrate.com/collections/home",
        "source_type": "market_reference",
        "category": "",
    },
    {
        "source": "Uncrate Shop",
        "url": "https://shop.uncrate.com/collections/home?page=2",
        "source_type": "market_reference",
        "category": "",
    },
]

SHOPIFY_JSON_ENDPOINTS = [
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/products.json",
        "source_type": "market_reference",
        "category": "",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/home/products.json",
        "source_type": "market_reference",
        "category": "",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/bags/products.json",
        "source_type": "market_reference",
        "category": "收纳包",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/backpacks/products.json",
        "source_type": "market_reference",
        "category": "收纳包",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/sport-bags/products.json",
        "source_type": "market_reference",
        "category": "收纳包",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/desk-writing/products.json",
        "source_type": "market_reference",
        "category": "创意桌搭",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/kitchen/products.json",
        "source_type": "market_reference",
        "category": "创意厨具",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/steelport-knife-co/products.json",
        "source_type": "market_reference",
        "category": "创意厨具",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/hoodies-sweats/products.json",
        "source_type": "market_reference",
        "category": "卫衣",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/shirts/products.json",
        "source_type": "market_reference",
        "category": "T恤",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/wallets/products.json",
        "source_type": "market_reference",
        "category": "卡包",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/ridge-wallet/products.json",
        "source_type": "market_reference",
        "category": "卡包",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/nanocase/products.json",
        "source_type": "market_reference",
        "category": "手机壳",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/mr-cupps/products.json",
        "source_type": "market_reference",
        "category": "水杯",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/gear/products.json",
        "source_type": "market_reference",
        "category": "",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/tech/products.json",
        "source_type": "market_reference",
        "category": "",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/style/products.json",
        "source_type": "market_reference",
        "category": "",
    },
    {
        "source": "Uncrate Shop",
        "base": "https://shop.uncrate.com",
        "path": "/collections/body/products.json",
        "source_type": "market_reference",
        "category": "",
    },
]


def fetch(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 DesignDailyInsight/1.0",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


STRICT_CATEGORY_PATTERNS = [
    ("创意厨具", [r"\b(bottle opener|kitchen|cookware|knife|utensil|pizza|pan|pot|cutting board)\b", r"厨具|厨房|刀具|锅|开瓶器"]),
    ("水杯", [r"\b(water bottle|travel bottle|drinking bottle|tumbler|mug|coffee cup|travel cup|flask|thermos|drinkware)\b", r"水杯|保温杯|马克杯|随行杯"]),
    ("氛围灯", [r"\b(table lamp|desk lamp|night light|ambient lamp|lantern|lighting fixture)\b", r"氛围灯|小夜灯|台灯|露营灯"]),
    ("创意礼盒", [r"\b(gift box|gift set|boxed set|packaging set)\b", r"礼盒|礼品套装|包装套装"]),
    ("帽子", [r"\b(hat|beanie|bucket hat|baseball cap|cap)\b", r"帽子|棒球帽|渔夫帽"]),
    ("创意桌搭", [r"\b(desk|keyboard|mouse|monitor stand|pen|notebook|stationery|cable organizer)\b", r"桌搭|桌面|键盘|显示器|文具"]),
    ("充电宝", [r"\b(power bank|portable charger|battery pack|portable power station)\b", r"充电宝|移动电源"]),
    ("日历", [r"\b(calendar|planner)\b", r"日历|台历"]),
    ("T恤", [r"\b(t-shirt|tee shirt|graphic tee|shirt)\b", r"T恤|短袖"]),
    ("卫衣", [r"\b(hoodie|sweatshirt|pullover)\b", r"卫衣|帽衫"]),
    ("卡包", [r"\b(wallet|card holder|card case|card wallet)\b", r"卡包|卡夹|钱包"]),
    ("手机壳", [r"\b(phone case|iphone case|phone cover)\b", r"手机壳|保护壳"]),
    ("收纳包", [r"\b(backpack|bag|pouch|organizer pouch|packing cube|travel case|carry-on|duffel)\b", r"收纳包|背包|旅行包|整理包"]),
    ("Polo衫", [r"\b(polo shirt|polo)\b", r"Polo衫"]),
    ("冲锋衣", [r"\b(shell jacket|rain jacket|windbreaker|outdoor jacket|sun jacket)\b", r"冲锋衣|防晒衣|防风夹克"]),
    ("钥匙扣水壶", [r"\b(keychain bottle|keychain|key ring|carabiner)\b", r"钥匙扣|钥匙链"]),
]


def strict_category(title, text=""):
    haystack = f"{title} {text}".lower()
    if "world cup" in haystack:
        haystack = haystack.replace("world cup", "worldcup")
    for category, patterns in STRICT_CATEGORY_PATTERNS:
        if any(re.search(pattern, haystack, re.I) for pattern in patterns):
            return category
    return ""


def first_image(img_tag, base_url):
    srcset = re.search(r'srcset=["\']([^"\']+)["\']', img_tag, re.S)
    src = re.search(r'src=["\']([^"\']+)["\']', img_tag, re.S)
    raw = ""
    if srcset:
        raw = srcset.group(1).split()[0].rstrip(",")
    elif src:
        raw = src.group(1).strip()
    if raw.startswith("//"):
        return "https:" + raw
    if raw.startswith("/"):
        return urljoin(base_url, raw)
    return raw if raw.startswith(("http://", "https://")) else ""


def collect_uncrate(page):
    text = fetch(page["url"])
    pattern = re.compile(r'<a href=["\']([^"\']+)["\'][^>]*>\s*(?:<!--.*?-->\s*)*<img([^>]+)>', re.S)
    items = []
    seen = set()
    for match in pattern.finditer(text):
        url = urljoin(page["url"], clean(match.group(1)))
        img_tag = match.group(2)
        alt = re.search(r'alt=["\']([^"\']+)["\']', img_tag)
        title = clean(alt.group(1) if alt else "")
        image = first_image(img_tag, page["url"])
        if not title or not image:
            continue
        if "assets_c" not in image and "/p/" not in image:
            continue
        category = strict_category(title, title)
        if not category:
            continue
        key = f"{page['source']}|{url}|{title}"
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "id": stable_hash(key),
                "title": title,
                "reason": f"{page['source']} curated product card. Premium market reference with product image.",
                "source": page["source"],
                "source_type": page["source_type"],
                "category": category,
                "creator": page["source"],
                "score": 0,
                "likes": 0,
                "url": url,
                "image": image,
                "tags": [category, page["source"], "市场参考", "premium", ">35"],
                "added": today(),
                "collected_at": today(),
            }
        )
    return items


def collect_shopify_collection(page):
    text = fetch(page["url"])
    items = []
    seen = set()
    card_pattern = re.compile(r'(<img[^>]+>)[\s\S]{0,2500}?href=["\']([^"\']*/products/[^"\']+)["\']', re.S)
    for img_tag, href in card_pattern.findall(text):
        alt = re.search(r'alt=["\']([^"\']+)["\']', img_tag)
        src = re.search(r'src=["\']([^"\']+)["\']', img_tag)
        title = clean(alt.group(1) if alt else "")
        title = re.sub(r"\s+-\s+[^-]{1,32}$", "", title).strip()
        image = clean(src.group(1) if src else "")
        if image.startswith("//"):
            image = "https:" + image
        elif image.startswith("/"):
            image = urljoin(page["url"], image)
        if "width=75" in image or "height=75" in image:
            continue
        url = urljoin(page["url"], clean(href).split("?")[0])
        if not title or not image:
            continue
        category = page.get("category") or strict_category(title, title)
        if not category:
            continue
        key = f"{page['source']}|{url}|{title}"
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "id": stable_hash(key),
                "title": title,
                "reason": f"{page['source']} product listing. Direct shop product page with product image and premium price signal.",
                "source": page["source"],
                "source_type": page["source_type"],
                "category": category,
                "creator": page["source"],
                "score": 0,
                "likes": 0,
                "url": url,
                "image": image,
                "tags": [category, page["source"], "市场参考", "premium", ">35"],
                "added": today(),
                "collected_at": today(),
            }
        )
    return items


def product_price(product):
    prices = []
    for variant in product.get("variants") or []:
        try:
            prices.append(float(variant.get("price") or 0))
        except (TypeError, ValueError):
            pass
    return max(prices) if prices else 0


def product_image(product):
    images = product.get("images") or []
    for image in images:
        src = image.get("src") or image.get("url") or ""
        if src.startswith("//"):
            return "https:" + src
        if src.startswith(("http://", "https://")):
            return src
    return ""


def collect_shopify_json(endpoint, page_number):
    url = endpoint["base"] + endpoint["path"] + "?" + urlencode({"limit": 250, "page": page_number})
    payload = json.loads(fetch(url, timeout=30))
    products = payload.get("products") or []
    items = []
    seen = set()
    for product in products:
        title = clean(product.get("title", ""))
        handle = clean(product.get("handle", ""))
        body = clean(product.get("body_html", ""))
        tags = [clean(tag) for tag in product.get("tags", []) if clean(tag)]
        price = product_price(product)
        image = product_image(product)
        product_url = urljoin(endpoint["base"], f"/products/{handle}") if handle else ""
        if not title or not product_url or not image:
            continue
        category = endpoint.get("category") or strict_category(title, f"{body} {' '.join(tags)}")
        if not category:
            continue
        key = f"{endpoint['source']}|{product_url}|{title}"
        if key in seen:
            continue
        seen.add(key)
        price_tag = ">35" if price >= 35 else "price_unknown"
        reason = body[:220] or f"{endpoint['source']} Shopify product listing."
        if price:
            reason = f"{reason} Listed price signal: ${price:.2f}."
        items.append(
            {
                "id": stable_hash(key),
                "title": title,
                "reason": reason,
                "source": endpoint["source"],
                "source_type": endpoint["source_type"],
                "category": category,
                "creator": endpoint["source"],
                "score": 0,
                "likes": 0,
                "url": product_url,
                "image": image,
                "tags": sorted(set([category, endpoint["source"], "市场参考", "shopify_product", price_tag] + tags[:8])),
                "added": today(),
                "collected_at": today(),
            }
        )
    return items, url


def rotated_pages(total_pages, pages_per_endpoint, offset=0):
    if total_pages <= 0:
        return []
    current_day = dt.date.fromisoformat(today()).toordinal()
    start = (current_day + offset) % total_pages
    return [((start + index) % total_pages) + 1 for index in range(pages_per_endpoint)]


def merge_daily_leads(path, leads):
    existing = []
    if path.exists():
        existing = load_json(path, [])
        if isinstance(existing, dict):
            existing = existing.get("items", [])
    merged = []
    seen = set()
    for item in list(existing) + list(leads):
        if not isinstance(item, dict):
            continue
        key = item.get("id") or item.get("url") or item.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged, len(existing), len(merged) - len(existing)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Maximum items to save.")
    parser.add_argument("--shopify-pages", type=int, default=2, help="Rotating Shopify JSON pages per endpoint.")
    parser.add_argument("--shopify-total-pages", type=int, default=8, help="Assumed page depth for rotating Shopify JSON pages.")
    parser.add_argument("--page-offset", type=int, default=0, help="Extra page rotation offset for top-up passes.")
    args = parser.parse_args()

    ensure_dirs()
    collected = []
    for page in CURATED_PAGES:
        try:
            items = collect_uncrate(page)
            print(f"{page['source']} {page['url']}: {len(items)}")
            collected.extend(items)
        except Exception as exc:
            print(f"{page['source']} {page['url']}: failed ({exc})")
    for page in SHOPIFY_COLLECTIONS:
        try:
            items = collect_shopify_collection(page)
            print(f"{page['source']} {page['url']}: {len(items)}")
            collected.extend(items)
        except Exception as exc:
            print(f"{page['source']} {page['url']}: failed ({exc})")
    for endpoint_index, endpoint in enumerate(SHOPIFY_JSON_ENDPOINTS):
        for page_number in rotated_pages(args.shopify_total_pages, args.shopify_pages, endpoint_index + args.page_offset):
            try:
                items, url = collect_shopify_json(endpoint, page_number)
                print(f"{endpoint['source']} {url}: {len(items)}")
                collected.extend(items)
            except Exception as exc:
                print(f"{endpoint['source']} {endpoint['path']} page={page_number}: failed ({exc})")
    if args.limit:
        collected = collected[: args.limit]
    path = RAW_DIR / f"curated-pages-{today().replace('-', '')}.json"
    merged, existing_count, added_count = merge_daily_leads(path, collected)
    write_json(path, merged)
    print(f"saved={path} fetched={len(collected)} existing={existing_count} added={added_count} total={len(merged)}")


if __name__ == "__main__":
    main()
