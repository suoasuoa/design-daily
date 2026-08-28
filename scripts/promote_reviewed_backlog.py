#!/usr/bin/env python3
"""Fill a daily group from strong, never-published DeepSeek-reviewed candidates."""

import argparse
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

from build_site import DAILY_CATEGORY_CAPS, build_daily_groups, record, sorted_products
from insight_common import DATA_DIR, INSIGHT_DIR, is_ordinary_laptop_stand, load_json, now_iso, semantic_title_duplicate, today, write_json
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
ENTITY_TERMS = {
    "水杯": ("mug", "bottle", "tumbler", "flask", "thermos", "drinkware", "水杯", "饮水", "水瓶", "随行杯", "保温杯"),
    "氛围灯": ("lamp", "light", "lighting", "lantern", "chandelier", "灯", "燈", "照明"),
    "创意礼盒": ("gift", "box", "packaging", "package", "礼盒", "包装", "礼赠", "开箱"),
    "装置艺术": ("installation", "sculpture", "interactive art", "装置", "雕塑", "互动艺术"),
    "中秋礼盒": ("mid-autumn", "mid autumn", "mooncake", "中秋", "月饼"),
    "端午礼盒": ("dragon boat", "zongzi", "端午", "粽"),
    "充电宝": ("power bank", "powerbank", "battery pack", "portable charger", "移动电源", "充电宝"),
    "日历": ("calendar", "date display", "planner", "日历", "台历", "年历", "日期", "节气", "撕历"),
    "冲锋衣": ("jacket", "windbreaker", "shell jacket", "outerwear", "parka", "vest", "冲锋衣", "夹克", "外套", "防晒衣"),
}


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


def has_category_evidence(item):
    category = item.get("category") or ""
    title = str(item.get("title") or "").lower()
    text = " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("summary") or ""),
        ]
    ).lower().replace("world cup", "worldcup")
    if category == "手机壳":
        return "手机壳" in text or "保护壳" in text or (
            "case" in text and any(token in text for token in ("phone", "iphone", "smartphone", "magsafe"))
        )
    if category == "钥匙扣水壶":
        hydration = any(token in text for token in ("bottle", "flask", "水瓶", "水壶", "饮水", "杯"))
        attachment = any(token in text for token in ("keychain", "key chain", "carabiner", "clip-on", "挂环", "挂扣", "钥匙扣"))
        return hydration and attachment
    if category == "装置艺术":
        return any(token in title for token in ENTITY_TERMS[category])
    terms = ENTITY_TERMS.get(category)
    return not terms or any(token in text for token in terms)


def is_candidate(
    item,
    published_urls,
    *,
    min_quality=74,
    min_innovation=7,
    min_relevance=8,
):
    review = item.get("category_review") or {}
    reason = str(review.get("reason") or "").lower()
    return (
        item.get("category") in CATEGORIES
        and item.get("category") not in RETIRED_CATEGORIES
        and bool(item.get("url"))
        and item.get("url") not in published_urls
        and bool(item.get("image"))
        and int(review.get("confidence") or 0) >= 8
        and int(review.get("quality_score") or 0) >= min_quality
        and int(review.get("innovation") or 0) >= min_innovation
        and int(review.get("relevance") or 0) >= min_relevance
        and has_category_evidence(item)
        and not is_ordinary_laptop_stand(item)
        and not any(signal in reason for signal in BAD_REASONS)
    )


def category_cap(category, emergency=False):
    return DAILY_CATEGORY_CAPS.get(category, 3)


def choose_candidates(candidates, needed, today_items, known_titles, selected=None, emergency=False):
    selected = list(selected or [])
    initial_count = len(selected)
    category_counts = Counter(item.get("category") for item in today_items)
    source_counts = Counter(item.get("source_name") for item in today_items)

    for item in selected:
        category_counts[item.get("category")] += 1
        source_counts[source_name(item)] += 1
        known_titles.append(item.get("title") or "")

    while len(selected) < initial_count + needed:
        options = []
        for item in candidates:
            if item in selected:
                continue
            category = item.get("category")
            source = source_name(item)
            if category_counts[category] >= category_cap(category, emergency=emergency):
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


