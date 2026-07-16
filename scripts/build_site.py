#!/usr/bin/env python3
"""Build a tabbed selection intelligence workspace."""

from collections import Counter, defaultdict
import json
import re
from urllib.parse import urlparse

from insight_common import clean_direct_product_url, DATA_DIR, INSIGHT_DIR, ensure_dirs, load_json, now_iso, source_quality, source_type, write_json
from insight_config import CATEGORIES, RETIRED_CATEGORIES


FUNCTION_WORDS = [
    "便携", "portable", "防水", "waterproof", "收纳", "storage", "模块", "modular",
    "充电", "charge", "磁吸", "magnetic", "折叠", "foldable", "多功能", "multifunction",
]
PACKAGING_WORDS = ["包装", "packaging", "box", "gift", "礼盒", "套装", "mooncake", "中秋", "端午"]
STRUCTURE_WORDS = ["结构", "structure", "支架", "frame", "fold", "hinge", "assembly", "模块", "shelf"]
EMOTION_WORDS = ["可爱", "cute", "温暖", "warm", "治愈", "playful", "surprise", "惊喜", "趣味", "幽默", "氛围"]
VISUAL_WORDS = ["纹理", "texture", "color", "颜色", "graphic", "图形", "surface", "材质", "finish"]
DAILY_SOURCE_QUOTAS = {
    "奖项案例": 8,
    "媒体案例": 6,
    "包装专项": 5,
    "设计社区": 5,
    "市场信号": 3,
    "弱市场信号": 1,
    "社交灵感": 3,
}
DAILY_CATEGORY_CAPS = {
    "创意礼盒": 3,
    "装置艺术": 3,
    "创意厨具": 3,
    "创意桌搭": 3,
    "氛围灯": 3,
    "水杯": 3,
    "中秋礼盒": 2,
    "端午礼盒": 2,
    "收纳包": 2,
    "T恤": 2,
    "卫衣": 2,
    "Polo衫": 2,
    "帽子": 2,
    "手机壳": 2,
    "卡包": 2,
    "钥匙扣水壶": 1,
    "充电宝": 2,
    "冲锋衣": 2,
}
DEFAULT_DAILY_CATEGORY_CAP = 2


def sorted_products(products):
    return sorted(
        products,
        key=lambda item: (
            int(item.get("selection_score") or 0),
            int(item.get("seen_count") or 0),
            item.get("last_seen") or "",
        ),
        reverse=True,
    )


def hits(text, words):
    text = text.lower()
    return sum(1 for word in words if word.lower() in text)


def source_family(item):
    source = (item.get("sources") or [{}])[0]
    source_type_value = source.get("source_type", "") or source_type(source.get("source", ""))
    quality = source_quality(
        source=source.get("source", ""),
        source_type_value=source_type_value,
        source_group=source.get("source_group", ""),
        quality_tier=source.get("quality_tier", "") or source.get("source_quality", ""),
    )
    if source_type_value == "social_signal":
        return "社交灵感"
    if source_type_value == "verified_official":
        return "奖项案例"
    if source_type_value == "editorial_source":
        return "媒体案例"
    if source_type_value == "packaging_source":
        return "包装专项"
    if source_type_value == "design_community":
        return "设计社区"
    if source_type_value == "market_reference":
        if quality == "weak":
            return "弱市场信号"
        return "市场信号"
    if source_type_value == "trend_source":
        return "弱市场信号" if quality == "weak" else "趋势观察"
    return "其他来源"


def source_quality_label(item):
    source = (item.get("sources") or [{}])[0]
    return source_quality(
        source=source.get("source", ""),
        source_type_value=source.get("source_type", "") or source_type(source.get("source", "")),
        source_group=source.get("source_group", ""),
        quality_tier=source.get("quality_tier", "") or source.get("source_quality", ""),
    )


