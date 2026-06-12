#!/usr/bin/env python3
"""Push the latest daily picks to a Feishu custom bot webhook."""

import argparse
import base64
import hashlib
import hmac
import json
import os
import ssl
import time
import datetime as dt
from zoneinfo import ZoneInfo
import urllib.error
import urllib.request

from insight_common import INSIGHT_DIR, load_env, load_json, write_json


SITE_URL = "https://suoasuoa.github.io/design-daily/insight/"
SSL_CONTEXT = ssl._create_unverified_context()
DAILY_DEMAND_CATEGORIES = {
    "水杯",
    "氛围灯",
    "创意厨具",
    "创意桌搭",
    "充电宝",
    "日历",
    "T恤",
    "卫衣",
    "卡包",
    "手机壳",
    "收纳包",
    "帽子",
}
BROAD_CATEGORIES = {
    "水杯",
    "氛围灯",
    "创意礼盒",
    "创意厨具",
    "创意桌搭",
    "充电宝",
    "日历",
    "T恤",
    "卫衣",
    "卡包",
    "手机壳",
    "收纳包",
    "Polo衫",
    "帽子",
}
FUNCTION_CATEGORIES = {"水杯", "创意厨具", "创意桌搭", "充电宝", "卡包", "手机壳", "收纳包", "钥匙扣水壶"}
EMOTION_CATEGORIES = {"氛围灯", "创意礼盒", "中秋礼盒", "端午礼盒", "帽子", "装置艺术"}
PRICE_LABELS = {
    "likely_over_35": "价格带大概率 >35 元",
    "unknown": "价格待人工确认",
    "risk_under_35": "价格可能偏低",
}
SOURCE_BONUS = {
    "社交灵感": 12,
    "市场信号": 10,
    "媒体案例": 8,
    "奖项案例": 7,
    "包装专项": 7,
    "设计社区": 6,
}


def item_link(item):
    return item.get("url") or SITE_URL


def source_label(item):
    source = item.get("source_name") or item.get("source_family") or "公开来源"
    family = item.get("source_family") or ""
    if family and family not in source:
        return f"{source}/{family}"
    return source


def recommend_reason(item):
    category = item.get("category") or "未分类"
    score = int(item.get("score") or 0)
    axes = item.get("axes") or []
    price_gate = item.get("price_gate") or "unknown"
    lane = item.get("action_lane") or "待判断"
    parts = []

    if category in DAILY_DEMAND_CATEGORIES:
        parts.append("高频需求")
    if category in BROAD_CATEGORIES:
        parts.append("打击面广")
    if category in FUNCTION_CATEGORIES or "功能启发" in axes:
        parts.append("功能点清晰")
    if category in EMOTION_CATEGORIES or "情绪启发" in axes:
        parts.append("有情绪/视觉钩子")
    if price_gate == "likely_over_35":
        parts.append("价格带有利润空间")
    if score >= 70:
        parts.append("综合分靠前")
    if not parts:
        parts.append("可作为方向参考")

    lead = "、".join(parts[:3])
    price = PRICE_LABELS.get(price_gate, "价格待人工确认")
    return f"{lead}，当前更适合走“{lane}”，{price}。"


def recommendation_score(item):
    score = int(item.get("score") or 0)
    if score > 0:
        return score
    category = item.get("category") or ""
    axes = item.get("axes") or []
    value = 45
    if category in DAILY_DEMAND_CATEGORIES:
        value += 12
    if category in BROAD_CATEGORIES:
        value += 10
    if category in FUNCTION_CATEGORIES or "功能启发" in axes:
        value += 8
    if category in EMOTION_CATEGORIES or "情绪启发" in axes:
        value += 5
    if item.get("price_gate") == "likely_over_35":
        value += 8
    if item.get("image"):
        value += 5
    if item_link(item) != SITE_URL:
        value += 4
    value += SOURCE_BONUS.get(item.get("source_family"), 3)
    return min(value, 95)


def top_items(items, limit):
    return sorted(
        items,
        key=lambda item: (
            recommendation_score(item),
            1 if item.get("image") else 0,
            item.get("source_family") or "",
            item.get("title") or "",
        ),
        reverse=True,
    )[:limit]


def truncate(text, limit):
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def markdown_escape(text):
    return str(text or "").replace("[", "［").replace("]", "］")


def clean_image_url(value):
    value = (value or "").strip()
    if value.startswith("//"):
        value = "https:" + value
    if not value.startswith(("http://", "https://")):
        return ""
    if any(token in value.lower() for token in ["placeholder", "blank.gif", "transparent.gif"]):
        return ""
    return value


