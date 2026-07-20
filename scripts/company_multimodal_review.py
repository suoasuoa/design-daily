#!/usr/bin/env python3
"""Use the internal GPT-5.5 gateway to visually audit same-day products."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os

from company_gpt import CompanyGPTClient, CompanyGPTError
from insight_common import DATA_DIR, load_env, load_json, now_iso, today, write_json
from insight_config import CATEGORIES, CATEGORY_REVIEW_RULES, RETIRED_CATEGORIES
from review_categories import QUALITY_FIELDS, REVIEW_POLICY_VERSION, build_published, quality_score


COMPANY_REVIEW_VERSION = 1
COMPANY_REVIEW_SOURCE = "company_gpt_multimodal"


def clamp_score(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0
    if 0 < value <= 1:
        value *= 10
    return max(0, min(10, int(round(value))))


def compact_product(item):
    return {
        "id": item.get("id"),
        "title": str(item.get("title") or "")[:180],
        "current_category": item.get("category") or "",
        "summary": str(item.get("summary") or "")[:700],
        "tags": (item.get("tags") or [])[:12],
        "price_gate": item.get("price_gate") or "unknown",
        "source": item.get("source_primary") or "",
        "url": item.get("url") or "",
        "image": item.get("image") or "",
    }


def review_messages(item):
    product = compact_product(item)
    rules = "\n".join(f"- {category}: {CATEGORY_REVIEW_RULES[category]}" for category in CATEGORIES)
    schema = {
        "id": product["id"],
        "keep": True,
        "category": "one allowed category",
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
        "image_status": "loaded/missing/unreadable",
        "product_visible": True,
        "title_image_match": 0,
        "visual_evidence": "specific visible evidence",
        "reason": "specific product-selection reason or rejection reason",
    }
    prompt = f"""
你是选品团队的最终多模态审核员。请同时检查产品文字、图片和链接信息，目标是阻止错图、错品类、普通基础款和弱创意进入每日40条。

硬规则：
1. 只允许下列品类。必须按图片中真实物件和实际用途归类，不能按搜索词硬贴标签。
2. 图片成功加载时，必须确认图片中存在明确产品，且图片与标题匹配；不匹配、纯建筑/汽车/人物/海报或无明确产品时 keep=false。
3. 必须有可说清楚的功能、结构、材料、交互、包装、视觉机制或使用场景创新。普通基础款、只换色/图案/品牌、常规联名，innovation<=5 且 keep=false。
4. 实用性、高频需求、功能完整度和广泛受众优先；价格空间原则上应支持人民币35元以上。
5. 装置艺术只作方向参考，必须能提炼出明确的结构、互动、光影、材料或内容启发。
6. 社媒、DIY和概念产品可以保留，但必须有明确物件、明显创意和可转化启发。
7. 图片无法读取时如实填写 image_status=unreadable，不得臆造视觉证据；仍可根据充分的文字证据审核。
8. reason和visual_evidence必须具体，不能只写“有设计感”“很创新”。
9. confidence、relevance、title_image_match以及所有选品评分必须输出0到10的整数，禁止使用0到1小数。

品类定义：
{rules}

产品数据：
{json.dumps(product, ensure_ascii=False)}