def action_lane(item):
    category = item.get("category", "")
    source = (item.get("sources") or [{}])[0]
    source_type = source.get("source_type", "")
    price_gate = item.get("price_gate")
    score = int(item.get("selection_score") or 0)
    text = " ".join(
        [
            item.get("title", ""),
            item.get("summary", ""),
            " ".join(item.get("tags", [])),
            " ".join(item.get("trend_tags", [])),
        ]
    ).lower()

    if source_type == "social_signal" and price_gate == "likely_over_35" and score >= 60:
        return "可直接买样"
    if category in {"创意礼盒", "中秋礼盒", "端午礼盒", "创意厨具", "创意桌搭", "手机壳", "水杯"}:
        return "适合改造"
    if hits(text, PACKAGING_WORDS) >= 2 or category in {"创意礼盒", "中秋礼盒", "端午礼盒"}:
        return "适合改造"
    if source_type in {"verified_official", "editorial_source", "packaging_source", "design_community"}:
        return "方向参考"
    return "适合改造"


def inspiration_axes(item):
    text = " ".join(
        [
            item.get("title", ""),
            item.get("summary", ""),
            " ".join(item.get("tags", [])),
            " ".join(item.get("trend_tags", [])),
        ]
    ).lower()
    axes = []
    if hits(text, FUNCTION_WORDS) >= 1 or item.get("category") in {"创意厨具", "充电宝", "水杯", "收纳包"}:
        axes.append("功能启发")
    if hits(text, PACKAGING_WORDS) >= 1 or item.get("category") in {"创意礼盒", "中秋礼盒", "端午礼盒"}:
        axes.append("包装启发")
    if hits(text, STRUCTURE_WORDS) >= 1 or item.get("category") in {"创意桌搭", "装置艺术", "收纳包"}:
        axes.append("结构启发")
    if hits(text, EMOTION_WORDS) >= 1 or item.get("category") in {"氛围灯", "帽子"}:
        axes.append("情绪启发")
    if hits(text, VISUAL_WORDS) >= 1 or not axes:
        axes.append("视觉启发")
    return axes[:3]


def image_state(item):
    image = clean_image_url(item.get("image", ""))
    title = item.get("title", "").lower()
    if not image:
        return "缺图"
    review = item.get("category_review") or {}
    reason = (review.get("reason") or "").lower()
    if "图" in reason and ("不符" in reason or "不一致" in reason):
        return "待核图"
    if "packaging" in image.lower() and item.get("category") == "冲锋衣":
        return "待核图"
    if "image" in title or "render" in title:
        return "待核图"
    return "已对齐"


def clean_image_url(value):
    value = (value or "").strip()
    if value.startswith("//"):
        value = "https:" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    lowered = value.lower()
    blocked = ["sedoparking", "js_preloader", "placeholder", "blank.gif", "transparent.gif"]
    if any(token in lowered for token in blocked):
        return ""
    return value


def clean_product_url(value):
    return clean_direct_product_url(value)


def record(item):
    source = (item.get("sources") or [{}])[0]
    axes = inspiration_axes(item)
    review = item.get("category_review") or {}
    image = clean_image_url(item.get("image", ""))
    url = clean_product_url(item.get("url") or source.get("url") or "")
    return {
        "id": item.get("id"),
        "title": item.get("title", ""),
        "category": item.get("category", ""),
        "summary": item.get("ai_reason") or item.get("summary", ""),
        "score": int(item.get("selection_score") or 0),
        "price_gate": item.get("price_gate", "unknown"),
        "image": image,
        "url": url,
        "source_name": source.get("source", item.get("source_primary", "未知来源")),
        "source_family": source_family(item),
        "source_type": source.get("source_type", "") or source_type(source.get("source", "")),
        "source_quality": source_quality_label(item),
        "action_lane": action_lane(item),
        "axes": axes,
        "image_state": image_state(item),
        "seen_count": int(item.get("seen_count") or 0),
        "first_seen": item.get("first_seen", ""),
        "last_seen": item.get("last_seen", ""),
        "review_reason": review.get("reason", ""),
        "review_confidence": review.get("confidence", 0),
        "tags": (item.get("trend_tags") or [])[:4]
        + [tag for tag in (item.get("tags") or [])[:6] if tag not in (item.get("trend_tags") or [])][:2],
    }


def normalize_key(value):
    value = (value or "").lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"www\\.", "", value)
    value = re.sub(r"[^a-z0-9\\u4e00-\\u9fff]+", "", value)
    return value[:120]


def dedupe_key(item):
    return item.get("id") or normalize_key(item.get("url")) or normalize_key(item.get("title"))


RELAXABLE_CATEGORIES = set(DAILY_CATEGORY_CAPS)


