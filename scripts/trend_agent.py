#!/usr/bin/env python3
"""Generate a lightweight trend report from the product pool."""

import argparse
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from collections import Counter

from insight_common import DATA_DIR, load_env, load_json, now_iso, write_json
from insight_config import RETIRED_CATEGORIES

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
SSL_CONTEXT = ssl._create_unverified_context()


def deepseek_model():
    raw = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash").strip()
    aliases = {
        "deepseek-v4-flash": "deepseek-v4-flash",
        "deepseek-v4-pro": "deepseek-v4-pro",
        "deepseek-v4": "deepseek-v4-flash",
        "deepseek-v3.2": "deepseek-v3.2",
        "deepseek-chat": "deepseek-chat",
        "deepseek-reasoner": "deepseek-reasoner",
    }
    return aliases.get(raw.lower(), raw)


def top_products(products, limit):
    return sorted(
        products,
        key=lambda item: (
            int(item.get("selection_score") or 0),
            int(item.get("seen_count") or 0),
            item.get("last_seen") or "",
        ),
        reverse=True,
    )[:limit]


def local_report(products, limit=80):
    category_counter = Counter(item.get("category") or "未分类" for item in products)
    source_counter = Counter()
    tag_counter = Counter()
    for item in products:
        for source in item.get("sources", []):
            source_counter[source.get("source") or "未知来源"] += 1
        for tag in item.get("trend_tags", []) or item.get("tags", []):
            tag_counter[tag] += 1
    picks = top_products(products, limit)[:20]
    return {
        "generated_at": now_iso(),
        "source": "local_summary",
        "summary": "本地趋势摘要。接入 DeepSeek 后会生成更完整的品类方向、机会点和风险判断。",
        "hot_categories": dict(category_counter.most_common(12)),
        "hot_sources": dict(source_counter.most_common(12)),
        "hot_tags": dict(tag_counter.most_common(20)),
        "recommended": [
            {
                "title": item.get("title"),
                "category": item.get("category"),
                "score": item.get("selection_score"),
                "reason": item.get("ai_reason") or item.get("summary", "")[:120],
            }
            for item in picks
        ],
    }


def deepseek_report(products, api_key, limit=80):
    sample = [
        {
            "title": item.get("title"),
            "category": item.get("category"),
            "score": item.get("selection_score"),
            "tags": (item.get("trend_tags") or item.get("tags") or [])[:6],
            "summary": (item.get("ai_reason") or item.get("summary") or "")[:160],
            "source_count": item.get("seen_count"),
        }
        for item in top_products(products, limit)
    ]
    schema = {
        "summary": "",
        "hot_categories": [],
        "hot_signals": [],
        "recommended_directions": [],
        "avoid_or_watch": [],
        "next_search_keywords": [],
    }
    prompt = f"""
你是产品选品趋势智能体。请基于这批产品线索，按以下选品标准做趋势分析：
- 实用为先
- 高频需求
- 打击面广
- 产品功能没有明显短板
- 售价最好大于 35 RMB
- 3 秒看懂
- 功能成立后再叠加情绪价值

请只返回 JSON，不要解释。JSON 结构：
{json.dumps(schema, ensure_ascii=False)}

产品样本：
{json.dumps(sample, ensure_ascii=False)}
"""
    body = {
        "model": deepseek_model(),
        "messages": [
            {"role": "system", "content": "你只输出合法 JSON。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 1800,
        "response_format": {"type": "json_object"},
    }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60, context=SSL_CONTEXT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code != 400:
            raise
        body.pop("response_format", None)
        req = urllib.request.Request(
            DEEPSEEK_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60, context=SSL_CONTEXT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    text = payload["choices"][0]["message"]["content"].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    report = json.loads(text)
    report["generated_at"] = now_iso()
    report["source"] = "deepseek"
    return report


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=80, help="How many top products to summarize.")
    args = parser.parse_args()

    products = [
        item
        for item in load_json(DATA_DIR / "products.json", [])
        if item.get("category") not in RETIRED_CATEGORIES
    ]
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    try:
        report = deepseek_report(products, api_key, args.limit) if api_key else local_report(products, args.limit)
        if api_key:
            time.sleep(0.3)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        print(f"fallback local trend report ({exc})")
        report = local_report(products, args.limit)
    write_json(DATA_DIR / "trends.json", report)
    print(f"trend_report={report.get('source')} limit={args.limit}")


if __name__ == "__main__":
    main()
