#!/usr/bin/env python3
"""Build and format the team's product preference memory."""

from collections import Counter, defaultdict

from insight_common import DATA_DIR, load_json, now_iso


PASS_REASON_LABELS = {
    "too_ordinary": "太普通，没有明显创意增量",
    "weak_function": "功能价值弱或需求不高频",
    "wrong_category": "品类错误或与选品范围无关",
    "low_margin": "价格空间或利润不足",
    "hard_to_execute": "难以买样、改造或落地",
    "bad_evidence": "图片、链接或产品证据有问题",
}


def latest_decisions(events):
    latest = {}
    ordered = sorted(events, key=lambda event: str(event.get("created_at") or ""))
    for event in ordered:
        actor_id = str(event.get("actor_id") or "anonymous")
        product_id = str(event.get("product_id") or "")
        if not product_id:
            continue
        key = (actor_id, product_id)
        if event.get("action") == "clear":
            latest.pop(key, None)
        elif event.get("action") in {"like", "pass"}:
            latest[key] = event
    return list(latest.values())


def top_values(counter, limit=8):
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def build_profile(events):
    decisions = latest_decisions(events)
    dimensions = {
        "like": defaultdict(Counter),
        "pass": defaultdict(Counter),
    }
    product_votes = defaultdict(Counter)
    examples = {"like": [], "pass": []}
    reason_counts = Counter()

    for event in decisions:
        action = event["action"]
        snapshot = event.get("item_snapshot") or {}
        product_id = str(event.get("product_id") or "")
        product_votes[product_id][action] += 1
        for field in ("category", "source_family", "action_lane"):
            value = str(snapshot.get(field) or "").strip()
            if value:
                dimensions[action][field][value] += 1
        for field in ("axes", "tags"):
            for value in snapshot.get(field) or []:
                value = str(value).strip()
                if value:
                    dimensions[action][field][value] += 1
        if action == "pass" and event.get("reason"):
            reason_counts[str(event["reason"])] += 1
        if len(examples[action]) < 12:
            examples[action].append(
                {
                    "product_id": product_id,
                    "title": snapshot.get("title", ""),
                    "category": snapshot.get("category", ""),
                    "summary": snapshot.get("summary", ""),
                    "reason": event.get("reason", ""),
                }
            )

    blocked = sorted(
        product_id
        for product_id, votes in product_votes.items()
        if votes["pass"] > votes["like"]
    )
    return {
        "version": 1,
        "generated_at": now_iso(),
        "stats": {
            "events": len(events),
            "active_decisions": len(decisions),
            "likes": sum(1 for event in decisions if event["action"] == "like"),
            "passes": sum(1 for event in decisions if event["action"] == "pass"),
        },
        "positive_patterns": {
            field: top_values(counter)
            for field, counter in dimensions["like"].items()
        },
        "negative_patterns": {
            field: top_values(counter)
            for field, counter in dimensions["pass"].items()
        },
        "pass_reasons": [
            {
                "code": code,
                "label": PASS_REASON_LABELS.get(code, code),
                "count": count,
            }
            for code, count in reason_counts.most_common()
        ],
        "positive_examples": examples["like"],
        "negative_examples": examples["pass"],
        "blocked_product_ids": blocked,
    }


def pattern_text(patterns):
    parts = []
    for field, rows in patterns.items():
        values = "、".join(f"{row['name']}({row['count']})" for row in rows[:6])
        if values:
            parts.append(f"{field}: {values}")
    return "；".join(parts) or "暂无"


def preference_context(profile=None):
    profile = profile or load_json(DATA_DIR / "preference_profile.json", {})
    stats = profile.get("stats") or {}
    if int(stats.get("active_decisions") or 0) <= 0:
        return "团队偏好反馈尚未积累，继续严格执行基础选品标准并保持品类探索。"

    positive = pattern_text(profile.get("positive_patterns") or {})
    negative = pattern_text(profile.get("negative_patterns") or {})
    reasons = "、".join(
        f"{row.get('label')}({row.get('count')})"
        for row in (profile.get("pass_reasons") or [])[:6]
    ) or "暂无"
    positive_examples = "；".join(
        f"{row.get('category')}｜{row.get('title')}"
        for row in (profile.get("positive_examples") or [])[:8]
    ) or "暂无"
    negative_examples = "；".join(
        f"{row.get('category')}｜{row.get('title')}｜{PASS_REASON_LABELS.get(row.get('reason'), row.get('reason'))}"
        for row in (profile.get("negative_examples") or [])[:8]
    ) or "暂无"
    return (
        f"有效反馈 {stats.get('active_decisions', 0)} 条，点赞 {stats.get('likes', 0)}，"
        f"Pass {stats.get('passes', 0)}。\n"
        f"偏好方向：{positive}\n"
        f"降权方向：{negative}\n"
        f"主要 Pass 原因：{reasons}\n"
        f"点赞示例：{positive_examples}\n"
        f"Pass 示例：{negative_examples}\n"
        "反馈只用于调整搜索和排序权重；不得降低品类、真实性、实用性、创新和链接证据的硬门槛，"
        "并保留约 20% 与历史偏好不同的探索候选。"
    )
