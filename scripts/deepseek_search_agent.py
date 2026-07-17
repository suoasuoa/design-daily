#!/usr/bin/env python3
"""Use DeepSeek to plan, execute, and pre-screen real product searches."""

import argparse
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
import http.client
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from collect_search import fetch_results, source_meta_for_url
from insight_common import (
    DATA_DIR,
    RAW_DIR,
    canonical_url,
    clean_direct_product_url,
    ensure_dirs,
    load_env,
    load_json,
    now_iso,
    stable_hash,
    strip_html,
    today,
    write_json,
)
from insight_config import (
    CATEGORIES,
    CATEGORY_REVIEW_RULES,
    SEARCH_INTENTS,
    SOURCE_DOMAIN_META,
    SOURCE_GROUP_QUALITY,
)


DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
SSL_CONTEXT = ssl._create_unverified_context()
USER_AGENT = "Mozilla/5.0 DesignDailyDeepSeekAgent/1.0"
PRE_REVIEW_VERSION = 1


class PageMetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title_parts = []
        self.in_title = False
        self.description = ""
        self.image = ""
        self.canonical = ""

    def handle_starttag(self, tag, attrs):
        attrs = {str(key).lower(): value for key, value in attrs if key}
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            prop = str(attrs.get("property") or attrs.get("name") or "").lower()
            content = str(attrs.get("content") or "").strip()
            if not self.description and prop in {"og:description", "twitter:description", "description"}:
                self.description = content
            if not self.image and prop in {"og:image", "og:image:url", "twitter:image", "twitter:image:src"}:
                self.image = content
        if tag == "link" and "canonical" in str(attrs.get("rel") or "").lower():
            self.canonical = str(attrs.get("href") or "").strip()

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    @property
    def title(self):
        return strip_html(" ".join(self.title_parts)).strip()


def deepseek_model():
    return os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash"