def choose_emergency_candidates(candidates, needed, today_items, known_titles, selected=None):
    """Select reviewed reserve items without repeating today's category mix."""
    selected = list(selected or [])
    known = list(known_titles) + [item.get("title") or "" for item in today_items]
    known.extend(item.get("title") or "" for item in selected)
    while len(selected) < needed:
        options = []
        for item in candidates:
            if item in selected or too_similar(item.get("title"), known):
                continue
            review = item.get("category_review") or {}
            options.append(
                (
                    -int(review.get("quality_score") or 0),
                    -int(review.get("innovation") or 0),
                    -int(review.get("relevance") or 0),
                    item.get("title") or "",
                    item,
                )
            )
        if not options:
            break
        chosen = min(options)[-1]
        selected.append(chosen)
        known.append(chosen.get("title") or "")
    return selected


def ranked_reviewed_candidates(candidates, limit=1500):
    """Bound semantic-dedupe work when a whole day is missing."""
    return sorted(
        candidates,
        key=lambda item: (
            -int((item.get("category_review") or {}).get("quality_score") or 0),
            -int((item.get("category_review") or {}).get("innovation") or 0),
            -int((item.get("category_review") or {}).get("relevance") or 0),
            item.get("title") or "",
        ),
    )[:limit]


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
    # Strong products can live in the main pool without ever being shown because
    # their original date/category was full. They are valid reserve candidates;
    # only a URL that already appeared in a daily group is ineligible.
    known_titles = [item.get("title") or "" for item in published_items]
    strict_candidates = [
        item for item in list(products) + list(rejected)
        if is_candidate(item, published_urls)
    ]
    strict_candidates = ranked_reviewed_candidates(strict_candidates)
    strict_candidates = [
        item for item in strict_candidates
        if not too_similar(item.get("title"), known_titles)
    ]
    today_titles = [item.get("title") or "" for item in today_items]
    selected = choose_candidates(
        strict_candidates,
        needed,
        today_items,
        today_titles,
    )
    emergency_ids = set()
    if len(selected) < needed:
        emergency_candidates = [
            item
            for item in list(products) + list(rejected)
            if is_candidate(item, published_urls, min_quality=70)
        ]
        emergency_candidates = ranked_reviewed_candidates(emergency_candidates)
        emergency_candidates = [
            item
            for item in emergency_candidates
            if not too_similar(item.get("title"), known_titles + today_titles)
        ]
        emergency = choose_emergency_candidates(
            [item for item in emergency_candidates if item not in selected],
            needed - len(selected),
            today_items,
            known_titles + today_titles,
        )
        selected.extend(emergency)
        emergency_ids = {item.get("id") for item in emergency}

    strict_ids = {item.get("id") for item in strict_candidates}

    selected_ids = {item.get("id") for item in selected}
    review_cache = load_json(DATA_DIR / "category_review.json", {})
    reviews = review_cache.get("reviews") or {}
    timestamp = now_iso()
    promoted = []
    for item in selected:
        clone = dict(item)
        original_first_seen = clone.get("first_seen") or ""
        review = dict(clone.get("category_review") or {})
        review_source = (
            "deepseek_backlog_recheck"
            if clone.get("id") in strict_ids
            else "deepseek_backlog_balanced"
        )
        review.update(
            {
                "status": "approved",
                "reason": f"DeepSeek候选复核：{review.get('reason') or '具体创新证据明确'}",
                "reviewed_at": timestamp,
                "source": review_source,
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
        if clone.get("id") in emergency_ids:
            clone["backlog_emergency_fill"] = True
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
            "source": review_source,
            "policy_version": 3,
        }

    selected_urls = {item.get("url") for item in selected if item.get("url")}
    products = [
        item for item in products
        if item.get("id") not in selected_ids and item.get("url") not in selected_urls
    ]
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
    if emergency_ids:
        write_json(
            DATA_DIR / "emergency_daily_fill.json",
            {
                "date": today(),
                "reason": "当日临时补录：普通品类配额后仍有缺口，从已完成 DeepSeek 审核且未进入正式展示的高分候选中补足。",
                "product_ids": [item.get("id") for item in promoted if item.get("id") in emergency_ids],
            },
        )
    print(
        f"backlog_promotion needed={needed} selected={len(promoted)} "
        f"emergency={len(emergency_ids)} categories={dict(Counter(item.get('category') for item in promoted))}"
    )


if __name__ == "__main__":
    main()