def category_under_cap(picks, category, relaxed=False):
    category = (category or "").strip()
    cap = DAILY_CATEGORY_CAPS.get(category, DEFAULT_DAILY_CATEGORY_CAP)
    if relaxed and category in RELAXABLE_CATEGORIES:
        cap += 1
    current = sum(1 for item in picks if item.get("category") == category)
    return current < cap


def display_eligible(item):
    if item.get("category") in RETIRED_CATEGORIES:
        return False
    if not item.get("title"):
        return False
    if not item.get("url"):
        return False
    text = f"{item.get('summary', '')} {item.get('review_reason', '')}".lower()
    mismatch_signals = [
        "不匹配", "与品类无关", "不属于", "内容不符", "品类不符",
        "off-category", "local fallback", "ai 审核失败",
    ]
    if any(signal in text for signal in mismatch_signals):
        return False
    if int(item.get("review_confidence") or 0) < 4 and int(item.get("score") or 0) < 60:
        return False
    if str(item.get("summary") or "").lower().startswith("open web search result for") and int(item.get("score") or 0) < 60:
        return False
    if item.get("source_quality") == "weak":
        if not item.get("image"):
            return False
        score = int(item.get("score") or 0)
        if score < 72:
            return False
        if item.get("category") in {"T恤", "卫衣", "Polo衫", "帽子"} and score < 84:
            return False
    return True


def balanced_ranked_items(ranked, picks, seen):
    category_counts = Counter(item.get("category") or "未分类" for item in picks)
    family_counts = Counter(item.get("source_family") or "其他来源" for item in picks)
    quality_rank = {"premium": 0, "standard": 1, "weak": 2}

    def key(item):
        return (
            category_counts[item.get("category") or "未分类"],
            family_counts[item.get("source_family") or "其他来源"],
            quality_rank.get(item.get("source_quality") or "standard", 1),
            -(item.get("score") or 0),
            -(item.get("seen_count") or 0),
            item.get("title") or "",
        )

    return sorted(
        [item for item in ranked if dedupe_key(item) not in seen],
        key=key,
    )


def append_balanced_fill(ranked, picks, seen, per_day, relaxed=False):
    while len(picks) < per_day:
        chosen = None
        for item in balanced_ranked_items(ranked, picks, seen):
            if not category_under_cap(picks, item.get("category"), relaxed=relaxed):
                continue
            chosen = item
            break
        if not chosen:
            return
        seen.add(dedupe_key(chosen))
        picks.append(chosen)


def compact_weekly_report(report):
    if not report:
        return {}
    recommendations = []
    for item in report.get("recommendations", []):
        cleaned = dict(item)
        cleaned["image"] = clean_image_url(cleaned.get("image", ""))
        cleaned["url"] = clean_product_url(cleaned.get("url", ""))
        recommendations.append(cleaned)
    return {
        "generated_at": report.get("generated_at", ""),
        "week": report.get("week", ""),
        "group_id": report.get("group_id") or report.get("week", ""),
        "date_start": report.get("date_start", ""),
        "date_end": report.get("date_end", ""),
        "date_label": report.get("date_label", ""),
        "title": report.get("title", ""),
        "target_count": report.get("target_count", 100),
        "actual_count": report.get("actual_count", len(report.get("recommendations", []))),
        "summary": report.get("summary", ""),
        "stats": report.get("stats", {}),
        "recommendations": recommendations,
    }


