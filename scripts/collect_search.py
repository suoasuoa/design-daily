#!/usr/bin/env python3
"""Collect open-web search results from the configured search job matrix."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
from html.parser import HTMLParser
import re
import ssl
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from insight_common import clean_direct_product_url, RAW_DIR, ensure_dirs, load_json, stable_hash, strip_html, today, write_json
from insight_config import SOURCE_DOMAIN_META


SSL_CONTEXT = ssl._create_unverified_context()
LOCAL_TZ = ZoneInfo("Asia/Shanghai")
DDGS_AVAILABLE = False

try:
    from ddgs import DDGS  # type: ignore
    DDGS_AVAILABLE = True
except Exception:
    DDGS_AVAILABLE = False


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


def is_product_like_url(url):
    if not source_meta_for_url(url):
        return False
    return bool(clean_direct_product_url(url))


def fetch_results(query, timeout=6):
    if DDGS_AVAILABLE:
        try:
            with DDGS(timeout=timeout) as ddgs:
                results = []
                for row in ddgs.text(query, max_results=12, safesearch="off"):
                    url = clean_duck_url(row.get("href") or row.get("url") or "")
                    title = row.get("title") or ""
                    snippet = row.get("body") or row.get("snippet") or ""
                    if title and url:
                        results.append({"url": url, "title": title, "snippet": snippet})
                if results:
                    return results
        except Exception:
            pass

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
    return {
        "id": stable_hash(f"{job.get('id')}|{url}|{title}"),
        "title": re.sub(r"\s+", " ", title)[:160],
        "reason": snippet[:260] or f"Open web search result for {job.get('query')}",
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
        results = [result for result in fetch_results(job["query"]) if is_product_like_url(result.get("url", ""))][:per_job]
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
