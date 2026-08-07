#!/usr/bin/env python3
"""Fill a daily group from strong, never-published DeepSeek-reviewed candidates."""

import argparse
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

from build_site import DAILY_CATEGORY_CAPS, build_daily_groups, record, sorted_products
from insight_common import DATA_DIR, INSIGHT_DIR, load_json, now_iso, semantic_title_duplicate, today, write_json
from insight_config import CATEGORIES, RETIRED_CATEGORIES


BAD_REASONS = (
    "品类已于",
    "不是可直达",
    "泛合集",
    "团队 pass",
    "非产品",
    "不是",
    "非实体",
    "信息不足",
    "无法确认",
    "缺乏",
    "普通",
    "常规",
    "无法",
    "不属于",
    "不符合",
    "相关性低",
    "仅为",
    "仅是",
    "仅增加",
    "纯概念",
    "缺少能够",
    "图片与标题不匹配",
    "图片不匹配",
    "错图",
    "质量评分不足",
    "score below",
    "创新不足",
    "创新增量有限",
    "实用化不确定",
    "品类应为",
    "品类错误",
    "非目标品类",
    "无具体创新",
    "未体现",
    "无实物",
    "不完整",
    "语义去重",
    "高度相似",
)
TITLE_NOISE = re.compile(
    r"\b(yanko design|dieline|uncrate|core77|designboom|design milk|behance|"
    r"adobe inc|pinterest|facebook|susi|if design|good design award)\b",
    re.IGNORECASE,
)
HARD_CAPS = {"手机壳", "充电宝"}


def dashboard_payload():
    path = INSIGHT_DIR / "data.json"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if "=" in text:
        text = text.split("=", 1)[1].strip().rstrip(";")
    return json.loads(text)


def core_title(value):
    value = unicodedata.normalize("NFKC", value or "").lower()
    value = TITLE_NOISE.sub(" ", value)
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value)
    return " ".join(value.split())


def title_tokens(value):
    return {token for token in core_title(value).split() if len(token) > 1}


def too_similar(title, known_titles):
    core = core_title(title)
    tokens = title_tokens(title)
    if not core:
        return True
    for known in known_titles:
        if semantic_title_duplicate(title, known):
            return True
        other = core_title(known)
        if core == other:
            return True
        length_ratio = min(len(core), len(other)) / max(len(core), len(other), 1)
        if (
            length_ratio >= 0.72
            and len(core) >= 12
            and len(other) >= 12
            and SequenceMatcher(None, core, other).ratio() >= 0.90
        ):
            return True
        other_tokens = title_tokens(known)
        union = tokens | other_tokens
        if union and len(tokens & other_tokens) / len(union) >= 0.78:
            return True
    return False


def source_name(item):
    source = item.get("source_primary") or {}
    if isinstance(source, dict):
        return source.get("source") or "其他来源"
    return str(source or "其他来源")


def clean_candidate_title(value):
    value = str(value or "").strip()
    for marker in (" :: Behance", " - DIELINE", " | Uncrate", " | Grommet"):
        if marker in value:
            value = value.split(marker, 1)[0].strip()
    value = re.sub(r"\s+-\s+Yanko Design$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+-\s+Core77 Design Awards$", "", value, flags=re.IGNORECASE)
    return value or "未命名产品"


def is_candidate(item, published_urls, product_urls):
    review = item.get("category_review") or {}
    reason = str(review.get("reason") or "").lower()
    return (
        item.get("category") in CATEGORIES
        and item.get("category") not in RETIRED_CATEGORIES
        and bool(item.get("url"))
        and item.get("url") not in published_urls
        and item.get("url") not in product_urls
        and bool(item.get("image"))
        and int(review.get("confidence") or 0) >= 8
        and int(review.get("quality_score") or 0) >= 65
        and int(review.get("innovation") or 0) >= 8
        and int(review.get("relevance") or 0) >= 8
        and not any(signal in reason for signal in BAD_REASONS)
    )


def category_cap(category):
    base = DAILY_CATEGORY_CAPS.get(category, 3)
    return base if category in HARD_CAPS else base + 2