def build_daily_groups(items, per_day=30, max_days=90):
    by_day = defaultdict(list)
    for item in items:
        by_day[item.get("first_seen") or item.get("last_seen") or "unknown"].append(item)

    groups = []
    for day in sorted(by_day.keys(), reverse=True)[:max_days]:
        seen = set()
        picks = []
        ranked = [
            item
            for item in sorted(by_day[day], key=lambda row: (row.get("score", 0), row.get("seen_count", 0)), reverse=True)
            if display_eligible(item)
        ]

        for family, quota in DAILY_SOURCE_QUOTAS.items():
            for item in ranked:
                if len([pick for pick in picks if pick["source_family"] == family]) >= quota:
                    break
                if item["source_family"] != family:
                    continue
                key = dedupe_key(item)
                if key in seen:
                    continue
                if not category_under_cap(picks, item.get("category")):
                    continue
                seen.add(key)
                picks.append(item)
                if len(picks) >= per_day:
                    break
            if len(picks) >= per_day:
                break

        append_balanced_fill(ranked, picks, seen, per_day, relaxed=False)
        append_balanced_fill(ranked, picks, seen, per_day, relaxed=True)

        groups.append(
            {
                "date": day,
                "group_id": f"daily-{day}",
                "title": f"{day} 每日情报收集",
                "target_count": per_day,
                "items": picks,
            }
        )

    # Historical groups are immutable daily snapshots. When stricter display rules
    # leave an old group short, fill it from eligible pool items that have never
    # appeared in any daily group. Keep the original first_seen value for audit.
    globally_seen = {
        dedupe_key(item)
        for group in groups
        for item in group["items"]
    }
    reserve = [
        item
        for item in sorted(items, key=lambda row: (row.get("score", 0), row.get("seen_count", 0)), reverse=True)
        if display_eligible(item) and dedupe_key(item) not in globally_seen
    ]
    backfill_date = now_iso()[:10]
    for group in groups[1:]:
        picks = group["items"]
        while len(picks) < per_day:
            chosen = None
            for item in balanced_ranked_items(reserve, picks, globally_seen):
                item_date = item.get("first_seen") or item.get("last_seen") or ""
                if item_date and item_date > group["date"]:
                    continue
                if not category_under_cap(picks, item.get("category"), relaxed=True):
                    continue
                chosen = item
                break
            if not chosen:
                break
            key = dedupe_key(chosen)
            globally_seen.add(key)
            archived = dict(chosen)
            archived["is_backfill"] = True
            archived["backfilled_at"] = backfill_date
            archived["original_first_seen"] = chosen.get("first_seen", "")
            picks.append(archived)

    for group in groups:
        picks = group["items"]
        by_source = Counter(item["source_family"] for item in picks)
        group["actual_count"] = len(picks)
        group["stats"] = {
            "by_lane": dict(Counter(item["action_lane"] for item in picks).most_common()),
            "by_category": dict(Counter(item["category"] for item in picks).most_common(12)),
            "by_source_family": dict(by_source.most_common()),
            "source_quota": DAILY_SOURCE_QUOTAS,
            "source_quota_fill": {
                family: min(by_source.get(family, 0), quota)
                for family, quota in DAILY_SOURCE_QUOTAS.items()
            },
            "backfill_count": sum(1 for item in picks if item.get("is_backfill")),
        }
    return groups


def build_payload(products, trends, weekly_report=None, weekly_groups=None):
    items = [record(item) for item in sorted_products(products)]
    by_category = Counter(item["category"] for item in items)
    by_lane = Counter(item["action_lane"] for item in items)
    by_axis = Counter(axis for item in items for axis in item["axes"])
    by_source_family = Counter(item["source_family"] for item in items)
    by_image_state = Counter(item["image_state"] for item in items)

    return {
        "generated_at": now_iso(),
        "stats": {
            "total_items": len(items),
            "by_category": dict(by_category.most_common()),
            "by_lane": dict(by_lane.most_common()),
            "by_axis": dict(by_axis.most_common()),
            "by_source_family": dict(by_source_family.most_common()),
            "by_image_state": dict(by_image_state.most_common()),
        },
        "trends": trends,
        "weekly_report": compact_weekly_report(weekly_report),
        "weekly_groups": [compact_weekly_report(report) for report in (weekly_groups or []) if report],
        "daily_groups": build_daily_groups(items),
        "configured_categories": CATEGORIES,
        "retired_categories": sorted(RETIRED_CATEGORIES),
        "items": items,
    }


HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Selection Signal Desk</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&family=Noto+Sans+SC:wght@400;500;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #f5f7fa;
      --panel: #ffffff;
      --soft: #f0f3f7;
      --ink: #1f2430;
      --muted: #687184;
      --line: #dfe4ec;
      --accent: #d66b2c;
      --green: #4f8063;
      --blue: #527fa3;
      --shadow: 0 16px 34px rgba(31, 41, 55, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Manrope", "Noto Sans SC", sans-serif;
      background: linear-gradient(180deg, #fafbfc 0%, var(--bg) 100%);
      color: var(--ink);
    }
    .shell { width: min(1480px, calc(100vw - 32px)); margin: 0 auto; padding: 28px 0 48px; }
    .topbar {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: end;
    }
    .eyebrow { color: var(--accent); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0; }
    h1 { margin: 8px 0 8px; font-size: clamp(34px, 4.6vw, 58px); line-height: 1.02; letter-spacing: 0; }
    .lead { margin: 0; max-width: 760px; color: var(--muted); font-size: 16px; line-height: 1.65; }
    .generated { color: var(--muted); font-size: 13px; font-weight: 700; white-space: nowrap; }
    .metrics {
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }
    .metric {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-height: 90px;
      box-shadow: var(--shadow);
    }
    .metric strong { display: block; font-size: 30px; line-height: 1; }
    .metric span { display: block; margin-top: 9px; color: var(--muted); font-size: 13px; font-weight: 700; }
    .tabs {
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      background: var(--soft);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 6px;
    }
    .tab {
      min-height: 48px;
      border: 0;
      border-radius: 6px;
      background: transparent;
      color: var(--muted);
      font: inherit;
      font-weight: 800;
      cursor: pointer;
    }
    .tab.active { background: var(--panel); color: var(--ink); box-shadow: 0 4px 14px rgba(31,41,55,.08); }
    .toolbar {
      margin-top: 16px;
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
      align-items: center;
    }
    .search {
      height: 48px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 0 14px;
    }
    .search input { width: 100%; border: 0; outline: 0; background: transparent; font: inherit; color: var(--ink); }
    .filters { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-start; }
    .chip {
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel);
      color: var(--muted);
      padding: 0 12px;
      font: inherit;
      font-size: 13px;
      font-weight: 800;
      cursor: pointer;
    }
    .chip.active { background: var(--ink); border-color: var(--ink); color: #fff; }
    .content {
      margin-top: 18px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 20px;
    }
    .section-head {
      display: block;
      margin-bottom: 16px;
    }
    .section-head h2 { margin: 0; font-size: 25px; line-height: 1.2; letter-spacing: 0; }
    .section-note { margin: 7px 0 0; color: var(--muted); font-size: 14px; line-height: 1.55; }
    .selector { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-start; align-items: center; margin-top: 14px; }
    .history-select {
      min-height: 38px;
      padding: 0 34px 0 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--ink);
      font: inherit;
      cursor: pointer;
    }
    .history-range { color: var(--muted); font-size: 13px; }
    .lane-switch { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(252px, 1fr)); gap: 14px; }
    .card {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      min-height: 100%;
      display: flex;
      flex-direction: column;
    }
    .thumb {
      width: 100%;
      aspect-ratio: 1.18 / .82;
      object-fit: cover;
      background: linear-gradient(135deg, #e9eef5, #f8fafc);
      display: grid;
      place-items: center;
      padding: 18px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
      text-align: center;
    }
    .body { padding: 13px; display: grid; gap: 8px; flex: 1; }
    .meta, .tags { display: flex; flex-wrap: wrap; gap: 7px; }
    .pill {
      min-height: 24px;
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 0 8px;
      font-size: 11px;
      font-weight: 800;
      background: #fff4e8;
      color: #9c4b1c;
    }
    .pill.green { background: #edf5ee; color: var(--green); }
    .pill.blue { background: #edf5f8; color: var(--blue); }
    .pill.gray { background: #f2f4f7; color: #667085; }
    .card h3 { margin: 0; font-size: 18px; line-height: 1.28; letter-spacing: 0; }
    .card h3 a { color: inherit; text-decoration: none; }
    .card h3 a:hover { color: var(--accent); }
    .summary {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
      min-height: 58px;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .empty {
      min-height: 180px;
      display: grid;
      place-items: center;
      color: var(--muted);
      background: var(--soft);
      border-radius: 8px;
      font-weight: 800;
      text-align: center;
      padding: 24px;
    }
    @media (max-width: 900px) {
      .topbar, .toolbar { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .tabs { grid-template-columns: 1fr; }
      .filters, .selector { justify-content: flex-start; }
    }
    @media (max-width: 620px) {
      .shell { width: min(100vw - 20px, 1480px); padding-top: 18px; }
      .metrics { grid-template-columns: 1fr; }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div>
        <div class="eyebrow">Selection Signal Desk</div>
        <h1>选品情报工作台</h1>
        <p class="lead">每日看新增，每周看推荐，通过池只保留品类相关且达到选品质量线的内容。让团队打开一个页面就知道今天系统真正筛出了什么。</p>
      </div>
      <div class="generated" id="generatedAt"></div>
    </header>

    <section class="metrics" id="metrics"></section>

    <nav class="tabs">
      <button class="tab active" type="button" data-tab="daily">今日新增</button>
      <button class="tab" type="button" data-tab="weekly">本周推荐</button>
      <button class="tab" type="button" data-tab="pool">审核通过池</button>
    </nav>

    <section class="toolbar">
      <label class="search">
        <span>⌕</span>
        <input id="search" type="search" placeholder="搜索标题、品类、来源、启发类型">
      </label>
      <div class="filters" id="filters"></div>
    </section>

    <main class="content">
      <div class="section-head">
        <div>
          <h2 id="viewTitle"></h2>
          <p class="section-note" id="viewNote"></p>
        </div>
        <div class="selector" id="groupSelector"></div>
      </div>
      <div class="lane-switch" id="laneSwitch"></div>
      <section class="grid" id="grid"></section>
      <div class="empty" id="emptyState" hidden>当前筛选下没有内容。</div>
    </main>
  </div>

  <script src="./data.json"></script>
  <script>
    const payload = window.__INSIGHT_DATA__;
    const configuredCategories = payload.configured_categories || [
      "水杯", "氛围灯", "创意礼盒", "装置艺术", "创意厨具", "中秋礼盒", "创意桌搭", "端午礼盒", "充电宝",
      "日历", "手机壳", "冲锋衣", "钥匙扣水壶"
    ];
    const retiredCategories = new Set(payload.retired_categories || ["T恤", "帽子", "卫衣", "Polo衫", "收纳包", "卡包"]);
    const state = {
      tab: "daily",
      q: "",
      lane: "全部",
      category: "全部",
      source: "全部",
      dailyGroup: "",
      weeklyGroup: ""
    };
    const $ = id => document.getElementById(id);

    function groupsDaily() {
      return (payload.daily_groups || []).filter(group => group.items && group.items.length);
    }

    function groupsWeekly() {
      const groups = payload.weekly_groups && payload.weekly_groups.length
        ? payload.weekly_groups
        : (payload.weekly_report && payload.weekly_report.recommendations ? [payload.weekly_report] : []);
      return groups.filter(group => group.recommendations && group.recommendations.length);
    }

    function activeDaily() {
      const groups = groupsDaily();
      if (!groups.length) return null;
      if (!state.dailyGroup) state.dailyGroup = groups[0].group_id || groups[0].date;
      return groups.find(group => (group.group_id || group.date) === state.dailyGroup) || groups[0];
    }

    function activeWeekly() {
      const groups = groupsWeekly();
      if (!groups.length) return null;
      if (!state.weeklyGroup) state.weeklyGroup = groups[0].group_id || groups[0].week;
      return groups.find(group => (group.group_id || group.week) === state.weeklyGroup) || groups[0];
    }

    function sourceText(item) {
      return item.source_name || item.source || "未知来源";
    }

    function scoreText(item) {
      if (item.score_label) return item.score_label;
      return ((item.score || 0) / 10).toFixed(1);
    }

    function textFor(item) {
      return [
        item.title, item.category, item.summary, sourceText(item),
        item.action_lane, item.source_family, ...(item.axes || []), ...(item.tags || [])
      ].join(" ").toLowerCase();
    }

    function matches(item) {
      if (state.lane !== "全部" && item.action_lane !== state.lane) return false;
      if (state.category !== "全部" && item.category !== state.category) return false;
      if (state.source !== "全部" && item.source_family !== state.source) return false;
      if (state.q && !textFor(item).includes(state.q.toLowerCase())) return false;
      return true;
    }

    function chip(label, active, onClick) {
      const el = document.createElement("button");
      el.type = "button";
      el.className = `chip${active ? " active" : ""}`;
      el.textContent = label;
      el.addEventListener("click", onClick);
      return el;
    }

    function renderMetrics() {
      const daily = groupsDaily()[0];
      const weekly = activeWeekly();
      const metrics = [
        [daily ? daily.actual_count : 0, "今日新增"],
        [weekly ? weekly.actual_count : 0, "本周推荐"],
        [payload.stats.total_items || 0, "审核通过池"],
        [payload.stats.by_image_state && payload.stats.by_image_state["已对齐"] || 0, "已带图内容"]
      ];
      $("metrics").innerHTML = metrics.map(([value, label]) => `<div class="metric"><strong>${value}</strong><span>${label}</span></div>`).join("");
      $("generatedAt").textContent = `最近生成 ${String(payload.generated_at || "").replace("T", " ")}`;
    }

    function currentItems() {
      if (state.tab === "daily") {
        const group = activeDaily();
        return group ? group.items : [];
      }
      if (state.tab === "weekly") {
        const group = activeWeekly();
        return group ? group.recommendations : [];
      }
      return payload.items || [];
    }

    function currentTitle() {
      if (state.tab === "daily") {
        const group = activeDaily();
        if (!group) return "今日新增";
        const latest = groupsDaily()[0];
        return group.date === (latest && latest.date)
          ? `${group.date} 今日新增`
          : `${group.date} 历史情报`;
      }
      if (state.tab === "weekly") {
        const group = activeWeekly();
        return group ? `${group.week} 本周推荐` : "本周推荐";
      }
      return "审核通过池";
    }

    function currentNote() {
      if (state.tab === "daily") {
        const group = activeDaily();
        if (!group) return "每天自动收集后，这里会按日期显示当天前 30 条去重情报。";
        const source = Object.entries(group.stats.by_source_family || {}).map(([k, v]) => `${k} ${v}`).join(" / ");
        const backfill = Number((group.stats || {}).backfill_count || 0);
        return `${group.actual_count} 条 · 每日分组 · 已去重${backfill ? ` · 历史补录 ${backfill}` : ""}${source ? " · " + source : ""}`;
      }
      if (state.tab === "weekly") {
        const group = activeWeekly();
        if (!group) return "每周自动生成 100 条推荐，并按买样、改造、方向参考分流。";
        const lane = Object.entries(group.stats.by_lane || {}).map(([k, v]) => `${k} ${v}`).join(" / ");
        return `${group.date_label || ""} · ${group.actual_count} 条 · 已去重${lane ? " · " + lane : ""}`;
      }
      return "这里只展示通过品类相关性、基础质量和创意增量审核的线索；未通过内容保留在审核归档中。";
    }

    function renderGroupSelector() {
      const root = $("groupSelector");
      root.innerHTML = "";
      if (state.tab === "daily") {
        const groups = groupsDaily();
        const active = activeDaily();
        const activeId = active && (active.group_id || active.date);
        groups.slice(0, 14).forEach(group => {
          const id = group.group_id || group.date;
          root.appendChild(chip(`${group.date} · ${group.actual_count}`, id === activeId, () => {
            state.dailyGroup = id;
            render();
          }));
        });
        const olderGroups = groups.slice(14);
        if (olderGroups.length) {
          const select = document.createElement("select");
          select.className = "history-select";
          select.setAttribute("aria-label", "选择更早日期");
          const placeholder = document.createElement("option");
          placeholder.value = "";
          placeholder.textContent = `更早日期（${olderGroups.length}）`;
          placeholder.selected = !olderGroups.some(group => (group.group_id || group.date) === activeId);
          select.appendChild(placeholder);
          olderGroups.forEach(group => {
            const option = document.createElement("option");
            option.value = group.group_id || group.date;
            option.textContent = `${group.date} · ${group.actual_count} 条`;
            option.selected = option.value === activeId;
            select.appendChild(option);
          });
          select.addEventListener("change", () => {
            if (!select.value) return;
            state.dailyGroup = select.value;
            render();
          });
          root.appendChild(select);
          const range = document.createElement("span");
          range.className = "history-range";
          range.textContent = `历史保留至 ${groups[groups.length - 1].date}`;
          root.appendChild(range);
        }
      } else if (state.tab === "weekly") {
        groupsWeekly().slice(0, 12).forEach(group => {
          const id = group.group_id || group.week;
          root.appendChild(chip(`${group.week} · ${group.actual_count}`, id === (activeWeekly() && (activeWeekly().group_id || activeWeekly().week)), () => {
            state.weeklyGroup = id;
            render();
          }));
        });
      }
    }

    function renderFilters(items) {
      const root = $("filters");
      const itemCategories = new Set(items.map(item => item.category).filter(Boolean));
      const categories = [
        ...configuredCategories,
        ...[...itemCategories].filter(category => !configuredCategories.includes(category) && !retiredCategories.has(category))
      ];
      const sources = [...new Set(items.map(item => item.source_family).filter(Boolean))];
      root.innerHTML = "";
      root.appendChild(chip("全部品类", state.category === "全部", () => { state.category = "全部"; render(); }));
      categories.forEach(category => root.appendChild(chip(`${category}${itemCategories.has(category) ? "" : " 0"}`, state.category === category, () => { state.category = category; render(); })));
      root.appendChild(chip("全部来源", state.source === "全部", () => { state.source = "全部"; render(); }));
      sources.forEach(source => root.appendChild(chip(source, state.source === source, () => { state.source = source; render(); })));
    }

    function renderLaneSwitch() {
      const root = $("laneSwitch");
      root.innerHTML = "";
      if (state.tab !== "weekly") return;
      ["全部", "可直接买样", "适合改造", "方向参考"].forEach(lane => {
        root.appendChild(chip(lane, state.lane === lane, () => { state.lane = lane; render(); }));
      });
    }

    function card(item) {
      const image = item.image
        ? `<img class="thumb" src="${item.image}" alt="" loading="lazy">`
        : `<div class="thumb">${item.category || "灵感"}<br>${sourceText(item)}<br>待补图</div>`;
      const title = item.url
        ? `<a href="${item.url}" target="_blank" rel="noopener">${item.title}</a>`
        : `${item.title}`;
      return `<article class="card">
        ${image}
        <div class="body">
          <div class="meta">
            <span class="pill">${item.action_lane}</span>
            <span class="pill green">${item.category || "未分类"}</span>
            <span class="pill blue">${scoreText(item)}分</span>
            ${item.is_backfill ? `<span class="pill gray">历史补录</span>` : ""}
          </div>
          <h3>${title}</h3>
          <p class="summary">${item.summary || item.next_action || item.review_reason || ""}</p>
          <div class="tags">
            ${(item.axes || []).slice(0, 2).map(axis => `<span class="pill gray">${axis}</span>`).join("")}
            <span class="pill gray">${sourceText(item)}</span>
          </div>
        </div>
      </article>`;
    }

    function renderGrid() {
      const base = currentItems();
      const items = base.filter(matches);
      $("emptyState").hidden = items.length > 0;
      $("grid").innerHTML = items.map(card).join("");
      renderFilters(base);
    }

    function render() {
      renderMetrics();
      renderGroupSelector();
      renderLaneSwitch();
      $("viewTitle").textContent = currentTitle();
      $("viewNote").textContent = currentNote();
      renderGrid();
      document.querySelectorAll(".tab").forEach(tab => tab.classList.toggle("active", tab.dataset.tab === state.tab));
    }

    document.querySelectorAll(".tab").forEach(tab => {
      tab.addEventListener("click", () => {
        state.tab = tab.dataset.tab;
        state.lane = "全部";
        state.category = "全部";
        state.source = "全部";
        render();
      });
    });
    $("search").addEventListener("input", event => {
      state.q = event.target.value.trim();
      renderGrid();
    });

    render();
  </script>
</body>
</html>
"""


def main():
    ensure_dirs()
    products = load_json(DATA_DIR / "products.json", [])
    trends = load_json(DATA_DIR / "trends.json", {})
    weekly_report = load_json(DATA_DIR / "weekly_report.json", {})
    weekly_groups = []
    reports_dir = DATA_DIR / "reports"
    if reports_dir.exists():
        for path in sorted(reports_dir.glob("weekly-*.json"), reverse=True):
            weekly_groups.append(load_json(path, {}))
    if weekly_report and not any(group.get("week") == weekly_report.get("week") for group in weekly_groups):
        weekly_groups.insert(0, weekly_report)
    payload = build_payload(products, trends, weekly_report, weekly_groups[:12])
    write_json(DATA_DIR / "published.json", payload)
    write_json(INSIGHT_DIR / "data.raw.json", payload)
    data_js = "window.__INSIGHT_DATA__ = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    (INSIGHT_DIR / "data.json").write_text(data_js, encoding="utf-8")
    (INSIGHT_DIR / "index.html").write_text(HTML, encoding="utf-8")
    print(f"built insight/index.html items={len(products)}")


if __name__ == "__main__":
    main()
