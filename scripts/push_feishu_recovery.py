#!/usr/bin/env python3
"""Recover a recent completed weekday digest that Feishu did not receive."""

import argparse
import datetime as dt
import json
import os
import urllib.error
from zoneinfo import ZoneInfo

from insight_common import INSIGHT_DIR, load_env, load_json, write_json
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def group_date(group):
    try:
        return dt.date.fromisoformat(str(group.get("date") or ""))
    except ValueError:
        return None


def recoverable_groups(data, sent_log, today, recover_days, min_count):
    candidates = []
    for group in data.get("daily_groups") or []:
        day = group_date(group)
        if not day or day >= today or day.weekday() >= 5:
            continue
        age = (today - day).days
        if age > recover_days:
            continue
        date = day.isoformat()
        if sent_log.get(date, {}).get("sent"):
            continue
        if len(group.get("items") or []) < min_count:
            continue
        candidates.append((day, group))
    return [group for _, group in sorted(candidates, key=lambda pair: pair[0])]


def main():
    from push_feishu_daily import card_elements, send_card, top_items

    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--top-limit", type=int, default=5)
    parser.add_argument("--min-count", type=int, default=40)
    parser.add_argument("--recover-days", type=int, default=7)
    parser.add_argument("--sent-log", default="data/feishu_push_log.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = load_json(INSIGHT_DIR / "data.raw.json", {})
    sent_log = load_json(args.sent_log, {})
    now = dt.datetime.now(LOCAL_TZ)
    candidates = recoverable_groups(
        data,
        sent_log,
        now.date(),
        max(args.recover_days, 0),
        max(args.min_count, 1),
    )
    if not candidates:
        print("feishu_recovery=skipped reason=no_completed_unsent_weekday")
        return

    group = candidates[0]
    date = group["date"]
    items = (group.get("items") or [])[: args.limit]
    highlighted = top_items(items, args.top_limit)
    title = f"Design Daily｜{date}｜{len(items)} 条中最推荐 5 个（补发）"

    if args.dry_run:
        print(json.dumps({"date": date, "total": len(items), "title": title}, ensure_ascii=False))
        return

    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
    secret = os.environ.get("FEISHU_WEBHOOK_SECRET", "").strip()
    if not webhook_url:
        print("feishu_recovery=skipped reason=missing_FEISHU_WEBHOOK_URL")
        return

    try:
        result = send_card(
            webhook_url,
            secret,
            title,
            card_elements(group, highlighted, len(items)),
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(f"feishu_recovery=failed date={date} error={exc}") from exc

    sent_log[date] = {
        "sent": True,
        "sent_at": now.isoformat(timespec="seconds"),
        "format": "card",
        "top_limit": len(highlighted),
        "total": len(items),
        "recovered": True,
    }
    write_json(args.sent_log, sent_log)
    print(f"feishu_recovery=sent date={date} top={len(highlighted)} result={result}")


if __name__ == "__main__":
    main()
