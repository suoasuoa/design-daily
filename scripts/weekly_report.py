#!/usr/bin/env python3
"""Generate a weekly 100-pick selection report from the product pool."""

import argparse
from collections import Counter, defaultdict
import datetime as dt
import re

from insight_common import clean_direct_product_url, DATA_DIR, INSIGHT_DIR, ensure_dirs, load_json, now_iso, source_quality, source_type, today, write_json
from insight_config import RETIRED_CATEGORIES


LANE_ORDER = ["可直接买样", "适合改造", "方向参考"]
LANE_QUOTAS = {"可直接买样": 30, "适合改造": 45, "方向参考": 25}


def week_id(day=None):
    day = day or dt.date.fromisoformat(today())
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def week_range(day=None):
    day = day or dt.date.fromisoformat(today())
    start = day - dt.timedelta(days=day.weekday())
    end = start + dt.timedelta(days=6)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "label": f"{start.isoformat()} 至 {end.isoformat()}",
    }


def normalize_key(value):
    value = (value or "").lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"www\\.", "", value)
    value = re.sub(r"[^a-z0-9\\u4e00-\\u9fff]+", "", value)
    return value[:120]


def dedupe_keys(item):
    return {
        item.get("id") or "",
        normalize_key(item.get("url")),
        normalize_key(item.get("title")),
    } - {""}


def product_score(item):
    return (
        int(item.get("score") or item.get("selection_score") or 0),
        int(item.get("seen_count") or 0),
        item.get("last_seen") or "",
    )


def normalize_item(item):
    source = item.get("source_name") or item.get("source_primary") or ""
    if not source and item.get("sources"):
        source = item["sources"][0].get("source", "")
    review = item.get("category_review") or {}
    score = int(review.get("quality_score") or item.get("score") or item.get("selection_score") or 0)
    url = clean_direct_product_url(item.get("url") or "")
    source_type_value = item.get("source_type", "") or source_type(source or "")
    source_group = item.get("source_group", "")
    quality = item.get("source_quality") or source_quality(
        source=source or "",
        source_type_value=source_type_value,
        source_group=source_group,
        quality_tier=item.get("quality_tier", ""),
    )
    return {
        "id": item.get("id"),
        "product_key": item.get("product_key"),
        "title": item.get("title", ""),
        "category": item.get("category", "未分类"),
        "action_lane": item.get("action_lane", "方向参考"),
        "axes": item.get("axes") or item.get("inspiration_axes") or [],
        "score": score,
        "score_label": f"{score / 10:.1f}",
        "source": source or "未知来源",
        "source_family": item.get("source_family", "其他来源"),
        "source_quality": quality,
        "url": url,
        "image": item.get("image", ""),
        "summary": item.get("summary") or item.get("ai_reason") or "",
        "risk": item.get("ai_risk") or item.get("review_reason") or "",
        "review_confidence": int(item.get("review_confidence") or review.get("confidence") or 0),
        "review_reason": item.get("review_reason") or review.get("reason") or "",
        "next_action": next_action(item),
        "tags": (item.get("tags") or item.get("trend_tags") or [])[:6],
    }


def next_action(item):
    lane = item.get("action_lane", "")
    category = item.get("category", "")
    if lane == "可直接买样":
        return "买样看材质、尺寸、成本和差评点"
    if lane == "适合改造":
        if "礼盒" in category:
            return "拆解包装结构和开箱动线，做二次主题化"
        if category in {"创意桌搭", "收纳包", "创意厨具"}:
            return "提取结构或功能点，换材质/场景重新组合"
        return "提取可借鉴元素，做同品类差异化改造"
    return "保留为趋势语言和内容方向，暂不直接打样"


