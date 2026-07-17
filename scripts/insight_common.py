#!/usr/bin/env python3
"""Common helpers for collecting, deduping, and publishing product leads."""

import datetime as dt
import hashlib
import html
import json
import os
import re
import unicodedata
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from insight_config import CATEGORY_KEYWORDS, SOURCE_QUALITY_BY_SOURCE, SOURCE_TYPES

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
INSIGHT_DIR = ROOT / "insight"
LOCAL_TZ = ZoneInfo("Asia/Shanghai")

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "spm",
    "fbclid",
    "gclid",
    "xsec_token",
    "xsec_source",
    "share_from_user_hidden",
    "share_id",
    "share_sign",
    "timestamp",
}

DIRECT_LINK_QUERY_KEYS = {
    "q",
    "query",
    "keyword",
    "keywords",
    "search",
    "s",
    "wd",
    "k",
}

DIRECT_LINK_BLOCKED_SEGMENTS = {
    "search",
    "tag",
    "tags",
    "category",
    "categories",
    "collection",
    "collections",
    "topic",
    "topics",
    "explore",
    "discover",
    "feed",
    "archive",
    "page",
    "pages",
    "market",
}

SOURCE_PREFIX_RE = re.compile(
    r"^(pinterest|behance|instagram|dezeen|design milk|yanko design|core77|designboom|trendhunter|the dieline|packaging of the world|pentawards|小红书|抖音|red dot|good design award|if设计奖|dia 中国设计智造大奖|a' design award|站酷|普象网|设计癖|数英)\s*[·:\-|]\s*",
    re.IGNORECASE,
)

NOISE_WORDS = [
    "爆款",
    "同款",
    "推荐",
    "新品",
    "设计",
    "创意",
    "2024",
    "2025",
    "2026",
    "best",
    "new",
    "design",
    "product",
    "review",
    "award",
    "winner",
    "official",
    "site",
    "官网",
    "获奖",
    "案例",
]
WEAK_FINGERPRINT_TOKENS = {
    "a", "an", "and", "the", "for", "with", "from", "official", "site",
    "design", "product", "award", "winner", "project", "case", "new",
    "创意", "设计", "产品", "新品", "官网", "获奖", "案例", "灵感",
}


def ensure_dirs():
    for path in [DATA_DIR, RAW_DIR, PROCESSED_DIR, INSIGHT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_env(path=None):
    """Load simple KEY=VALUE pairs from .env without overriding existing env."""
    env_path = Path(path) if path else ROOT / ".env"
    if not env_path.exists():
        return {}
    loaded = {}
    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
                loaded[key] = value
    return loaded


def today():
    return dt.datetime.now(LOCAL_TZ).date().isoformat()


def now_iso():
    return dt.datetime.now(LOCAL_TZ).replace(microsecond=0).isoformat()


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def strip_html(value):
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def clean_title(title):
    title = strip_html(title)
    title = SOURCE_PREFIX_RE.sub("", title).strip()
    return title or "未命名产品"


def canonical_url(url):
    if not url:
        return ""
    url = html.unescape(str(url)).strip()
    parts = urlsplit(url)
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    path = re.sub(r"/+$", "", parts.path)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=False)
        if key not in TRACKING_PARAMS and not key.startswith("utm_")
    ]
    return urlunsplit((scheme, netloc, path, urlencode(query, doseq=True), ""))


def clean_direct_product_url(url):
    canonical = canonical_url(url)
    if not canonical:
        return ""

    parts = urlsplit(canonical)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return ""

    host = parts.netloc.lower()
    path = parts.path.lower().strip("/")
    query = dict(parse_qsl(parts.query, keep_blank_values=False))
    segments = [segment for segment in path.split("/") if segment]

    if any(host.endswith(domain) for domain in ["duckduckgo.com", "google.com", "bing.com", "baidu.com"]):
        return ""

    if any(key.lower() in DIRECT_LINK_QUERY_KEYS for key in query):
        return ""

    if segments and segments[-1] in DIRECT_LINK_BLOCKED_SEGMENTS:
        return ""

    if any(segment in DIRECT_LINK_BLOCKED_SEGMENTS for segment in segments[:2]) and len(segments) <= 3:
        return ""

    if host.endswith("etsy.com"):
        if len(segments) < 2 or segments[0] != "listing" or not segments[1].isdigit():
            return ""

    if host.endswith("producthunt.com"):
        if segments[:1] not in (["posts"], ["products"]):
            return ""

    if host.endswith("threadless.com") and segments[:1] == ["search"]:
        return ""

    if host.endswith("kickstarter.com") and segments[:1] == ["projects"] and len(segments) > 3:
        if segments[3] in {"comments", "community", "description", "faqs", "posts", "updates"}:
            original_segments = [segment for segment in parts.path.strip("/").split("/") if segment]
            parts = parts._replace(path="/" + "/".join(original_segments[:3]), query="")
            return urlunsplit(parts)

    return canonical


def stable_hash(value, length=12):
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]


