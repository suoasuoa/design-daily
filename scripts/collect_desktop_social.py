#!/usr/bin/env python3
"""Collect social product leads from a visible local browser session.

This script is for the operator's own desktop. It opens Douyin and Instagram
search pages in a persistent browser profile, uses normal page navigation, and
does not bypass login, captcha, paywalls, or private data. If a platform asks
for verification, handle it in the browser and rerun the script.
"""

import argparse
import json
import os
import re
import time
import urllib.parse
from pathlib import Path

from insight_common import RAW_DIR, ensure_dirs, stable_hash, today, write_json
from insight_config import CATEGORIES


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = Path.home() / ".design-daily-social-browser"
DEFAULT_STATE = ROOT / "data" / "desktop_social_state.json"

PLATFORM_META = {
    "douyin": {
        "source": "抖音",
        "search_url": "https://www.douyin.com/search/{query}?type=general",
        "host_tokens": ["douyin.com"],
    },
    "instagram": {
        "source": "Instagram",
        "search_url": "https://www.instagram.com/explore/search/keyword/?q={query}",
        "host_tokens": ["instagram.com"],
    },
}

QUERY_SUFFIXES = {
    "douyin": ["好物", "新品", "创意", "种草"],
    "instagram": ["product design", "gift ideas", "gadgets"],
}


def category_query(category, platform):
    if platform == "instagram":
        mapping = {
            "水杯": "water bottle",
            "氛围灯": "ambient lamp",
            "创意礼盒": "gift box packaging",
            "装置艺术": "installation art",
            "创意厨具": "kitchen gadget",
            "中秋礼盒": "mooncake packaging",
            "帽子": "cap design",
            "创意桌搭": "desk setup accessory",
            "端午礼盒": "zongzi packaging",
            "充电宝": "power bank",
            "日历": "desk calendar",
            "T恤": "graphic t shirt",
            "卫衣": "hoodie design",
            "卡包": "card holder wallet",
            "手机壳": "phone case",
            "收纳包": "organizer pouch",
            "Polo衫": "polo shirt",
            "冲锋衣": "shell jacket",
            "钥匙扣水壶": "keychain bottle",
        }
        return mapping.get(category, category)
    return category


def search_url(platform, category, suffix):
    base = category_query(category, platform)
    query = f"{base} {suffix}".strip()
    return PLATFORM_META[platform]["search_url"].format(query=urllib.parse.quote(query))


def load_state(path):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"seen_urls": {}, "seen_ids": {}}


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_url(url):
    if not url:
        return ""
    url = str(url).strip()
    if url.startswith("/"):
        return ""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    query = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        if not key.startswith("utm_") and key not in {"share_token", "share_sign", "xsec_token"}
    ]
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), urllib.parse.urlencode(query), ""))


def valid_platform_url(platform, url):
    url = normalize_url(url)
    if not url:
        return ""
    host = urllib.parse.urlsplit(url).netloc.lower()
    if not any(token in host for token in PLATFORM_META[platform]["host_tokens"]):
        return ""
    if platform == "douyin" and not re.search(r"/(video|note)/[0-9]+|/share/", url):
        return ""
    if platform == "instagram" and not re.search(r"/(p|reel|reels|tv)/", urllib.parse.urlsplit(url).path):
        return ""
    return url


def extract_candidates(page, platform):
    if platform == "douyin":
        return page.evaluate(
            r"""() => {
              const imageFrom = (el) => {
                const img = el.querySelector('img');
                if (img && (img.currentSrc || img.src)) return img.currentSrc || img.src;
                const bg = Array.from(el.querySelectorAll('*')).map(node => getComputedStyle(node).backgroundImage || '').find(value => value.includes('url('));
                if (!bg) return '';
                const match = bg.match(/url\(["']?(.*?)["']?\)/);
                return match ? match[1] : '';
              };
              return Array.from(document.querySelectorAll('[id^="waterfall_item_"]')).map(card => {
                const id = (card.id || '').replace('waterfall_item_', '');
                const titleEl = card.querySelector('.BjLsdJMi') || card.querySelector('[class*="title"]');
                const authorEl = card.querySelector('.WldPmwm5');
                const text = (card.innerText || '').trim();
                const title = (titleEl ? titleEl.innerText : text).trim();
                const author = authorEl ? '@' + authorEl.innerText.trim() : '';
                return {
                  href: id ? `https://www.douyin.com/video/${id}` : '',
                  title: [title, author].filter(Boolean).join(' · '),
                  image: imageFrom(card),
                };
              }).filter(item => item.href && item.title);
            }"""
        )
    return page.evaluate(
        """(platform) => {
          const out = [];
          const anchors = Array.from(document.querySelectorAll('a[href]'));
          for (const a of anchors) {
            const href = a.href || '';
            const card = a.closest('article, li, section, div') || a;
            const text = (card.innerText || a.innerText || a.getAttribute('aria-label') || '').trim();
            const img = card.querySelector('img');
            const image = img ? (img.currentSrc || img.src || '') : '';
            const title = text.split('\\n').map(s => s.trim()).filter(Boolean).slice(0, 3).join(' · ');
            if (!href) continue;
            out.push({ href, title, image });
          }
          return out;
        }""",
        platform,
    )