def pick_balanced(items, limit=100):
    by_lane = defaultdict(list)
    for item in sorted(items, key=product_score, reverse=True):
        if item.get("category") in RETIRED_CATEGORIES:
            continue
        review_text = f"{item.get('summary', '')} {item.get('review_reason', '')}".lower()
        if any(word in review_text for word in ["不匹配", "与品类无关", "不属于", "内容不符", "off-category", "fallback"]):
            continue
        if int(item.get("score") or 0) < 60 or int(item.get("review_confidence") or 0) < 4:
            continue
        if not item.get("url"):
            continue
        if item.get("source_quality") == "weak":
            if not item.get("image") or int(item.get("score") or 0) < 82:
                continue
            if item.get("category") in {"T恤", "卫衣", "Polo衫", "帽子"}:
                continue
        by_lane[item.get("action_lane", "方向参考")].append(item)

    picked = []
    seen_keys = set()
    category_counts = Counter()

    def add_from_lane(lane, quota):
        for item in by_lane.get(lane, []):
            if len([x for x in picked if x.get("action_lane") == lane]) >= quota:
                break
            keys = dedupe_keys(item)
            if keys & seen_keys:
                continue
            category = item.get("category", "未分类")
            if category_counts[category] >= 12 and len(picked) < limit * 0.8:
                continue
            picked.append(item)
            seen_keys.update(keys)
            category_counts[category] += 1

    for lane in LANE_ORDER:
        add_from_lane(lane, LANE_QUOTAS[lane])

    if len(picked) < limit:
        for item in sorted(items, key=product_score, reverse=True):
            review_text = f"{item.get('summary', '')} {item.get('review_reason', '')}".lower()
            if (
                item.get("category") in RETIRED_CATEGORIES
                or not item.get("url")
                or int(item.get("score") or 0) < 60
                or int(item.get("review_confidence") or 0) < 4
                or any(word in review_text for word in ["不匹配", "与品类无关", "不属于", "内容不符", "off-category", "fallback"])
            ):
                continue
            keys = dedupe_keys(item)
            if keys & seen_keys:
                continue
            picked.append(item)
            seen_keys.update(keys)
            if len(picked) >= limit:
                break

    return picked[:limit]


def build_report(payload, limit=100):
    raw_items = [normalize_item(item) for item in payload.get("items", [])]
    picks = pick_balanced(raw_items, limit)
    by_lane = Counter(item["action_lane"] for item in picks)
    by_category = Counter(item["category"] for item in picks)
    by_axis = Counter(axis for item in picks for axis in item["axes"])

    dates = week_range()
    return {
        "generated_at": now_iso(),
        "week": week_id(),
        "group_id": week_id(),
        "date_start": dates["start"],
        "date_end": dates["end"],
        "date_label": dates["label"],
        "title": f"{week_id()} 选品机会周报",
        "target_count": limit,
        "actual_count": len(picks),
        "summary": "本周推荐按买样、改造、方向参考分流，优先服务选品会讨论和后续人工筛选。",
        "stats": {
            "by_lane": dict(by_lane.most_common()),
            "by_category": dict(by_category.most_common(20)),
            "by_axis": dict(by_axis.most_common()),
        },
        "dedupe": {
            "method": "product id + canonical url + normalized title",
            "unique_recommendations": len({item.get("id") or item.get("url") or item.get("title") for item in picks}),
        },
        "recommendations": picks,
    }


def write_markdown(report):
    lines = [
        f"# {report['title']}",
        "",
        report["summary"],
        "",
        f"- 推荐数量：{report['actual_count']} / {report['target_count']}",
        f"- 生成时间：{report['generated_at']}",
        "",
        "## 行动分布",
        "",
    ]
    for lane, count in report["stats"]["by_lane"].items():
        lines.append(f"- {lane}: {count}")
    lines.extend(["", "## 推荐清单", ""])
    for idx, item in enumerate(report["recommendations"], 1):
        axes = "、".join(item.get("axes") or [])
        lines.extend(
            [
                f"### {idx}. {item['title']}",
                "",
                f"- 品类：{item['category']}",
                f"- 路径：{item['action_lane']}",
                f"- 启发：{axes or '待判断'}",
                f"- 分数：{item['score_label']}",
                f"- 来源：{item['source']}",
                f"- 下一步：{item['next_action']}",
                f"- 链接：{item['url']}",
                "",
                item.get("summary", ""),
                "",
            ]
        )
    text = "\n".join(lines).strip() + "\n"
    (INSIGHT_DIR / "weekly.md").write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100, help="Weekly recommendation count.")
    args = parser.parse_args()

    ensure_dirs()
    payload = load_json(DATA_DIR / "published.json", {})
    if not payload.get("items"):
        raise SystemExit("No published items found. Run scripts/build_site.py first.")

    report = build_report(payload, args.limit)
    reports_dir = DATA_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    write_json(DATA_DIR / "weekly_report.json", report)
    write_json(reports_dir / f"weekly-{report['week']}.json", report)
    write_json(INSIGHT_DIR / "weekly.json", report)
    write_markdown(report)
    print(f"weekly_report={report['week']} recommendations={report['actual_count']}")


if __name__ == "__main__":
    main()
