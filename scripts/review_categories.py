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

from insight_common import DATA_DIR, load_env, load_json, now_iso, today, write_json
from insight_config import (
    CATEGORIES,
    CATEGORY_KEYWORDS,
    CATEGORY_REVIEW_RULES,
    RETIRED_CATEGORIES,
    RETIRED_CATEGORY_CUTOFF,
)

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
SSL_CONTEXT = ssl._create_unverified_context()
REVIEW_POLICY_VERSION = 2
QUALITY_WEIGHTS = {
    "utility": 0.22,
    "frequency": 0.18,
    "broad_appeal": 0.16,
    "functionality": 0.16,
    "innovation": 0.14,
    "price_power": 0.07,
    "clarity": 0.05,
    "emotion": 0.02,
}
QUALITY_FIELDS = tuple(QUALITY_WEIGHTS)


def retirement_review(item):
    return {
        "id": item.get("id"),
        "keep": False,
        "category": "",
        "confidence": 10,
        "reason": f"品类已于 {RETIRED_CATEGORY_CUTOFF} 停止收集，原记录转入审核归档",
        "reviewed_at": now_iso(),
        "source": "retirement_policy",
        "policy_version": REVIEW_POLICY_VERSION,
    }


def trusted_cached_review(review):
    if not review:
        return False
    if int(review.get("policy_version") or 0) != REVIEW_POLICY_VERSION:
        return False
    if not review.get("keep"):
        return True
    if review.get("category") not in CATEGORIES:
        return False
    reason = str(review.get("reason") or "").lower()
    suspicious = ["fallback", "不匹配", "无关", "不属于", "内容不符", "off-category"]
    return (
        int(review.get("confidence") or 0) >= 7
        and int(review.get("quality_score") or 0) >= 65
        and int(review.get("innovation") or 0) >= 6
        and not any(word in reason for word in suspicious)
    )


def clamp_score(value):
    return max(0, min(10, int(round(float(value or 0)))))


def quality_score(row):
    return int(round(sum(clamp_score(row.get(key)) * 10 * weight for key, weight in QUALITY_WEIGHTS.items())))


