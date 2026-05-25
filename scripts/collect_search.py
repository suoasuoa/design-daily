#!/usr/bin/env python3
"""Collect open-web search results from the configured search job matrix."""

import argparse
import datetime as dt
from html.parser import HTMLParser
import re
import ssl
import time
import urllib.parse
import urllib.request

from insight_common import RAW_DIR, ensure_dirs, load_json, stable_hash, strip_html, write_json


SSL_CONTEXT = ssl._create_unverified_context()


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


def is_product_like_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = parsed.netloc.lower()
    path = parsed.path.lower().strip("/")
    query = urllib.parse.parse_qs(parsed.query)
    if any(host.endswith(domain) for domain in ["duckduckgo.com", "google.com", "bing.com", "baidu.com"]):
        return False
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


def fetch_results(query, timeout=25):
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
    source = urllib.parse.urlparse(url).netloc.replace("www.", "") or "Open Web Search"
    tags = [
        job.get("category", ""),
        "公开搜索",
        job.get("intent_note", ""),
        job.get("source_group", ""),
    ]
    return {
        "id": stable_hash(f"{job.get('id')}|{url}|{title}"),
        "title": re.sub(r"\s+", " ", title)[:160],
        "reason": snippet[:260] or f"Open web search result for {job.get('query')}",
        "source": source,
        "category": job.get("category"),
        "creator": "open web search",
        "score": 0,
        "likes": 0,
        "url": url,
        "image": "",
        "tags": [tag for tag in tags if tag],
        "search_query": job.get("query"),
        "search_intent": job.get("intent"),
        "added": dt.date.today().isoformat(),
        "collected_at": dt.date.today().isoformat(),
    }


def rotate_jobs(jobs, limit_jobs, offset=None):
    if not jobs:
        return []
    if offset is None:
        offset = (dt.date.today().timetuple().tm_yday * limit_jobs) % len(jobs)
    ordered = jobs[offset:] + jobs[:offset]
    return ordered[:limit_jobs]


def collect(jobs, limit_jobs=40, per_job=4, sleep=1.0, offset=None):
    collected = []
    for job in rotate_jobs(jobs, limit_jobs, offset):
        try:
            results = [result for result in fetch_results(job["query"]) if is_product_like_url(result.get("url", ""))][:per_job]
            leads = [lead_from_result(job, result) for result in results if result.get("title") and result.get("url")]
            collected.extend(leads)
            print(f"{job['category']} | {job['query']}: {len(leads)}")
        except Exception as exc:
            print(f"{job.get('query')}: failed ({exc})")
        if sleep:
            time.sleep(sleep)
    return collected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-jobs", type=int, default=40, help="Maximum search jobs to run.")
    parser.add_argument("--per-job", type=int, default=4, help="Maximum search results per job.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Delay between search requests.")
    parser.add_argument("--offset", type=int, default=None, help="Optional start offset in the search job matrix.")
    args = parser.parse_args()

    ensure_dirs()
    jobs_payload = load_json("data/search_jobs.json", {})
    jobs = jobs_payload.get("jobs", [])
    if not jobs:
        raise SystemExit("No search jobs found. Run scripts/search_jobs.py first.")

    leads = collect(jobs, args.limit_jobs, args.per_job, args.sleep, args.offset)
    path = RAW_DIR / f"search-{dt.date.today().isoformat()}.json"
    write_json(path, leads)
    print(f"saved={path} items={len(leads)}")


if __name__ == "__main__":
    main()
