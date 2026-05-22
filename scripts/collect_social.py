#!/usr/bin/env python3
"""Create a small daily social sampling file for Xiaohongshu or Douyin.

This script is intentionally conservative. It does not bypass login, solve
captchas, or scrape private data. In the default mode it prints search URLs
and creates a fill-in JSON template. Use it as the durable handoff between
browser sampling and the dedupe pipeline.
"""

import argparse
import datetime as dt
import json
import urllib.parse

from insight_common import RAW_DIR, ensure_dirs, stable_hash, write_json
from insight_config import CATEGORIES, SOCIAL_SEARCH_TEMPLATES


def make_search_url(source, category):
    template = SOCIAL_SEARCH_TEMPLATES[source]
    return template.format(query=urllib.parse.quote(category))


def template_items(source, per_category):
    items = []
    for category in CATEGORIES:
        search_url = make_search_url(source, category)
        for index in range(per_category):
            items.append(
                {
                    "id": stable_hash(f"{source}|{category}|{dt.date.today().isoformat()}|{index}"),
                    "title": "",
                    "reason": "",
                    "source": "小红书" if source == "xiaohongshu" else "抖音",
                    "category": category,
                    "creator": "",
                    "score": 0,
                    "likes": 0,
                    "url": "",
                    "image": "",
                    "tags": [category, "社交采样"],
                    "added": dt.date.today().isoformat(),
                    "collected_at": dt.date.today().isoformat(),
                    "_search_url": search_url,
                    "_note": "填入你在平台搜索时确认过的产品线索。空标题会在导入前被忽略。",
                }
            )
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["xiaohongshu", "douyin"], required=True)
    parser.add_argument("--per-category", type=int, default=5)
    parser.add_argument("--print-urls", action="store_true", help="Print search URLs for manual browser sampling.")
    args = parser.parse_args()

    ensure_dirs()
    if args.print_urls:
        for category in CATEGORIES:
            print(f"{category}: {make_search_url(args.source, category)}")

    items = template_items(args.source, args.per_category)
    source_name = "xiaohongshu" if args.source == "xiaohongshu" else "douyin"
    path = RAW_DIR / f"social-{source_name}-{dt.date.today().isoformat()}.json"
    existing = path.exists()
    if existing:
        print(f"exists={path}; not overwriting")
        print("Edit the existing file, then run: python3 scripts/dedupe.py")
        return
    write_json(path, items)
    print(f"created={path} slots={len(items)}")
    print("Fill confirmed items into the template, leave unused slots blank, then run:")
    print("python3 scripts/dedupe.py && python3 scripts/score.py --limit 200 && python3 scripts/build_site.py")


if __name__ == "__main__":
    main()