def quality_gate(row, category):
    relevance = clamp_score(row.get("relevance"))
    innovation = clamp_score(row.get("innovation"))
    functionality = clamp_score(row.get("functionality"))
    clarity = clamp_score(row.get("clarity"))
    price_power = clamp_score(row.get("price_power"))
    total = quality_score(row)
    installation_exception = category == "装置艺术" and innovation >= 8 and clarity >= 5
    return (
        relevance >= 7
        and total >= 65
        and innovation >= 6
        and functionality >= 5
        and clarity >= 5
        and (price_power >= 5 or installation_exception)
    )


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
        "url": item.get("url", "")[:240],
        "image": item.get("image", "")[:240],
        "price_gate": item.get("price_gate", "unknown"),
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
                "relevance": 0,
                "utility": 0,
                "frequency": 0,
                "broad_appeal": 0,
                "functionality": 0,
                "innovation": 0,
                "price_power": 0,
                "clarity": 0,
                "emotion": 0,
                "quality_score": 0,
                "reason": "short, concrete reason",
            }
        ]
    }
    rules = "\n".join(f"- {category}: {CATEGORY_REVIEW_RULES[category]}" for category in CATEGORIES)
    prompt = f"""
你是严格的产品选品审核员。目标不是凑数量，而是只保留品类正确、真实具体、值得团队讨论的创意产品。

审核规则：
1. 只允许以下 {len(CATEGORIES)} 个品类；相关性 relevance 低于 7 必须 keep=false。
2. 必须是明确、具体的产品或可转化物件。建筑新闻、汽车、宠物用品、泛设计文章、合集、搜索页、话题页、用户页、首页、纯概念叙事必须删除。
3. 原品类错误但明确属于另一个允许品类时可以修正；不能因为标题或搜索词出现 bag、case、outdoor、lamp 等单词就硬归类。
4. 分别评估实用性、高频需求、打击面、功能完整度、创新增量、价格空间、3 秒看懂、情绪价值，所有分数 0-10。
5. 创新增量必须清楚：至少在功能、结构、材料、交互、视觉、包装或使用场景中有一项明显不同。普通基础款、只换颜色/图案/品牌、没有亮点的常规产品，innovation 不得超过 5 且 keep=false。
6. 普通产品必须同时满足：quality_score >= 65、innovation >= 6、functionality >= 5、clarity >= 5、price_power >= 5。
7. 装置艺术只作为方向参考：必须 innovation >= 8，并能明确提炼为产品结构、交互、光影、材料或内容创意；单纯建筑或大型公共项目不保留。
8. 礼盒与包装必须有明确的结构、开箱、复用、材料或叙事创新；只有平面视觉或普通盒型不保留。
9. 社媒内容可保留高热度、好看、有趣、种草、DIY/手作/改造或概念原型，但仍必须有明确物件和可转化启发。
10. 宁可少收，也不要为了达到数量保留弱相关、低创新、信息不完整的内容。

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
        "max_tokens": 7000,
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
    if category in RETIRED_CATEGORIES:
        return retirement_review(item)
    keywords = CATEGORY_KEYWORDS.get(category, [])
    title = item.get("title", "").lower()
    matched = [word for word in keywords if word.lower() in title]
    return {
        "id": item.get("id"),
        "keep": False,
        "category": "",
        "confidence": 0,
        "reason": "AI 审核失败，已隔离等待重试" + (f"；标题命中 {matched[:2]}" if matched else ""),
    }


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
        category = row.get("category") if row.get("category") in CATEGORIES else ""
        scores = {key: clamp_score(row.get(key)) for key in QUALITY_FIELDS}
        total = quality_score(row)
        keep = bool(row.get("keep")) and bool(category) and quality_gate(row, category)
        reviews[item_id] = {
            "keep": keep,
            "category": category if keep else "",
            "confidence": clamp_score(row.get("confidence")),
            "relevance": clamp_score(row.get("relevance")),
            **scores,
            "quality_score": total,
            "reason": str(row.get("reason") or "")[:320],
            "reviewed_at": now_iso(),
            "source": "deepseek" if os.environ.get("DEEPSEEK_API_KEY", "") else "local_fallback",
            "policy_version": REVIEW_POLICY_VERSION,
        }
    for item in batch:
        if item.get("id") not in reviews:
            reviews[item.get("id")] = local_fallback(item)


def review_products(products, batch_size=20, force=False, sleep=0.5):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    existing = load_json(DATA_DIR / "category_review.json", {})
    reviews = {} if force else dict(existing.get("reviews", {}))
    for item in products:
        if item.get("category") in RETIRED_CATEGORIES:
            reviews[item.get("id")] = retirement_review(item)
    todo = [
        item
        for item in products
        if item.get("category") not in RETIRED_CATEGORIES
        and (
            force
            or item.get("first_seen") == today()
            or not trusted_cached_review(reviews.get(item.get("id")))
        )
    ]

    batches = [todo[start : start + batch_size] for start in range(0, len(todo), batch_size)]
    workers = max(1, int(os.environ.get("CATEGORY_REVIEW_WORKERS", "1")))
    done = 0
    if workers == 1:
        for batch in batches:
            result = review_one_batch(batch, api_key)
            apply_batch_reviews(batch, result, reviews)
            done += len(batch)
            write_json(DATA_DIR / "category_review.json", {"generated_at": now_iso(), "policy_version": REVIEW_POLICY_VERSION, "reviews": reviews})
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
                write_json(DATA_DIR / "category_review.json", {"generated_at": now_iso(), "policy_version": REVIEW_POLICY_VERSION, "reviews": reviews})
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
                "quality_score": review.get("quality_score", 0),
                "innovation": review.get("innovation", 0),
                "relevance": review.get("relevance", 0),
                "policy_version": review.get("policy_version", REVIEW_POLICY_VERSION),
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
                "quality_score": review.get("quality_score", 0),
                "innovation": review.get("innovation", 0),
                "relevance": review.get("relevance", 0),
                "policy_version": review.get("policy_version", REVIEW_POLICY_VERSION),
            }
            rejected.append(clone)

    write_json(DATA_DIR / "category_review.json", {"generated_at": now_iso(), "policy_version": REVIEW_POLICY_VERSION, "reviews": reviews})
    rejected_by_id = {
        item.get("id"): item
        for item in load_json(DATA_DIR / "rejected_category.json", [])
        if item.get("id")
    }
    rejected_by_id.update({item.get("id"): item for item in rejected if item.get("id")})
    write_json(DATA_DIR / "rejected_category.json", list(rejected_by_id.values()))
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
    parser.add_argument("--workers", type=int, default=int(os.environ.get("CATEGORY_REVIEW_WORKERS", "1")))
    args = parser.parse_args()

    os.environ["CATEGORY_REVIEW_WORKERS"] = str(args.workers)
    products = load_json(DATA_DIR / "products.json", [])
    review_products(products, args.batch_size, args.force)


if __name__ == "__main__":
    main()