def likes_from_text(text):
    text = text or ""
    match = re.search(r"([0-9]+(?:\\.[0-9]+)?)\\s*([万wWkK]?)", text)
    if not match:
        return 0
    value = float(match.group(1))
    unit = match.group(2).lower()
    if unit in {"万", "w"}:
        value *= 10000
    elif unit == "k":
        value *= 1000
    return int(value)


def make_item(platform, category, raw):
    source = PLATFORM_META[platform]["source"]
    url = valid_platform_url(platform, raw.get("href", ""))
    title = re.sub(r"\\s+", " ", raw.get("title") or "").strip()
    if not title:
        title = f"{source} · {category} 灵感"
    title = title[:120]
    item_id = stable_hash(f"{platform}|{url or title}", 16)
    return {
        "id": item_id,
        "title": title,
        "reason": f"{source}桌面采集 · {category}相关社媒线索，需结合原链接判断是否可买样或改造。",
        "source": source,
        "category": category,
        "creator": source,
        "score": 0,
        "likes": likes_from_text(title),
        "url": url,
        "image": raw.get("image", ""),
        "tags": [category, source, "桌面采集", "社媒线索"],
        "added": today(),
        "collected_at": today(),
        "source_type": "social_signal",
    }


def collect_platform(page, platform, categories, per_category, delay, state, max_items):
    items = []
    suffixes = QUERY_SUFFIXES[platform]
    for category_index, category in enumerate(categories):
        suffix = suffixes[category_index % len(suffixes)]
        url = search_url(platform, category, suffix)
        print(f"search platform={platform} category={category} url={url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if platform == "douyin":
            try:
                page.wait_for_selector('[id^="waterfall_item_"]', timeout=15000)
            except Exception:
                title = page.title()
                body = ""
                try:
                    body = page.locator("body").inner_text(timeout=3000)
                except Exception:
                    body = ""
                if "验证码" in title or "验证码" in body or not body.strip():
                    debug_path = ROOT / "logs" / f"douyin-blocked-{today()}.png"
                    debug_path.parent.mkdir(exist_ok=True)
                    page.screenshot(path=str(debug_path), full_page=True)
                    print(f"blocked platform=douyin category={category} title={title} screenshot={debug_path}")
                    break
        time.sleep(delay)
        for _ in range(2):
            page.mouse.wheel(0, 1200)
            time.sleep(delay)
        raw_candidates = extract_candidates(page, platform)
        kept_for_category = 0
        for raw in raw_candidates:
            item = make_item(platform, category, raw)
            if not item["url"]:
                continue
            if item["url"] in state["seen_urls"]:
                continue
            state["seen_urls"][item["url"]] = today()
            state["seen_ids"][item["id"]] = today()
            items.append(item)
            kept_for_category += 1
            if kept_for_category >= per_category or len(items) >= max_items:
                break
        print(f"kept platform={platform} category={category} count={kept_for_category}")
        if len(items) >= max_items:
            break
    return items


def merge_existing(path, new_items):
    existing = []
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        existing = payload.get("items", payload) if isinstance(payload, dict) else payload
    by_url = {normalize_url(item.get("url", "")): item for item in existing if isinstance(item, dict) and item.get("url")}
    for item in new_items:
        key = normalize_url(item.get("url", ""))
        if key and key not in by_url:
            by_url[key] = item
    return list(by_url.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", action="append", choices=sorted(PLATFORM_META), help="Platform to collect. Repeatable.")
    parser.add_argument("--target-total", type=int, default=80, help="Maximum new raw candidates to collect.")
    parser.add_argument("--min-social", type=int, default=10, help="Warn if fewer than this many candidates are collected.")
    parser.add_argument("--per-category", type=int, default=3)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--headless", action="store_true", help="Run browser headless. Visible mode is safer for first setup.")
    parser.add_argument("--profile-dir", default=str(DEFAULT_PROFILE))
    parser.add_argument("--state-file", default=str(DEFAULT_STATE))
    parser.add_argument("--category", action="append", help="Limit to one or more categories for testing.")
    args = parser.parse_args()

    ensure_dirs()
    platforms = args.platform or ["douyin"]
    categories = args.category or CATEGORIES
    max_per_platform = max(1, args.target_total // len(platforms))
    state_path = Path(args.state_file)
    state = load_state(state_path)
    state.setdefault("seen_urls", {})
    state.setdefault("seen_ids", {})

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("缺少 Playwright。请先运行：python3 -m pip install playwright && python3 -m playwright install chromium") from exc

    all_items = []
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            args.profile_dir,
            headless=args.headless,
            viewport={"width": 1440, "height": 1000},
            locale="zh-CN",
        )
        page = context.pages[0] if context.pages else context.new_page()
        for platform in platforms:
            all_items.extend(collect_platform(page, platform, categories, args.per_category, args.delay, state, max_per_platform))
        context.close()

    path = RAW_DIR / f"social-desktop-{today()}.json"
    merged = merge_existing(path, all_items)
    write_json(
        path,
        {
            "generated_at": today(),
            "items": merged,
            "meta": {
                "platforms": platforms,
                "target_total": args.target_total,
                "new_items": len(all_items),
                "total_items_for_day": len(merged),
                "min_social": args.min_social,
            },
        },
    )
    save_state(state_path, state)
    status = "ok" if len(merged) >= args.min_social else "low"
    print(f"social_desktop={status} path={path} new={len(all_items)} total_today={len(merged)} min={args.min_social}")


if __name__ == "__main__":
    main()
