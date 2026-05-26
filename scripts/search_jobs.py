#!/usr/bin/env python3
"""Generate the recurring search job matrix for weekly product discovery."""

import argparse
import datetime as dt
import urllib.parse

from insight_common import DATA_DIR, ensure_dirs, write_json
from insight_config import CATEGORIES, CATEGORY_SOURCE_GROUPS, SEARCH_INTENTS, SEARCH_QUERY_PATTERNS, SEARCH_SOURCE_GROUPS


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
    today = dt.date.today().isoformat()
    for category in categories:
        base_queries = SEARCH_QUERY_PATTERNS.get(category, [category])
        for query in base_queries[: max(1, min(per_category, 2))]:
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
                    "created_at": today,
                }
            )
        group_names = CATEGORY_SOURCE_GROUPS.get(
            category,
            ["editorial_main", "award_gallery", "design_community", "market_signal"],
        )
        for group_name in group_names:
            sites = SEARCH_SOURCE_GROUPS.get(group_name, [])
            for site in sites[:3]:
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
                        "created_at": today,
                    }
                )
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-category", type=int, default=4, help="Base keyword queries per category.")
    args = parser.parse_args()

    ensure_dirs()
    jobs = build_jobs(per_category=args.per_category)
    payload = {
        "generated_at": dt.datetime.now().replace(microsecond=0).isoformat(),
        "total_jobs": len(jobs),
        "jobs": jobs,
    }
    write_json(DATA_DIR / "search_jobs.json", payload)
    print(f"search_jobs={len(jobs)}")


if __name__ == "__main__":
    main()
