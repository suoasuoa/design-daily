#!/usr/bin/env python3
"""Review whether products fit the configured categories before publishing."""

import argparse
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from insight_common import DATA_DIR, load_env, load_json, now_iso, write_json
from insight_config import CATEGORIES, CATEGORY_REVIEW_RULES

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
SSL_CONTEXT = ssl._create_unverified_context()


def deepseek_model():
    raw = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()
    aliases = {
        "deepseek-v4-flash": "deepseek-v4-flash",
        "deepseek-v4-pro": "deepseek-v4-pro",
        "deepseek-v4": "deepseek-v4-flash",
        "deepseek-v3.2": "deepseek-v3.2",
        "deepseek-chat": "deepseek-chat",
        "deepseek-reasoner": "deepseek-reasoner",
    }
    return aliases.get(raw.lower(), raw)


def compact_product(item):
    sources = item.get("sources") or []
    source_names = []
    for source in sources[:4]:
        name = source.get("source")
        if name and name not in source_names:
            source_names.append(name)
    return {
        "id": item.get("id"),
        "title": item.get("title", "")[:120],
        "category": item.get("category", ""),
        "summary": item.get("summary", "")[:240],
        "tags": (item.get("tags") or [])[:10],
        "trend_tags": (item.get("trend_tags") or [])[:8],
        "sources": source_names,
    }


def parse_json_response(text):
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        text = match.group(0)
    return json.loads(text)