def normalize_text(value):
    value = clean_title(value).lower()
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"https?://\S+", " ", value)
    for word in NOISE_WORDS:
        value = value.replace(word.lower(), " ")
    value = re.sub(r"[^\w\u4e00-\u9fff]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def content_tokens(*values):
    normalized = normalize_text(" ".join(str(value or "") for value in values))
    raw_tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", normalized)
    tokens = []
    for token in raw_tokens:
        if token in WEAK_FINGERPRINT_TOKENS:
            continue
        if len(token) < 2:
            continue
        tokens.append(token)
    return tokens


def content_fingerprint(item):
    """Return a category-aware fingerprint for cross-date duplicate suppression."""
    title = item.get("title") or ""
    reason = item.get("reason") or item.get("summary") or ""
    creator = item.get("creator") or item.get("source_primary") or ""
    category = item.get("category") or guess_category(title, reason) or "未分类"
    tokens = content_tokens(title, creator)
    if len(tokens) < 2:
        tokens = content_tokens(title, reason, creator)
    compact = "".join(tokens[:8]) if tokens else normalize_text(title)
    if not compact:
        compact = item.get("url") or title
    return f"{category}:{stable_hash(compact, 16)}"


def guess_category(title, text=""):
    haystack = normalize_text(f"{title} {text}")
    best_category = None
    best_hits = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = sum(1 for word in keywords if word.lower() in haystack)
        if hits > best_hits:
            best_category = category
            best_hits = hits
    return best_category


def product_key(item):
    title = item.get("title") or ""
    category = item.get("category") or guess_category(title, item.get("reason", ""))
    tokens = content_tokens(title)
    compact = "".join(tokens[:8]) if tokens else stable_hash(title)
    return f"{category or '未分类'}:{stable_hash(compact, 16)}"


def source_type(source):
    return SOURCE_TYPES.get(source or "", "public_web")


def source_quality(source="", source_type_value="", source_group="", quality_tier=""):
    direct = (quality_tier or "").strip().lower()
    if direct in {"premium", "standard", "weak"}:
        return direct
    group = (source_group or "").strip().lower()
    if "weak" in group:
        return "weak"
    if "strong" in group:
        return "standard"
    by_name = SOURCE_QUALITY_BY_SOURCE.get(source or "")
    if by_name:
        return by_name
    if source_type_value == "verified_official":
        return "premium"
    if source_type_value in {"editorial_source", "packaging_source"}:
        return "premium"
    if source_type_value in {"design_community", "social_signal", "market_reference"}:
        return "standard"
    if source_type_value == "trend_source":
        return "weak"
    return "standard"


def infer_price_power(item):
    """Return a rough price gate status without inventing exact pricing."""
    text = f"{item.get('title', '')} {item.get('reason', '')} {' '.join(item.get('tags', []) or [])}".lower()
    if re.search(r"(¥|￥|rmb|元)\s*([3-9]\d|[1-9]\d{2,})", text):
        return "likely_over_35"
    if any(word in text for word in ["premium", "高端", "质感", "套装", "礼盒", "award", "获奖"]):
        return "likely_over_35"
    if any(word in text for word in ["贴纸", "便签", "小挂件", "sticker"]):
        return "risk_under_35"
    return "unknown"


def make_source_record(item):
    url = canonical_url(item.get("url", ""))
    source = item.get("source") or item.get("platform") or "未知来源"
    source_type_value = item.get("source_type") or source_type(source)
    return {
        "source": source,
        "source_type": source_type_value,
        "source_group": item.get("source_group", ""),
        "quality_tier": item.get("quality_tier", ""),
        "source_quality": source_quality(
            source=source,
            source_type_value=source_type_value,
            source_group=item.get("source_group", ""),
            quality_tier=item.get("quality_tier", ""),
        ),
        "url": url,
        "title": clean_title(item.get("title", "")),
        "image": item.get("image", ""),
        "likes": item.get("likes", 0) or 0,
        "collected_at": item.get("collected_at") or item.get("added") or today(),
    }


def lead_from_legacy(item):
    title = clean_title(item.get("title", ""))
    reason = strip_html(item.get("reason", ""))
    category = item.get("category") or guess_category(title, reason) or "未分类"
    url = canonical_url(item.get("url", ""))
    return {
        "id": item.get("id") or stable_hash(url or f"{title}|{category}"),
        "title": title,
        "reason": reason,
        "source": item.get("source") or "未知来源",
        "category": category,
        "creator": item.get("creator", ""),
        "score": item.get("score", 0),
        "likes": item.get("likes", 0) or 0,
        "url": url,
        "image": item.get("image", ""),
        "tags": item.get("tags", []) or [],
        "added": item.get("added") or today(),
        "source_group": item.get("source_group", ""),
        "quality_tier": item.get("quality_tier", ""),
        "_score_total": item.get("_score_total"),
        "_deepseek": item.get("_deepseek"),
        "_scores": item.get("_scores"),
    }


def merge_unique_sources(existing, new_source):
    if not new_source.get("url"):
        source_id = f"{new_source.get('source')}|{new_source.get('title')}"
    else:
        source_id = new_source["url"]
    for source in existing:
        current_id = source.get("url") or f"{source.get('source')}|{source.get('title')}"
        if current_id == source_id:
            return
    existing.append(new_source)
