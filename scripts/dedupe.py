#!/usr/bin/env python3
"""Build the deduped product pool from legacy and raw collected leads."""

import argparse
from collections import Counter
from pathlib import Path

from insight_common import (
    DATA_DIR,
    RAW_DIR,
    canonical_url,
    clean_title,
    content_fingerprint,
    ensure_dirs,
    infer_price_power,
    lead_from_legacy,
    load_json,
    make_source_record,
    merge_unique_sources,
    now_iso,
    product_key,
    stable_hash,
    today,
    write_json,
)

SEEN_FINGERPRINTS_PATH = DATA_DIR / "seen_fingerprints.json"


def load_raw_leads():
    leads = []
    for path in sorted(RAW_DIR.glob("*.json")):
        payload = load_json(path, [])
        if isinstance(payload, dict):
            payload = payload.get("items", [])
        for item in payload:
            if isinstance(item, dict):
                if not item.get("title") and not item.get("url"):
                    continue
                leads.append(lead_from_legacy(item))
    return leads


def load_legacy_pool(path):
    payload = load_json(path, [])
    return [lead_from_legacy(item) for item in payload if isinstance(item, dict)]


def load_seen_fingerprints():
    payload = load_json(SEEN_FINGERPRINTS_PATH, {})
    if isinstance(payload, dict):
        return payload.get("fingerprints", {})
    return {}


def empty_product(item, key, seen_fingerprints=None):
    url = canonical_url(item.get("url", ""))
    fingerprint = content_fingerprint(item)
    seen_fingerprints = seen_fingerprints or {}
    created = seen_fingerprints.get(fingerprint) or item.get("added") or today()
    source_record = make_source_record(item)
    base_score = item.get("_score_total") or int(float(item.get("score") or 0) * 5)
    return {
        "id": stable_hash(key),
        "product_key": key,
        "content_fingerprint": fingerprint,
        "title": clean_title(item.get("title", "")),
        "category": item.get("category") or "未分类",
        "summary": item.get("reason", ""),
        "image": item.get("image", ""),
        "tags": sorted(set(item.get("tags", []) or [])),
        "price_gate": infer_price_power(item),
        "selection_score": min(100, max(0, int(base_score or 0) * 2)),
        "selection_scores": {},
        "trend_tags": [],
        "status": "raw",
        "review_status": "unreviewed",
        "source_primary": item.get("source") or "未知来源",
        "sources": [source_record],
        "first_seen": created,
        "last_seen": created,
        "seen_count": 1,
        "url": url,
        "likes_total": item.get("likes", 0) or 0,
        "updated_at": now_iso(),
    }


def merge_product(product, item):
    source_record = make_source_record(item)
    merge_unique_sources(product["sources"], source_record)
    product["seen_count"] = len(product["sources"])
    product["last_seen"] = max(product.get("last_seen") or "", item.get("added") or today())
    product["likes_total"] = int(product.get("likes_total") or 0) + int(item.get("likes") or 0)
    product["tags"] = sorted(set(product.get("tags", []) + (item.get("tags", []) or [])))
    if not product.get("image") and item.get("image"):
        product["image"] = item["image"]
    if len(item.get("reason", "")) > len(product.get("summary", "")):
        product["summary"] = item.get("reason", "")
    if product.get("price_gate") == "unknown":
        product["price_gate"] = infer_price_power(item)
    incoming_score = item.get("_score_total") or int(float(item.get("score") or 0) * 5)
    product["selection_score"] = max(int(product.get("selection_score") or 0), min(100, int(incoming_score or 0) * 2))
    product["updated_at"] = now_iso()
    product["content_fingerprint"] = product.get("content_fingerprint") or content_fingerprint(item)


def build_pool(leads, seen_fingerprints=None):
    products = {}
    url_index = {}
    product_index = {}
    content_index = {}
    seen_fingerprints = seen_fingerprints or {}

    for item in leads:
        url = canonical_url(item.get("url", ""))
        key = product_key(item)

        if url and url in url_index:
            product_id = url_index[url]
        elif key in product_index:
            product_id = product_index[key]
        elif content_fingerprint(item) in content_index:
            product_id = content_index[content_fingerprint(item)]
        else:
            product = empty_product(item, key, seen_fingerprints)
            product_id = product["id"]
            products[product_id] = product
            product_index[key] = product_id
            content_index[product["content_fingerprint"]] = product_id

        if url:
            url_index[url] = product_id
        if key:
            product_index[key] = product_id
        fingerprint = content_fingerprint(item)
        if fingerprint:
            content_index[fingerprint] = product_id

        if products[product_id]["sources"][0].get("url") != url:
            merge_product(products[product_id], item)

    return products, url_index, product_index


def write_seen_fingerprints(products, existing=None):
    fingerprints = dict(existing or {})
    for item in products.values():
        fingerprint = item.get("content_fingerprint")
        first_seen = item.get("first_seen") or today()
        if not fingerprint:
            continue
        previous = fingerprints.get(fingerprint)
        if not previous or first_seen < previous:
            fingerprints[fingerprint] = first_seen
    write_json(
        SEEN_FINGERPRINTS_PATH,
        {
            "generated_at": now_iso(),
            "fingerprints": dict(sorted(fingerprints.items())),
        },
    )


def build_published(products):
    items = sorted(
        products.values(),
        key=lambda item: (
            int(item.get("selection_score") or 0),
            int(item.get("seen_count") or 0),
            item.get("last_seen") or "",
        ),
        reverse=True,
    )
    by_category = Counter(item.get("category") or "未分类" for item in items)
    by_source = Counter()
    for item in items:
        for source in item.get("sources", []):
            by_source[source.get("source") or "未知来源"] += 1
    return {
        "generated_at": now_iso(),
        "stats": {
            "total_products": len(items),
            "total_sources": sum(len(item.get("sources", [])) for item in items),
            "by_category": dict(by_category.most_common()),
            "by_source": dict(by_source.most_common()),
        },
        "items": items,
    }


def refresh_published_from_products(products):
    published = build_published({item["id"]: item for item in products})
    write_json(DATA_DIR / "published.json", published)
    return published


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", default="brand_pool.json", help="Legacy JSON pool to import.")
    parser.add_argument("--raw-only", action="store_true", help="Ignore brand_pool.json and dedupe raw leads only.")
    args = parser.parse_args()

    ensure_dirs()
    leads = []
    if not args.raw_only:
        legacy_path = Path(args.legacy)
        if legacy_path.exists():
            leads.extend(load_legacy_pool(legacy_path))
    leads.extend(load_raw_leads())

    seen_fingerprints = load_seen_fingerprints()
    products, url_index, product_index = build_pool(leads, seen_fingerprints)
    published = build_published(products)
    write_seen_fingerprints(products, seen_fingerprints)

    write_json(DATA_DIR / "products.json", list(products.values()))
    write_json(
        DATA_DIR / "dedupe_index.json",
        {
            "generated_at": now_iso(),
            "url_index": url_index,
            "product_index": product_index,
            "content_index": {
                item.get("content_fingerprint"): item.get("id")
                for item in products.values()
                if item.get("content_fingerprint")
            },
        },
    )
    write_json(DATA_DIR / "published.json", published)

    print(f"leads={len(leads)} products={len(products)} sources={published['stats']['total_sources']}")


if __name__ == "__main__":
    main()