def card_elements(group, items, total_count, include_images=False):
    date = group.get("date") or "今日"
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**{date} 每日情报已更新**\n"
                    f"从当天 {total_count} 条去重选品里，优先推荐下面 5 个。"
                ),
            },
        },
        {"tag": "hr"},
    ]

    for index, item in enumerate(items, 1):
        title = markdown_escape(truncate(item.get("title") or "未命名产品", 52))
        category = item.get("category") or "未分类"
        source = markdown_escape(truncate(source_label(item), 24))
        reason = markdown_escape(truncate(recommend_reason(item), 86))
        score = recommendation_score(item)
        url = item_link(item)
        image = clean_image_url(item.get("image", ""))
        image_md = ""
        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": image_md
                    + (
                        f"**{index}. {title}**\n"
                        f"`{category}`  推荐指数 **{score}/100**  来源：{source}\n"
                        f"推荐理由：{reason}\n"
                        f"[打开原链接]({url})"
                    ),
                },
            }
        )
        if index < len(items):
            elements.append({"tag": "hr"})

    elements.append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看完整 30 条"},
                    "url": SITE_URL,
                    "type": "primary",
                }
            ],
        }
    )
    return elements


def sign_payload(secret):
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256).digest()
    return timestamp, base64.b64encode(digest).decode("utf-8")


def post_payload(webhook_url, payload):
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as response:
        return json.loads(response.read().decode("utf-8"))


def send_post(webhook_url, secret, title, blocks):
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": blocks,
                }
            }
        },
    }
    if secret:
        timestamp, sign = sign_payload(secret)
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    return post_payload(webhook_url, payload)


def send_card(webhook_url, secret, title, elements):
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "turquoise",
                "title": {"tag": "plain_text", "content": title},
            },
            "elements": elements,
        },
    }
    if secret:
        timestamp, sign = sign_payload(secret)
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    return post_payload(webhook_url, payload)


def latest_daily_group(data):
    groups = data.get("daily_groups") or []
    if not groups:
        return None
    return groups[0]


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30, help="Maximum daily picks to push.")
    parser.add_argument("--top-limit", type=int, default=5, help="Number of highlighted picks in the card.")
    parser.add_argument("--min-count", type=int, default=1, help="Skip push unless the latest daily group has at least this many items.")
    parser.add_argument("--require-today", action="store_true", help="Skip push unless the latest daily group date is today in Asia/Shanghai.")
    parser.add_argument("--not-before-hour", type=int, default=None, help="Skip push before this Asia/Shanghai hour.")
    parser.add_argument("--sent-log", default="", help="JSON file used to skip duplicate same-day pushes.")
    parser.add_argument("--chunk-size", type=int, default=10, help="Items per Feishu message.")
    parser.add_argument("--format", choices=["card", "post"], default="card", help="Feishu message format.")
    parser.add_argument("--no-images", action="store_true", help="Disable external image elements in Feishu cards.")
    parser.add_argument("--dry-run", action="store_true", help="Print messages instead of sending.")
    args = parser.parse_args()

    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
    secret = os.environ.get("FEISHU_WEBHOOK_SECRET", "").strip()
    data = load_json(INSIGHT_DIR / "data.raw.json", {})
    group = latest_daily_group(data)
    if not group:
        print("feishu_push=skipped reason=no_daily_group")
        return

    date = group.get("date") or "今日"
    now = dt.datetime.now(ZoneInfo("Asia/Shanghai"))
    if args.not_before_hour is not None and now.hour < args.not_before_hour:
        print(f"feishu_push=skipped reason=before_window hour={now.hour} not_before_hour={args.not_before_hour}")
        return
    if args.require_today:
        current_day = now.date().isoformat()
        if date != current_day:
            print(f"feishu_push=skipped reason=not_today date={date} today={current_day}")
            return

    sent_log = {}
    if args.sent_log:
        sent_log = load_json(args.sent_log, {})
        if sent_log.get(date, {}).get("sent"):
            print(f"feishu_push=skipped reason=already_sent date={date} sent_at={sent_log[date].get('sent_at', '')}")
            return

    items = (group.get("items") or [])[: args.limit]
    if not items:
        print("feishu_push=skipped reason=no_items")
        return
    if len(items) < args.min_count:
        print(f"feishu_push=skipped reason=below_min_count items={len(items)} min_count={args.min_count}")
        return

    total = len(items)
    highlighted = top_items(items, args.top_limit)
    title_prefix = f"Design Daily｜{date} 最推荐 5 个选品"
    if args.dry_run:
        print(json.dumps({"title": title_prefix, "card": card_elements(group, highlighted, total, not args.no_images)}, ensure_ascii=False, indent=2))
        return

    if not webhook_url:
        print("feishu_push=skipped reason=missing_FEISHU_WEBHOOK_URL")
        return

    try:
        if args.format == "post":
            fallback = [
                [
                    {"tag": "text", "text": f"{date} 最推荐 5 个选品已更新，请打开完整数据池查看：\n"},
                    {"tag": "a", "text": "打开完整数据池", "href": SITE_URL},
                ]
            ]
            result = send_post(webhook_url, secret, title_prefix, fallback)
        else:
            result = send_card(webhook_url, secret, title_prefix, card_elements(group, highlighted, total, not args.no_images))
        if args.sent_log:
            sent_log[date] = {
                "sent": True,
                "sent_at": now.isoformat(timespec="seconds"),
                "format": args.format,
                "top_limit": len(highlighted),
                "total": total,
            }
            write_json(args.sent_log, sent_log)
        print(f"feishu_push=sent format={args.format} top={len(highlighted)} result={result}")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(f"feishu_push=failed error={exc}") from exc


if __name__ == "__main__":
    main()
