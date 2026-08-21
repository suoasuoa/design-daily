#!/usr/bin/env python3
"""Reject a generated daily group if quantity pressure weakened its quality."""

from collections import Counter
import argparse
from pathlib import Path

from build_site import DAILY_CATEGORY_CAPS, DAILY_SOURCE_CAP, display_eligible
from insight_common import load_json, semantic_product_duplicate, today


def verify_payload(payload, current_day):
    groups = payload.get("daily_groups") or []
    group = next((row for row in groups if row.get("date") == current_day), None)
    if not group:
        return [f"missing daily group for {current_day}"]

    items = group.get("items") or []
    historical = [
        item
        for row in groups
        if (row.get("date") or "") < current_day
        for item in (row.get("items") or [])
    ]
    errors = []
    regular_items = []

    for item in items:
        emergency = bool(item.get("is_emergency_fill"))
        minimum = 70 if emergency else 74
        if not display_eligible(item, min_quality=minimum):
            errors.append(
                f"quality gate failed id={item.get('id')} score={item.get('quality_score')} "
                f"innovation={item.get('innovation')} relevance={item.get('relevance')}"
            )
        if not emergency:
            regular_items.append(item)
        if any(semantic_product_duplicate(item, old) for old in historical):
            errors.append(f"historical duplicate id={item.get('id')} title={item.get('title')}")

    for index, item in enumerate(items):
        if any(semantic_product_duplicate(item, other) for other in items[:index]):
            errors.append(f"same-day duplicate id={item.get('id')} title={item.get('title')}")

    category_counts = Counter(item.get("category") or "未分类" for item in regular_items)
    for category, count in category_counts.items():
        cap = DAILY_CATEGORY_CAPS.get(category, 5)
        if count > cap:
            errors.append(f"category cap exceeded category={category} count={count} cap={cap}")

    source_counts = Counter(item.get("source_name") or "未知来源" for item in regular_items)
    for source, count in source_counts.items():
        if count > DAILY_SOURCE_CAP:
            errors.append(f"source cap exceeded source={source} count={count} cap={DAILY_SOURCE_CAP}")

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="insight/data.raw.json")
    parser.add_argument("--date", default=today())
    args = parser.parse_args()

    payload = load_json(Path(args.data), {})
    errors = verify_payload(payload, args.date)
    if errors:
        print("daily_quality_gate=failed")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    group = next(row for row in payload.get("daily_groups") or [] if row.get("date") == args.date)
    print(f"daily_quality_gate=passed date={args.date} items={len(group.get('items') or [])}")


if __name__ == "__main__":
    main()
