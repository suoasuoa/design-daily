#!/usr/bin/env python3
"""Generate the recurring search job matrix for weekly product discovery."""

import argparse
from collections import defaultdict, deque
import datetime as dt
import os
import urllib.parse
from zoneinfo import ZoneInfo

from insight_common import DATA_DIR, ensure_dirs, today, write_json
from insight_config import CATEGORIES, CATEGORY_SOURCE_GROUPS, SEARCH_INTENTS, SEARCH_QUERY_PATTERNS, SEARCH_SOURCE_GROUPS

LOCAL_TZ = ZoneInfo("Asia/Shanghai")

def intent_for_query(category, query):
    text = f"{category} {query}".lower()
    if any(word in text for word in ["amazon", "etsy", "新品", "new", "product", "gadget", "holder", "bottle", "lamp"]):
        return "buy_sample"
    if any(word in text for word in ["packaging", "包装", "design", "结构", "creative", "创意"]):
        return "adapt"
    return "trend"


def search_url(query):
    return "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})


def build_jobs(categories=None, per_category=4):
    categories = categories or CATEGORIES
    jobs = []
    current_day = today()
    enable_social = os.environ.get("ENABLE_SOCIAL_PUBLIC_SEARCH", "").strip().lower() in {"1", "true", "yes"}
    for category in categories:
        base_queries = SEARCH_QUERY_PATTERNS.get(category, [category])
        for query in base_queries[: max(1, min(per_category, 3))]:
            intent = intent_for_query(category, query)
            jobs.append(
                {
                    "id": f"{category}:{query}",
                    "category": category,
                    "query": query,
                    "intent": intent,
                    "intent_note": SEARCH_INTENTS[intent],
                    "source_group": "curated_keyword",
                    "quality_tier": "curated",
                    "search_url": search_url(query),
                    "created_at": current_day,
                }
            )
        group_names = CATEGORY_SOURCE_GROUPS.get(
            category,
            ["editorial_main", "award_gallery", "design_community", "market_signal"],
        )
        if enable_social and "social_public_index" not in group_names:
            group_names = list(group_names) + ["social_public_index"]
        for group_name in group_names:
            sites = SEARCH_SOURCE_GROUPS.get(group_name, [])
            for site in sites:
                query = f"{category} {site}"
                intent = intent_for_query(category, query)
                jobs.append(
                    {
                        "id": f"{category}:{group_name}:{site}",
                        "category": category,
                        "query": query,
                        "intent": intent,
                        "intent_note": SEARCH_INTENTS[intent],
                        "source_group": group_name,
                        "quality_tier": "curated",
                        "search_url": search_url(query),
                        "created_at": current_day,
                    }
                )
    return jobs


def balanced_jobs(jobs):
    """Interleave jobs across source groups and categories so early limits stay diverse."""
    buckets = defaultdict(deque)
    for job in jobs:
        key = (job.get("source_group") or "unknown", job.get("category") or "未分类")
        buckets[key].append(job)

    group_order = [
        "packaging_specialist",
        "design_community",
        "market_signal",
        "social_public_index",
        "editorial_main",
        "award_gallery",
        "curated_keyword",
    ]
    ordered = []
    while any(buckets.values()):
        for category in CATEGORIES:
            for group_name in group_order:
                bucket = buckets.get((group_name, category))
                if bucket:
                    ordered.append(bucket.popleft())
        for key in sorted(buckets):
            group_name, _category = key
            if group_name in group_order:
                continue
            bucket = buckets[key]
            if bucket:
                ordered.append(bucket.popleft())
    return ordered


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-category", type=int, default=4, help="Base keyword queries per category.")
    args = parser.parse_args()

    ensure_dirs()
    jobs = balanced_jobs(build_jobs(per_category=args.per_category))
    payload = {
        "generated_at": dt.datetime.now(LOCAL_TZ).replace(microsecond=0).isoformat(),
        "total_jobs": len(jobs),
        "jobs": jobs,
    }
    write_json(DATA_DIR / "search_jobs.json", payload)
    print(f"search_jobs={len(jobs)}")


if __name__ == "__main__":
    main()
