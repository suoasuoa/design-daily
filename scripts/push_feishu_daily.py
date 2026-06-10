#!/usr/bin/env python3
"""Push the latest daily 30-pick group to a Feishu custom bot webhook."""

import argparse
import base64
import hashlib
import hmac
import json
import os
import ssl
import time
import urllib.error
import urllib.request

from insight_common import INSIGHT_DIR, load_env, load_json


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


def truncate(text, limit):
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def line_blocks(items, start_index):
    blocks = []
    for offset, item in enumerate(items, start_index):
        title = truncate(item.get("title") or "未命名产品", 70)
        category = item.get("category") or "未分类"
        score = item.get("score") or 0
        source = truncate(source_label(item), 32)
        reason = truncate(recommend_reason(item), 90)
        blocks.append(
            [
                {"tag": "text", "text": f"{offset}. {title}\n"},
                {"tag": "text", "text": f"品类：{category}｜评分：{score}｜来源：{source}\n"},
                {"tag": "text", "text": f"推荐理由：{reason}\n"},
                {"tag": "a", "text": "打开原链接", "href": item_link(item)},
                {"tag": "text", "text": "\n"},
            ]
        )
    return blocks


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


def latest_daily_group(data):
    groups = data.get("daily_groups") or []
    if not groups:
        return None
    return groups[0]


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30, help="Maximum daily picks to push.")
    parser.add_argument("--chunk-size", type=int, default=10, help="Items per Feishu message.")
    parser.add_argument("--dry-run", action="store_true", help="Print messages instead of sending.")
    args = parser.parse_args()

    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
    secret = os.environ.get("FEISHU_WEBHOOK_SECRET", "").strip()
    data = load_json(INSIGHT_DIR / "data.raw.json", {})
    group = latest_daily_group(data)
    if not group:
        print("feishu_push=skipped reason=no_daily_group")
        return

    items = (group.get("items") or [])[: args.limit]
    if not items:
        print("feishu_push=skipped reason=no_items")
        return

    date = group.get("date") or "今日"
    total = len(items)
    header = [
        [
            {"tag": "text", "text": f"{date} 每日选品情报已更新，共 {total} 条。\n"},
            {"tag": "text", "text": "每条推荐语按实用、高频、功能、打击面、价格空间和来源可信度生成。\n"},
            {"tag": "a", "text": "打开完整数据池", "href": SITE_URL},
        ]
    ]

    title_prefix = f"Design Daily｜{date} 每日 30 个选品推荐"
    if args.dry_run:
        print(json.dumps({"title": title_prefix, "header": header}, ensure_ascii=False, indent=2))
        for start in range(0, total, args.chunk_size):
            chunk = items[start : start + args.chunk_size]
            print(json.dumps({"chunk": start // args.chunk_size + 1, "content": line_blocks(chunk, start + 1)}, ensure_ascii=False, indent=2))
        return

    if not webhook_url:
        print("feishu_push=skipped reason=missing_FEISHU_WEBHOOK_URL")
        return

    try:
        send_post(webhook_url, secret, title_prefix, header)
        for start in range(0, total, args.chunk_size):
            chunk = items[start : start + args.chunk_size]
            chunk_title = f"{title_prefix}（{start + 1}-{start + len(chunk)}）"
            result = send_post(webhook_url, secret, chunk_title, line_blocks(chunk, start + 1))
            print(f"feishu_push=sent chunk={start // args.chunk_size + 1} result={result}")
            time.sleep(0.4)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(f"feishu_push=failed error={exc}") from exc


if __name__ == "__main__":
    main()