只返回合法JSON：
{json.dumps(schema, ensure_ascii=False)}
"""
    content = [{"type": "text", "text": prompt}]
    image = product.get("image") or ""
    if image.startswith(("http://", "https://")):
        content.append({"type": "image_url", "image_url": {"url": image}})
    return [
        {"role": "system", "content": "你是严格的多模态选品审核员，只输出合法JSON。"},
        {"role": "user", "content": content},
    ]


def normalize_review(item, row, usage=None):
    category = row.get("category") if row.get("category") in CATEGORIES else ""
    scores = {key: clamp_score(row.get(key)) for key in QUALITY_FIELDS}
    total = quality_score(scores)
    confidence = clamp_score(row.get("confidence"))
    relevance = clamp_score(row.get("relevance"))
    image_status = str(row.get("image_status") or ("missing" if not item.get("image") else "unreadable")).lower()
    product_visible = bool(row.get("product_visible"))
    title_image_match = clamp_score(row.get("title_image_match"))

    base_gate = (
        bool(row.get("keep"))
        and bool(category)
        and category not in RETIRED_CATEGORIES
        and confidence >= 8
        and relevance >= 8
        and scores["innovation"] >= 7
        and scores["functionality"] >= 6
        and scores["clarity"] >= 6
        and total >= 70
        and (scores["price_power"] >= 5 or category == "装置艺术")
    )
    visual_gate = True
    if image_status == "loaded":
        visual_gate = product_visible and title_image_match >= 7
    keep = base_gate and visual_gate

    reason = str(row.get("reason") or "").strip()[:420]
    if not reason:
        reason = "多模态审核没有返回可核验的具体理由"
        keep = False
    return {
        "id": item.get("id"),
        "keep": keep,
        "category": category if keep else "",
        "suggested_category": category,
        "confidence": confidence,
        "relevance": relevance,
        **scores,
        "quality_score": total,
        "image_status": image_status,
        "product_visible": product_visible,
        "title_image_match": title_image_match,
        "visual_evidence": str(row.get("visual_evidence") or "")[:420],
        "reason": reason,
        "reviewed_at": now_iso(),
        "source": COMPANY_REVIEW_SOURCE,
        "policy_version": REVIEW_POLICY_VERSION,
        "company_review_version": COMPANY_REVIEW_VERSION,
        "usage": usage or {},
    }


def review_one(item, client):
    row, usage = client.chat_json(review_messages(item), max_tokens=1800, temperature=0)
    if row.get("id") not in {None, "", item.get("id")}:
        raise CompanyGPTError(f"review id mismatch expected={item.get('id')} actual={row.get('id')}")
    return normalize_review(item, row, usage)


def cached_review_is_current(review):
    return (
        isinstance(review, dict)
        and review.get("source") == COMPANY_REVIEW_SOURCE
        and int(review.get("company_review_version") or 0) == COMPANY_REVIEW_VERSION
    )


def apply_reviews(products, decisions, review_date):
    category_payload = load_json(DATA_DIR / "category_review.json", {})
    category_reviews = dict(category_payload.get("reviews", {}))
    rejected_by_id = {
        item.get("id"): item
        for item in load_json(DATA_DIR / "rejected_category.json", [])
        if item.get("id")
    }
    kept = []
    rejected = []
    recategorized = 0
    for item in products:
        decision = decisions.get(item.get("id"))
        if not decision:
            kept.append(item)
            continue
        category_reviews[item.get("id")] = decision
        if decision.get("keep"):
            if item.get("category") != decision.get("category"):
                item["company_review_original_category"] = item.get("category")
                item["category"] = decision["category"]
                recategorized += 1
            item["company_multimodal_review"] = decision
            item["selection_scores"] = {
                **{key: decision.get(key, 0) for key in QUALITY_FIELDS},
                "source": COMPANY_REVIEW_SOURCE,
                "reason": decision.get("reason", ""),
                "visual_evidence": decision.get("visual_evidence", ""),
                "title_image_match": decision.get("title_image_match", 0),
            }
            item["selection_score"] = decision.get("quality_score", 0)
            item["ai_reason"] = decision.get("reason", "")
            item["status"] = "scored"
            item["updated_at"] = now_iso()
            kept.append(item)
        else:
            clone = dict(item)
            clone["company_multimodal_review"] = decision
            rejected.append(clone)
            rejected_by_id[item.get("id")] = clone

    write_json(
        DATA_DIR / "category_review.json",
        {
            "generated_at": now_iso(),
            "policy_version": REVIEW_POLICY_VERSION,
            "reviews": category_reviews,
        },
    )
    write_json(DATA_DIR / "rejected_category.json", list(rejected_by_id.values()))
    write_json(DATA_DIR / "products.json", kept)
    write_json(DATA_DIR / "published.json", build_published(kept))

    report_path = DATA_DIR / "company_multimodal_review.json"
    report = load_json(report_path, {"reviews": {}, "daily": {}})
    report.setdefault("reviews", {}).update(decisions)
    reviewed_today = [row for row in decisions.values() if row.get("reviewed_at", "").startswith(review_date)]
    report.setdefault("daily", {})[review_date] = {
        "generated_at": now_iso(),
        "reviewed": len(reviewed_today),
        "kept": sum(bool(row.get("keep")) for row in reviewed_today),
        "rejected": sum(not bool(row.get("keep")) for row in reviewed_today),
        "by_category": dict(Counter(row.get("category") for row in reviewed_today if row.get("keep"))),
    }
    report["generated_at"] = now_iso()
    report["policy_version"] = COMPANY_REVIEW_VERSION
    write_json(report_path, report)
    return kept, rejected, recategorized


def run_review(review_date=None, limit=0, workers=3, force=False, dry_run=False):
    load_env()
    review_date = review_date or today()
    products = load_json(DATA_DIR / "products.json", [])
    report = load_json(DATA_DIR / "company_multimodal_review.json", {"reviews": {}})
    cached = report.get("reviews", {})
    candidates = [item for item in products if item.get("first_seen") == review_date]
    if not force:
        candidates = [item for item in candidates if not cached_review_is_current(cached.get(item.get("id")))]
    if limit:
        candidates = candidates[:limit]
    if not candidates:
        print(f"company_review=skipped date={review_date} reason=no_new_candidates")
        return {"reviewed": 0, "kept": 0, "rejected": 0, "remaining": len(products)}

    client = CompanyGPTClient()
    decisions = {}
    failures = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_to_item = {executor.submit(review_one, item, client): item for item in candidates}
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                decision = future.result()
                decisions[item.get("id")] = decision
                print(
                    f"company_review item={item.get('id')} keep={decision.get('keep')} "
                    f"category={decision.get('category') or decision.get('suggested_category')} "
                    f"quality={decision.get('quality_score')} image={decision.get('image_status')}",
                    flush=True,
                )
            except Exception as exc:
                failures.append({"id": item.get("id"), "error": str(exc)[:300]})
                print(f"company_review_retry_later item={item.get('id')} error={exc}", flush=True)

    if dry_run:
        summary = {
            "reviewed": len(decisions),
            "kept": sum(bool(row.get("keep")) for row in decisions.values()),
            "rejected": sum(not bool(row.get("keep")) for row in decisions.values()),
            "failures": failures,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return summary

    kept, rejected, recategorized = apply_reviews(products, decisions, review_date)
    summary = {
        "reviewed": len(decisions),
        "kept": sum(bool(row.get("keep")) for row in decisions.values()),
        "rejected": len(rejected),
        "recategorized": recategorized,
        "failures": len(failures),
        "remaining": len(kept),
    }
    print("company_review=" + json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="", help="Asia/Shanghai review date; defaults to today.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_review(args.date or None, args.limit, args.workers, args.force, args.dry_run)


if __name__ == "__main__":
    main()
