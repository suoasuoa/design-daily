#!/usr/bin/env python3
"""Score products with DeepSeek when available, otherwise use local heuristics."""

import argparse
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request

from insight_common import DATA_DIR, load_env, load_json, now_iso, write_json
from insight_config import SCORING_PRINCIPLES, SELECTION_WEIGHTS

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
SSL_CONTEXT = ssl._create_unverified_context()

USEFUL_WORDS = ["收纳", "整理", "便携", "折叠", "多功能", "防水", "模块", "磁吸", "省空间", "工具", "organizer", "portable", "foldable", "storage"]
FREQUENCY_WORDS = ["水杯", "灯", "桌", "键盘", "手机", "包", "厨", "日历", "充电", "杯", "wallet", "desk", "kitchen", "phone", "bag"]
BROAD_WORDS = ["水杯", "收纳", "桌搭", "厨具", "灯", "手机壳", "充电", "礼盒", "bag", "cup", "lamp", "desk", "kitchen"]
EMOTION_WORDS = ["可爱", "温暖", "治愈", "幽默", "惊喜", "反差", "质感", "高级", "cute", "warm", "playful", "premium"]
RISK_WORDS = ["概念", "装置", "艺术", "汽车", "耳机", "大型", "chair", "car", "concept", "installation"]


def deepseek_model():
    raw = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()
    aliases = {
        "deepseek-v4-flash": "deepseek-v4-flash",
        "deepseek-v4-pro": "deepseek-v4-pro",
        "deepseek-v4": "deepseek-v4-flash",
        "deepseek-v3.2": "deepseek-v3.2",
        "deepseek-chat": "deepseek-chat",
        "deepseek-reasoner": "deepseek-reasoner",
    }
    return aliases.get(raw.lower(), raw)


def clamp(value, low=0, high=10):
    return max(low, min(high, int(round(value))))


def hits(text, words):
    text = text.lower()
    return sum(1 for word in words if word.lower() in text)


def local_score(product):
    text = " ".join(
        [
            product.get("title", ""),
            product.get("summary", ""),
            product.get("category", ""),
            " ".join(product.get("tags", [])),
        ]
    )
    source_bonus = min(2, max(0, int(product.get("seen_count") or 1) - 1))
    utility = clamp(5 + hits(text, USEFUL_WORDS) * 1.2 - hits(text, RISK_WORDS))
    frequency = clamp(5 + hits(text, FREQUENCY_WORDS) * 1.1 - hits(text, RISK_WORDS))
    broad_appeal = clamp(5 + hits(text, BROAD_WORDS) * 1.0 + source_bonus - hits(text, RISK_WORDS))
    functionality = clamp(6 + hits(text, USEFUL_WORDS) * 0.6 - hits(text, ["概念", "concept", "装置"]))
    price_power = {"likely_over_35": 8, "unknown": 6, "risk_under_35": 3}.get(product.get("price_gate"), 6)
    clarity = clamp(6 + (1 if len(product.get("title", "")) <= 32 else -1) + hits(text, FREQUENCY_WORDS) * 0.4)
    emotion = clamp(5 + hits(text, EMOTION_WORDS) * 1.2)
    return {
        "utility": utility,
        "frequency": frequency,
        "broad_appeal": broad_appeal,
        "functionality": functionality,
        "price_power": price_power,
        "clarity": clarity,
        "emotion": emotion,
        "source": "local_heuristic",
    }


def weighted_total(scores):
    total = 0
    for key, weight in SELECTION_WEIGHTS.items():
        total += scores.get(key, 0) * 10 * weight
    return int(round(total))


def parse_json_response(text):
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        text = match.group(0)
    return json.loads(text)


def deepseek_score(product, api_key):
    schema = {
        "utility": 0,
        "frequency": 0,
        "broad_appeal": 0,
        "functionality": 0,
        "price_power": 0,
        "clarity": 0,
        "emotion": 0,
        "trend_tags": [],
        "reason": "",
        "risk": "",
    }
    prompt = f"""
你是产品选品分析师。请按下面标准评估产品，所有分数 0-10：
{chr(10).join("- " + item for item in SCORING_PRINCIPLES)}

产品：
标题：{product.get('title')}
品类：{product.get('category')}
摘要：{product.get('summary')}
标签：{', '.join(product.get('tags', []))}
来源次数：{product.get('seen_count')}
价格判断：{product.get('price_gate')}

只返回 JSON，不要解释。JSON 结构必须是：
{json.dumps(schema, ensure_ascii=False)}
"""
    body = {
        "model": deepseek_model(),
        "messages": [
            {"role": "system", "content": "你只输出合法 JSON。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 700,
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
        with urllib.request.urlopen(req, timeout=40, context=SSL_CONTEXT) as resp:
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
        with urllib.request.urlopen(req, timeout=40, context=SSL_CONTEXT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    result = parse_json_response(content)
    for key in SELECTION_WEIGHTS:
        result[key] = clamp(result.get(key, 0))
    result["trend_tags"] = result.get("trend_tags", [])[:8]
    result["source"] = "deepseek"
    return result


def score_products(products, limit=0, force=False, sleep=0.6):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    scored = 0
    for product in products:
        if limit and scored >= limit:
            break
        if product.get("selection_scores") and not force:
            continue
        try:
            if api_key:
                scores = deepseek_score(product, api_key)
                time.sleep(sleep)
            else:
                scores = local_score(product)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            print(f"fallback local score: {product.get('title')} ({exc})")
            scores = local_score(product)
        product["selection_scores"] = scores
        product["selection_score"] = weighted_total(scores)
        product["trend_tags"] = scores.get("trend_tags", []) or product.get("trend_tags", [])
        if scores.get("reason"):
            product["ai_reason"] = scores["reason"]
        if scores.get("risk"):
            product["ai_risk"] = scores["risk"]
        product["status"] = "scored"
        product["updated_at"] = now_iso()
        scored += 1
    return scored


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Score at most N unscored products.")
    parser.add_argument("--force", action="store_true", help="Rescore products with existing scores.")
    args = parser.parse_args()

    products = load_json(DATA_DIR / "products.json", [])
    count = score_products(products, args.limit, args.force)
    write_json(DATA_DIR / "products.json", products)
    print(f"scored={count} products={len(products)}")


if __name__ == "__main__":
    main()
