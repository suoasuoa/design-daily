#!/usr/bin/env python3
"""Collect open-web search results from the configured search job matrix."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
from html.parser import HTMLParser
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from insight_common import RAW_DIR, ensure_dirs, load_json, stable_hash, strip_html, today, write_json
from insight_config import CATEGORY_KEYWORDS, SOURCE_DOMAIN_META


SSL_CONTEXT = ssl._create_unverified_context()
LOCAL_TZ = ZoneInfo("Asia/Shanghai")
SOCIAL_HOSTS = {"douyin.com", "xiaohongshu.com", "instagram.com"}
PRODUCT_SIGNAL_WORDS = [
    "好物", "种草", "开箱", "测评", "推荐", "新品", "同款", "礼物", "礼盒", "包装",
    "收纳", "便携", "高颜值", "实用", "神器", "设计", "创意", "有趣", "好看", "爆款",
    "概念", "手作", "自制", "改造", "diy", "prototype", "concept", "product", "design",
    "unboxing", "review", "gift", "packaging", "gadget", "organizer", "setup", "accessory",
    "case", "bottle", "cup", "lamp", "bag", "wallet", "charger", "calendar", "hoodie", "shirt",
]
LOW_VALUE_WORDS = [
    "招聘", "下载", "登录", "账号", "隐私", "协议", "直播", "合集", "主页", "个人页",
    "challenge", "profile", "login", "download", "privacy", "terms",
]


class DuckDuckGoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current = None
        self.capture_title = False
        self.capture_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "")
        if tag == "a" and "result__a" in classes:
            self.current = {"url": clean_duck_url(attrs.get("href", "")), "title": "", "snippet": ""}
            self.capture_title = True
        elif self.current and tag in {"a", "div"} and "result__snippet" in classes:
            self.capture_snippet = True

    def handle_data(self, data):
        if self.current and self.capture_title:
            self.current["title"] += data
        elif self.current and self.capture_snippet:
            self.current["snippet"] += data

    def handle_endtag(self, tag):
        if self.current and self.capture_title and tag == "a":
            self.capture_title = False
            if self.current.get("title") and self.current.get("url"):
                self.results.append(self.current)
        if self.current and self.capture_snippet and tag in {"a", "div"}:
            self.capture_snippet = False
            self.current = None


def clean_duck_url(url):
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    if "uddg" in params:
        return urllib.parse.unquote(params["uddg"][0])
    if url.startswith("//"):
        return "https:" + url
    return url


def source_meta_for_url(url):
    host = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    for domain, meta in SOURCE_DOMAIN_META.items():
        if host == domain or host.endswith("." + domain):
            return meta
    return None


def social_host(url):
    host = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    for domain in SOCIAL_HOSTS:
        if host == domain or host.endswith("." + domain):
            return domain
    return ""


def is_social_content_url(url):
    domain = social_host(url)
    if not domain:
        return False
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lower()
    if domain == "douyin.com":
        return bool(re.search(r"/video/[0-9]+", path))
    if domain == "xiaohongshu.com":
        return bool(re.search(r"/(explore|discovery/item)/[0-9a-z]+", path))
    if domain == "instagram.com":
        return bool(re.search(r"/(p|reel|reels)/[a-z0-9_-]+", path))
    return False


def passes_selection_signal(job, result):
    result_text = " ".join(
        [
            result.get("title", ""),
            result.get("snippet", ""),
        ]
    ).lower()
    full_text = " ".join(
        [
            job.get("category", ""),
            job.get("query", ""),
            result.get("title", ""),
            result.get("snippet", ""),
        ]
    ).lower()
    if any(word.lower() in result_text for word in LOW_VALUE_WORDS):
        return False
    category = job.get("category", "")
    category_words = [category] + CATEGORY_KEYWORDS.get(category, [])
    category_hit = any(word.lower() in result_text for word in category_words if word)
    if social_host(result.get("url", "")):
        product_hit = any(word.lower() in result_text for word in PRODUCT_SIGNAL_WORDS)
        return category_hit and product_hit
    if category_hit:
        return True
    return any(word.lower() in full_text for word in PRODUCT_SIGNAL_WORDS)


def is_product_like_url(url):
    meta = source_meta_for_url(url)
    if not meta:
        return False
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = parsed.netloc.lower()
    path = parsed.path.lower().strip("/")
    query = urllib.parse.parse_qs(parsed.query)
    if any(host.endswith(domain) for domain in ["duckduckgo.com", "google.com", "bing.com", "baidu.com"]):
        return False
    if social_host(url):
        return is_social_content_url(url)
    if any(key in query for key in ["q", "query", "keyword", "search", "s", "wd"]):
        return False
    bad_segments = {
        "search", "tag", "tags", "category", "categories", "collections", "topics",
        "explore", "discover", "feed", "archive", "page", "pages",
    }
    segments = [segment for segment in path.split("/") if segment]
    if segments and segments[-1] in bad_segments:
        return False
    if any(segment in bad_segments for segment in segments[:2]) and len(segments) <= 3:
        return False
    return True


def fetch_results(query, timeout=6):
    tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
    use_tavily = os.environ.get("USE_TAVILY_SEARCH", "").strip().lower() in {"1", "true", "yes"}
    if tavily_key and use_tavily:
        return fetch_tavily_results(query, tavily_key, timeout=max(15, timeout))
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 DesignDailyInsight/1.0",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    parser = DuckDuckGoParser()
    parser.feed(html)
    return parser.results


def fetch_tavily_results(query, api_key, timeout=20):
    body = {
        "query": query,
        "topic": "general",
        "search_depth": "basic",
        "max_results": 8,
        "include_answer": False,
        "include_raw_content": False,
    }
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    results = []
    for item in payload.get("results", []):
        results.append(
            {
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "snippet": item.get("content", ""),
            }
        )
    return results


def lead_from_result(job, result):
    title = strip_html(result.get("title", "")).strip()
    snippet = strip_html(result.get("snippet", "")).strip()
    url = result.get("url", "")
    meta = source_meta_for_url(url) or {}
    source = meta.get("source") or urllib.parse.urlparse(url).netloc.replace("www.", "") or "Curated Web Search"
    tags = [
        job.get("category", ""),
        "白名单来源",
        job.get("intent_note", ""),
        job.get("source_group", ""),
    ]
    if social_host(url):
        tags.extend(["社媒公开索引", "需人工复核"])
    return {
        "id": stable_hash(f"{job.get('id')}|{url}|{title}"),
        "title": re.sub(r"\s+", " ", title)[:160],
        "reason": snippet[:260] or f"公开社媒索引命中：{job.get('query')}。需按实用、高频、功能、打击面和价格空间复核。",
        "source": source,
        "source_type": meta.get("source_type", ""),
        "category": job.get("category"),
        "creator": source,
        "score": 0,
        "likes": 0,
        "url": url,
        "image": "",
        "tags": [tag for tag in tags if tag],
        "search_query": job.get("query"),
        "search_intent": job.get("intent"),
        "source_group": job.get("source_group"),
        "quality_tier": job.get("quality_tier", "curated"),
        "added": today(),
        "collected_at": today(),
    }


def rotate_jobs(jobs, limit_jobs, offset=None):
    if not jobs:
        return []
    if limit_jobs <= 0 or limit_jobs >= len(jobs):
        limit_jobs = len(jobs)
    if offset is None:
        now = dt.datetime.now(LOCAL_TZ)
        run_bucket = 0 if now.hour < 11 else 1 if now.hour < 17 else 2
        offset = ((now.timetuple().tm_yday * 3 + run_bucket) * limit_jobs) % len(jobs)
    ordered = jobs[offset:] + jobs[:offset]
    return ordered[:limit_jobs]


def collect_one(job, per_job=4):
    try:
        results = [
            result
            for result in fetch_results(job["query"])
            if is_product_like_url(result.get("url", "")) and passes_selection_signal(job, result)
        ][:per_job]
        leads = [lead_from_result(job, result) for result in results if result.get("title") and result.get("url")]
        return leads, f"{job['category']} | {job['query']}: {len(leads)}"
    except Exception as exc:
        return [], f"{job.get('query')}: failed ({exc})"


def collect(jobs, limit_jobs=40, per_job=4, sleep=1.0, offset=None, workers=8):
    collected = []
    selected_jobs = rotate_jobs(jobs, limit_jobs, offset)
    if workers <= 1:
        for job in selected_jobs:
            leads, message = collect_one(job, per_job)
            collected.extend(leads)
            print(message, flush=True)
            if sleep:
                time.sleep(sleep)
        return collected

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for job in selected_jobs:
            futures.append(executor.submit(collect_one, job, per_job))
            if sleep:
                time.sleep(sleep)
        for future in as_completed(futures):
            leads, message = future.result()
            collected.extend(leads)
            print(message, flush=True)
    return collected


def merge_daily_leads(path, leads):
    existing = load_json(path, [])
    if isinstance(existing, dict):
        existing = existing.get("items", [])
    merged = []
    seen = set()
    for item in list(existing) + list(leads):
        if not isinstance(item, dict):
            continue
        key = item.get("id") or item.get("url") or item.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged, len(existing), len(merged) - len(existing)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-jobs", type=int, default=40, help="Maximum search jobs to run. Use 0 to run all jobs.")
    parser.add_argument("--per-job", type=int, default=4, help="Maximum search results per job.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Delay between search requests.")
    parser.add_argument("--offset", type=int, default=None, help="Optional start offset in the search job matrix.")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent search workers.")
    args = parser.parse_args()

    ensure_dirs()
    jobs_payload = load_json("data/search_jobs.json", {})
    jobs = jobs_payload.get("jobs", [])
    if not jobs:
        raise SystemExit("No search jobs found. Run scripts/search_jobs.py first.")

    leads = collect(jobs, args.limit_jobs, args.per_job, args.sleep, args.offset, args.workers)
    path = RAW_DIR / f"search-{today()}.json"
    merged, existing_count, added_count = merge_daily_leads(path, leads)
    write_json(path, merged)
    print(f"saved={path} fetched={len(leads)} existing={existing_count} added={added_count} total={len(merged)}")


if __name__ == "__main__":
    main()
