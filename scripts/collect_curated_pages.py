#!/usr/bin/env python3
"""Collect product cards from curated market/editorial listing pages."""

import argparse
import html
import re
import ssl
from urllib.parse import urljoin
import urllib.request

from insight_common import RAW_DIR, ensure_dirs, guess_category, stable_hash, today, write_json

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
        category = guess_category(title, title)
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
        category = page.get("category") or guess_category(title, title)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Maximum items to save.")
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
    if args.limit:
        collected = collected[: args.limit]
    path = RAW_DIR / f"curated-pages-{today().replace('-', '')}.json"
    write_json(path, collected)
    print(f"saved={path} items={len(collected)}")


if __name__ == "__main__":
    main()