def review_batch(batch, api_key):
    schema = {
        "items": [
            {
                "id": "product id",
                "keep": True,
                "category": "one configured category if keep is true",
                "confidence": 0,
                "reason": "short reason",
            }
        ]
    }
    rules = "\n".join(f"- {category}: {CATEGORY_REVIEW_RULES[category]}" for category in CATEGORIES)
    prompt = f"""
你是严格的产品品类审核员。目标是清洗选品数据池，只保留明确属于指定品类的产品。

审核规则：
1. 只允许以下 19 个品类，不允许新增品类。
2. 如果产品不明确属于任何一个指定品类，keep=false。
3. 如果原品类错了但产品明确属于另一个指定品类，keep=true 并修正 category。
4. 对泛户外、运动器材、鞋、手套、望远镜、棒球用品、宠物用品、马桶、检测耗材、家具、家电、汽车、相机等，不要因为出现 outdoor/shell/bag/case 就硬归入冲锋衣/收纳包/手机壳。
5. 宁可严格删除，也不要保留弱相关产品。

品类定义：
{rules}

只返回合法 JSON，不要解释。结构必须是：
{json.dumps(schema, ensure_ascii=False)}

待审核产品：
{json.dumps([compact_product(item) for item in batch], ensure_ascii=False)}
"""
    body = {
        "model": deepseek_model(),
        "messages": [
            {"role": "system", "content": "你只输出合法 JSON。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 3500,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90, context=SSL_CONTEXT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code != 400:
            raise
        body.pop("response_format", None)
        req = urllib.request.Request(
            DEEPSEEK_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90, context=SSL_CONTEXT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    return parse_json_response(content).get("items", [])


def local_fallback(item):
    category = item.get("category")
    title = item.get("title", "").lower()
    summary = item.get("summary", "").lower()
    text = f"{title} {summary} {' '.join(item.get('tags') or [])}".lower()
    reject_words = [
        "baseball", "glove", "shoe", "shoes", "cleat", "binocular", "toilet",
        "urine", "pet", "camera", "rangefinder", "spoon", "golf", "hockey",
        "wrapping toilet", "马桶", "棒球", "望远镜", "球鞋", "宠物", "尿",
    ]
    if category == "冲锋衣" and any(word in text for word in reject_words):
        return {"id": item.get("id"), "keep": False, "category": category, "confidence": 8, "reason": "local reject obvious off-category"}
    return {"id": item.get("id"), "keep": True, "category": category, "confidence": 3, "reason": "local fallback kept"}


def review_one_batch(batch, api_key):
    try:
        return review_batch(batch, api_key) if api_key else [local_fallback(item) for item in batch]
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        print(f"fallback local category review ({exc})", flush=True)
        return [local_fallback(item) for item in batch]


def apply_batch_reviews(batch, result, reviews):
    batch_ids = {item.get("id") for item in batch}
    for row in result:
        item_id = row.get("id")
        if item_id not in batch_ids:
            continue
        keep = bool(row.get("keep"))
        category = row.get("category") if row.get("category") in CATEGORIES else ""
        reviews[item_id] = {
            "keep": keep and bool(category),
            "category": category,
            "confidence": int(row.get("confidence") or 0),
            "reason": str(row.get("reason") or "")[:240],
            "reviewed_at": now_iso(),
            "source": "deepseek" if os.environ.get("DEEPSEEK_API_KEY", "") else "local_fallback",
        }
    for item in batch:
        if item.get("id") not in reviews:
            reviews[item.get("id")] = local_fallback(item)


def review_products(products, batch_size=20, force=False, sleep=0.5):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    existing = load_json(DATA_DIR / "category_review.json", {})
    reviews = {} if force else dict(existing.get("reviews", {}))
    todo = [item for item in products if force or item.get("id") not in reviews]

    batches = [todo[start : start + batch_size] for start in range(0, len(todo), batch_size)]
    workers = max(1, int(os.environ.get("CATEGORY_REVIEW_WORKERS", "1")))
    done = 0
    if workers == 1:
        for batch in batches:
            result = review_one_batch(batch, api_key)
            apply_batch_reviews(batch, result, reviews)
            done += len(batch)
            write_json(DATA_DIR / "category_review.json", {"generated_at": now_iso(), "reviews": reviews})
            print(f"reviewed={done}/{len(todo)} cached={len(reviews)}", flush=True)
            if api_key:
                time.sleep(sleep)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_batch = {executor.submit(review_one_batch, batch, api_key): batch for batch in batches}
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                result = future.result()
                apply_batch_reviews(batch, result, reviews)
                done += len(batch)
                write_json(DATA_DIR / "category_review.json", {"generated_at": now_iso(), "reviews": reviews})
                print(f"reviewed={done}/{len(todo)} cached={len(reviews)}", flush=True)

    kept = []
    rejected = []
    changed = 0
    for item in products:
        review = reviews.get(item.get("id")) or local_fallback(item)
        if review.get("keep") and review.get("category") in CATEGORIES:
            if item.get("category") != review["category"]:
                item["category_review_original"] = item.get("category")
                item["category"] = review["category"]
                changed += 1
            item["category_review"] = {
                "status": "approved",
                "confidence": review.get("confidence", 0),
                "reason": review.get("reason", ""),
                "reviewed_at": review.get("reviewed_at", now_iso()),
            }
            kept.append(item)
        else:
            clone = dict(item)
            clone["category_review"] = {
                "status": "rejected",
                "suggested_category": review.get("category", ""),
                "confidence": review.get("confidence", 0),
                "reason": review.get("reason", ""),
                "reviewed_at": review.get("reviewed_at", now_iso()),
            }
            rejected.append(clone)

    write_json(DATA_DIR / "category_review.json", {"generated_at": now_iso(), "reviews": reviews})
    write_json(DATA_DIR / "rejected_category.json", rejected)
    write_json(DATA_DIR / "products.json", kept)
    write_json(DATA_DIR / "published.json", build_published(kept))
    print(f"category_review kept={len(kept)} rejected={len(rejected)} recategorized={changed}")
    return kept, rejected, changed


def build_published(products):
    items = sorted(
        products,
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


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    os.environ["CATEGORY_REVIEW_WORKERS"] = str(args.workers)
    products = load_json(DATA_DIR / "products.json", [])
    review_products(products, args.batch_size, args.force)


if __name__ == "__main__":
    main()