def choose_candidates(candidates, needed, today_items, known_titles):
    selected = []
    category_counts = Counter(item.get("category") for item in today_items)
    source_counts = Counter(item.get("source_name") for item in today_items)

    while len(selected) < needed:
        options = []
        for item in candidates:
            if item in selected:
                continue
            category = item.get("category")
            source = source_name(item)
            if category_counts[category] >= category_cap(category):
                continue
            if source_counts[source] >= 5:
                continue
            if too_similar(item.get("title"), known_titles):
                continue
            review = item.get("category_review") or {}
            options.append(
                (
                    category_counts[category],
                    source_counts[source],
                    -int(review.get("quality_score") or 0),
                    -int(review.get("innovation") or 0),
                    item.get("title") or "",
                    item,
                )
            )
        if not options:
            break
        chosen = min(options)[-1]
        selected.append(chosen)
        category_counts[chosen.get("category")] += 1
        source_counts[source_name(chosen)] += 1
        known_titles.append(chosen.get("title") or "")

    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=40)
    args = parser.parse_args()

    products = load_json(DATA_DIR / "products.json", [])
    rejected = load_json(DATA_DIR / "rejected_category.json", [])
    payload = dashboard_payload()
    previous_groups = payload.get("daily_groups") or []
    current_groups = build_daily_groups(
        [record(item) for item in sorted_products(products)],
        per_day=max(40, args.target),
        max_days=1,
        previous_groups=previous_groups,
    )
    today_items = []
    for group in current_groups:
        if group.get("date") == today():
            today_items = list(group.get("items") or [])
            break

    needed = max(0, args.target - len(today_items))
    if not needed:
        print(f"backlog_promotion skipped count={len(today_items)} target={args.target}")
        return

    published_items = [item for group in previous_groups for item in group.get("items", [])]
    published_urls = {item.get("url") for item in published_items if item.get("url")}
    product_urls = {item.get("url") for item in products if item.get("url")}
    known_titles = [item.get("title") or "" for item in published_items]
    known_titles.extend(item.get("title") or "" for item in products)
    candidates = [
        item for item in rejected
        if is_candidate(item, published_urls, product_urls)
    ]
    candidates = [
        item for item in candidates
        if not too_similar(item.get("title"), known_titles)
    ]
    selected = choose_candidates(candidates, needed, today_items, [])

    selected_ids = {item.get("id") for item in selected}
    review_cache = load_json(DATA_DIR / "category_review.json", {})
    reviews = review_cache.get("reviews") or {}
    timestamp = now_iso()
    promoted = []
    for item in selected:
        clone = dict(item)
        original_first_seen = clone.get("first_seen") or ""
        review = dict(clone.get("category_review") or {})
        review.update(
            {
                "status": "approved",
                "reason": f"DeepSeek候选复核：{review.get('reason') or '具体创新证据明确'}",
                "reviewed_at": timestamp,
                "source": "deepseek_backlog_recheck",
                "policy_version": 3,
                "backlog_promotion": True,
                "original_first_seen": original_first_seen,
            }
        )
        clone["category_review"] = review
        clone["title"] = clean_candidate_title(clone.get("title"))
        clone["first_seen"] = today()
        clone["last_seen"] = today()
        clone["updated_at"] = timestamp
        clone["status"] = "scored"
        promoted.append(clone)
        reviews[clone.get("id")] = {
            "id": clone.get("id"),
            "keep": True,
            "category": clone.get("category"),
            "confidence": int(review.get("confidence") or 8),
            "quality_score": int(review.get("quality_score") or 0),
            "relevance": int(review.get("relevance") or 0),
            "innovation": int(review.get("innovation") or 0),
            "functionality": int(review.get("functionality") or 0),
            "clarity": int(review.get("clarity") or 0),
            "price_power": int(review.get("price_power") or 0),
            "reason": review.get("reason"),
            "reviewed_at": timestamp,
            "source": "deepseek_backlog_recheck",
            "policy_version": 3,
        }

    products.extend(promoted)
    rejected = [item for item in rejected if item.get("id") not in selected_ids]
    write_json(DATA_DIR / "products.json", products)
    write_json(DATA_DIR / "rejected_category.json", rejected)
    write_json(
        DATA_DIR / "category_review.json",
        {
            "generated_at": timestamp,
            "policy_version": 3,
            "reviews": reviews,
        },
    )
    print(
        f"backlog_promotion needed={needed} selected={len(promoted)} "
        f"categories={dict(Counter(item.get('category') for item in promoted))}"
    )


if __name__ == "__main__":
    main()