def parse_json_response(text):
    text = str(text or "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        text = match.group(0)
    return json.loads(text)


def call_deepseek(prompt, max_tokens=7000, attempts=3):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required for the search agent")
    body = {
        "model": deepseek_model(),
        "messages": [
            {"role": "system", "content": "你是严格的产品搜索智能体，只输出合法 JSON。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    recoverable = (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
        ConnectionError,
        OSError,
        http.client.HTTPException,
    )
    last_error = None
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(
            DEEPSEEK_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120, context=SSL_CONTEXT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return parse_json_response(payload["choices"][0]["message"]["content"])
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 400 and body.pop("response_format", None):
                continue
        except recoverable as exc:
            last_error = exc
        print(f"deepseek_retry attempt={attempt}/{attempts} error={last_error}", flush=True)
        if attempt < attempts:
            time.sleep(attempt * 2)
    raise RuntimeError(f"DeepSeek request failed after retries: {last_error}")


def accepted_today():
    products = load_json(DATA_DIR / "products.json", [])
    current_day = today()
    rows = [item for item in products if item.get("first_seen") == current_day]
    return len(rows), Counter(item.get("category") or "未分类" for item in rows)


def seen_urls():
    seen = set()
    index = load_json(DATA_DIR / "dedupe_index.json", {})
    seen.update(canonical_url(url) for url in (index.get("url_index") or {}) if url)
    for path in [DATA_DIR / "products.json", DATA_DIR / "rejected_category.json"]:
        for item in load_json(path, []):
            url = canonical_url(item.get("url") or "")
            if url:
                seen.add(url)
    return seen


def allowed_domains():
    return sorted(SOURCE_DOMAIN_META)


def fallback_query_jobs(limit, round_index=0):
    payload = load_json(DATA_DIR / "search_jobs.json", {})
    jobs = [job for job in payload.get("jobs", []) if job.get("category") in CATEGORIES]
    if not jobs:
        return []
    start = (round_index * limit) % len(jobs)
    ordered = jobs[start:] + jobs[:start]
    return ordered[:limit]


def plan_queries(query_count, target, round_index):
    current_count, current_categories = accepted_today()
    rules = "\n".join(f"- {category}: {CATEGORY_REVIEW_RULES[category]}" for category in CATEGORIES)
    domains = ", ".join(allowed_domains())
    schema = {
        "queries": [
            {
                "category": "one allowed category",
                "query": "precise search query, usually with site:domain",
                "source_group": "award_gallery/editorial_main/packaging_specialist/design_community/market_signal_strong",
                "intent": "buy_sample/adapt/trend",
                "reason": "why this query can find concrete products",
            }
        ]
    }
    prompt = f"""
你负责为选品团队制定第 {round_index + 1} 轮真实网页搜索计划。今天已经严格通过 {current_count}/{target} 条，品类分布：
{json.dumps(dict(current_categories), ensure_ascii=False)}

请生成最多 {query_count} 条高精度搜索词。目标是找到数据库从未收录的具体产品或具体设计案例，不要求当天发布。

硬规则：
1. 只搜索下面的允许品类，优先今天数量少的品类；同一品类计划不超过总搜索词的 20%。
2. 70% 搜索词必须带 site:白名单域名，优先设计奖、设计媒体、包装网站、众筹和真实商品页。
3. 搜索词必须指向具体产品页或具体案例页，避免 search、collection、tag、topic、首页和泛文章。
4. 明确排除普通基础款、换色/印花/普通联名、建筑新闻、汽车、宠物用品、泛科技新闻和已停用品类。
5. 中英文关键词混合轮换；第二轮以后换产品结构、功能痛点、材料、交互、DIY/概念原型等角度，不要重复上一轮套路。
6. 水杯、灯、厨具、桌搭等高频品类也要寻找明确功能创新，不要只搜 aesthetic/design。

品类定义：
{rules}

白名单域名：
{domains}

只返回 JSON：
{json.dumps(schema, ensure_ascii=False)}
"""
    try:
        rows = call_deepseek(prompt, max_tokens=8000).get("queries", [])
    except RuntimeError as exc:
        print(f"query_plan_fallback error={exc}", flush=True)
        rows = []

    planned = []
    seen = set()
    for index, row in enumerate(rows):
        category = row.get("category")
        query = re.sub(r"\s+", " ", str(row.get("query") or "")).strip()
        if category not in CATEGORIES or not query:
            continue
        key = query.lower()
        if key in seen:
            continue
        seen.add(key)
        planned.append(
            {
                "id": f"deepseek:{today()}:{round_index}:{index}:{stable_hash(query)}",
                "category": category,
                "query": query,
                "source_group": row.get("source_group") or "curated_keyword",
                "quality_tier": SOURCE_GROUP_QUALITY.get(row.get("source_group"), "standard"),
                "intent": row.get("intent") if row.get("intent") in SEARCH_INTENTS else "adapt",
                "intent_note": str(row.get("reason") or "")[:180],
            }
        )
        if len(planned) >= query_count:
            break

    for job in fallback_query_jobs(query_count, round_index):
        if len(planned) >= query_count:
            break
        key = str(job.get("query") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        planned.append(job)
    return planned


def search_one(job, per_query):
    rows = []
    try:
        results = fetch_results(job["query"], timeout=12)
    except Exception as exc:
        return rows, f"search_failed query={job.get('query')} error={exc}"
    for result in results:
        url = clean_direct_product_url(result.get("url") or "")
        meta = source_meta_for_url(url)
        if not url or not meta:
            continue
        title = strip_html(result.get("title") or "").strip()
        if not title:
            continue
        rows.append(
            {
                "id": stable_hash(url),
                "url": url,
                "title": title[:180],
                "snippet": strip_html(result.get("snippet") or "")[:500],
                "category_hint": job.get("category"),
                "query": job.get("query"),
                "source_group": job.get("source_group") or "curated_keyword",
                "quality_tier": job.get("quality_tier") or "standard",
                "intent": job.get("intent") or "adapt",
                "source": meta.get("source"),
                "source_type": meta.get("source_type"),
            }
        )
        if len(rows) >= per_query:
            break
    return rows, f"search_ok category={job.get('category')} results={len(rows)} query={job.get('query')}"


def execute_searches(jobs, per_query=10, workers=10):
    rows = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(search_one, job, per_query): job for job in jobs}
        for future in as_completed(futures):
            found, message = future.result()
            rows.extend(found)
            print(message, flush=True)
    unique = {}
    for row in rows:
        unique.setdefault(canonical_url(row.get("url") or ""), row)
    return list(unique.values())


def balanced_limit(rows, limit):
    buckets = defaultdict(deque)
    for row in rows:
        buckets[row.get("category_hint") or "未分类"].append(row)
    selected = []
    while len(selected) < limit and any(buckets.values()):
        for category in CATEGORIES:
            if buckets[category]:
                selected.append(buckets[category].popleft())
                if len(selected) >= limit:
                    break
    return selected


def fetch_page_meta(row, timeout=15):
    url = row["url"]
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as response:
            content_type = response.headers.get("content-type", "").lower()
            if "html" not in content_type and "xhtml" not in content_type:
                return row
            html = response.read(600_000).decode("utf-8", errors="replace")
    except Exception as exc:
        row["page_error"] = str(exc)[:160]
        return row
    parser = PageMetaParser()
    parser.feed(html)
    canonical = urllib.parse.urljoin(url, parser.canonical) if parser.canonical else url
    canonical = clean_direct_product_url(canonical) or url
    if not source_meta_for_url(canonical):
        canonical = url
    row["url"] = canonical
    row["page_title"] = parser.title[:200]
    row["description"] = strip_html(parser.description)[:700]
    row["image"] = urllib.parse.urljoin(url, parser.image) if parser.image else ""
    return row


def enrich_pages(rows, workers=12):
    enriched = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(fetch_page_meta, dict(row)) for row in rows]
        for future in as_completed(futures):
            enriched.append(future.result())
    return enriched


def compact_candidate(row):
    return {
        "id": row.get("id"),
        "category_hint": row.get("category_hint"),
        "title": (row.get("page_title") or row.get("title") or "")[:180],
        "search_title": (row.get("title") or "")[:180],
        "snippet": (row.get("snippet") or "")[:400],
        "description": (row.get("description") or "")[:600],
        "source": row.get("source"),
        "url": row.get("url"),
        "has_image": bool(row.get("image")),
    }


def screen_batch(batch):
    rules = "\n".join(f"- {category}: {CATEGORY_REVIEW_RULES[category]}" for category in CATEGORIES)
    schema = {
        "items": [
            {
                "id": "candidate id",
                "keep": True,
                "category": "one allowed category",
                "confidence": 0,
                "relevance": 0,
                "innovation": 0,
                "utility": 0,
                "clarity": 0,
                "reason": "specific product and innovation evidence",
            }
        ]
    }
    prompt = f"""
你是 DeepSeek 选品搜索智能体的候选预审员。这里只做严格预筛，后面还有一次完整终审。

必须拒绝：搜索/合集/分类页、泛文章、建筑/汽车/宠物、标题和摘要无法确认具体产品、普通基础款、仅换颜色图案或联名、创新点只能写成“设计感/材质好看”的内容。
可以保留：明确单品、可买样产品、功能/结构/材料/交互创新、可转化的 DIY 或概念原型。必须符合指定品类实体边界。
预筛通过必须同时满足 relevance>=8、innovation>=6、clarity>=7、confidence>=7，并在 reason 中说清楚具体产品和创新证据。不能用“可能、或许、需确认”。

品类定义：
{rules}

只返回 JSON：
{json.dumps(schema, ensure_ascii=False)}

候选：
{json.dumps([compact_candidate(row) for row in batch], ensure_ascii=False)}
"""
    try:
        result = call_deepseek(prompt, max_tokens=7000).get("items", [])
    except RuntimeError as exc:
        print(f"screen_batch_failed size={len(batch)} error={exc}", flush=True)
        return []
    by_id = {row.get("id"): row for row in batch}
    kept = []
    for decision in result:
        candidate = by_id.get(decision.get("id"))
        category = decision.get("category")
        if not candidate or category not in CATEGORIES or not decision.get("keep"):
            continue
        scores = {
            key: max(0, min(10, int(decision.get(key) or 0)))
            for key in ("confidence", "relevance", "innovation", "utility", "clarity")
        }
        if scores["confidence"] < 7 or scores["relevance"] < 8 or scores["innovation"] < 6 or scores["clarity"] < 7:
            continue
        reason = str(decision.get("reason") or "").strip()
        if not reason or any(token in reason.lower() for token in ("可能", "或许", "需确认", "unclear", "perhaps")):
            continue
        candidate = dict(candidate)
        candidate["agent_decision"] = {
            "category": category,
            "reason": reason[:320],
            **scores,
        }
        kept.append(candidate)
    return kept


def screen_candidates(rows, batch_size=20, workers=6):
    batches = [rows[index : index + batch_size] for index in range(0, len(rows), batch_size)]
    kept = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(screen_batch, batch) for batch in batches]
        for future in as_completed(futures):
            accepted = future.result()
            kept.extend(accepted)
            print(f"agent_screen progress_kept={len(kept)}", flush=True)
    return kept


def lead_from_candidate(row, round_index):
    decision = row["agent_decision"]
    meta = source_meta_for_url(row.get("url") or "") or {}
    title = strip_html(row.get("page_title") or row.get("title") or "").strip()
    description = strip_html(row.get("description") or row.get("snippet") or "").strip()
    reason = f"{decision['reason']}。页面证据：{description}"[:700]
    return {
        "id": stable_hash(f"deepseek-agent|{row.get('url')}|{title}"),
        "title": title[:180],
        "reason": reason,
        "source": meta.get("source") or row.get("source") or "DeepSeek Curated Search",
        "source_type": meta.get("source_type") or row.get("source_type") or "",
        "category": decision["category"],
        "creator": meta.get("source") or row.get("source") or "DeepSeek Search Agent",
        "score": 0,
        "likes": 0,
        "url": clean_direct_product_url(row.get("url") or ""),
        "image": row.get("image") or "",
        "tags": [
            decision["category"],
            "deepseek_search_agent",
            row.get("source_group") or "curated_keyword",
            row.get("intent") or "adapt",
        ],
        "search_query": row.get("query"),
        "search_intent": row.get("intent") or "adapt",
        "source_group": row.get("source_group") or "curated_keyword",
        "quality_tier": row.get("quality_tier") or "standard",
        "agent_pre_review": {**decision, "version": PRE_REVIEW_VERSION, "round": round_index + 1},
        "added": today(),
        "collected_at": today(),
        "collected_at_iso": now_iso(),
    }


def merge_leads(path, leads):
    existing = load_json(path, [])
    if isinstance(existing, dict):
        existing = existing.get("items", [])
    merged = []
    seen = set()
    for item in list(existing) + list(leads):
        key = canonical_url(item.get("url") or "") or item.get("id")
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged, len(existing), len(merged) - len(existing)


def write_agent_report(stats):
    path = DATA_DIR / "reports" / f"deepseek-search-agent-{today()}.json"
    report = load_json(path, {"date": today(), "rounds": []})
    report.setdefault("rounds", []).append(stats)
    report["generated_at"] = now_iso()
    report["total_kept"] = sum(int(row.get("kept") or 0) for row in report["rounds"])
    write_json(path, report)


def run_agent(args):
    current_count, current_categories = accepted_today()
    jobs = plan_queries(args.query_count, args.target, args.round)
    print(f"agent_plan queries={len(jobs)} current={current_count}/{args.target}", flush=True)
    results = execute_searches(jobs, args.per_query, args.search_workers)
    known = seen_urls()
    fresh = [row for row in results if canonical_url(row.get("url") or "") not in known]
    fresh = balanced_limit(fresh, args.max_pages)
    print(f"agent_search results={len(results)} fresh={len(fresh)} page_limit={args.max_pages}", flush=True)
    enriched = enrich_pages(fresh, args.page_workers)
    screened = screen_candidates(enriched, args.batch_size, args.screen_workers)
    leads = [lead_from_candidate(row, args.round) for row in screened]
    leads = [lead for lead in leads if lead.get("url") and lead.get("title")]
    path = RAW_DIR / f"deepseek-agent-{today()}.json"
    merged, existing, added = merge_leads(path, leads)
    write_json(path, merged)
    by_category = Counter(lead.get("category") for lead in leads)
    stats = {
        "round": args.round + 1,
        "generated_at": now_iso(),
        "accepted_before": current_count,
        "accepted_by_category_before": dict(current_categories),
        "queries": len(jobs),
        "search_results": len(results),
        "fresh_direct_urls": len(fresh),
        "pages_enriched": sum(bool(row.get("description") or row.get("page_title")) for row in enriched),
        "pre_screened": len(enriched),
        "kept": len(leads),
        "added": added,
        "by_category": dict(by_category.most_common()),
    }
    write_agent_report(stats)
    print(
        f"deepseek_agent saved={path} existing={existing} screened={len(enriched)} "
        f"kept={len(leads)} added={added} total={len(merged)} categories={dict(by_category)}",
        flush=True,
    )
    return stats


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=30)
    parser.add_argument("--round", type=int, default=0)
    parser.add_argument("--query-count", type=int, default=60)
    parser.add_argument("--per-query", type=int, default=10)
    parser.add_argument("--max-pages", type=int, default=280)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--search-workers", type=int, default=10)
    parser.add_argument("--page-workers", type=int, default=12)
    parser.add_argument("--screen-workers", type=int, default=6)
    args = parser.parse_args()
    ensure_dirs()
    run_agent(args)


if __name__ == "__main__":
    main()
