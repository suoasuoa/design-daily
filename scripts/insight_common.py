#!/usr/bin/env python3
"""Common helpers for collecting, deduping, and publishing product leads."""

import datetime as dt
from difflib import SequenceMatcher
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
SEMANTIC_TITLE_NOISE = {
    "red", "dot", "good", "if", "yanko", "dieline", "uncrate", "core77",
    "designboom", "behance", "adobe", "inc", "pinterest", "facebook",
    "susifacebook", "search", "zcool", "站酷", "design", "award", "project",
    "the", "a", "an", "for", "of", "and", "with", "from", "this", "to",
    "in", "by", "home",
}
PRODUCT_IDENTITY_NOISE = SEMANTIC_TITLE_NOISE | {
    "regular", "phone", "phones", "smartphone", "iphone", "case", "cases",
    "cover", "covers", "stand", "stands", "kickstand", "product", "products",
    "tool", "tools", "set", "sets", "series", "system", "edition", "model",
    "puts", "entire", "into", "your", "pocket", "offer", "offers", "ultimate",
    "hands", "free", "ergonomics", "adds", "provides", "solution", "debut",
    "debuts", "secret", "hiding", "running", "shoes", "content", "creator",
    "dream", "apple", "think", "powered", "magnetic", "magsafe", "rotating",
    "spin", "degree", "slim", "durable", "compatibility", "built", "integrated",
    "portable", "smart", "all", "one", "dead", "these", "was", "its",
    "power", "bank", "battery", "water", "bottle", "cup", "cups", "mug",
    "modular", "desk", "desktop", "lamp", "light", "lighting", "wireless",
    "world", "first", "best", "fastest", "thinnest", "most", "smallest",
    "jacket", "travel", "measuring", "cutting", "board", "visual", "reviewed",
    "review", "kickstarter", "indiegogo", "dia", "intelligence", "more", "much",
    "that", "with", "than", "just", "made", "makes", "meet", "gets", "got",
    "charger", "mah", "in1", "led", "midautumn", "festival", "campaign", "images",
    "are", "is", "has", "have", "had", "were", "will", "can", "could", "should",
}
PRODUCT_FAMILY_CONCEPTS = {
    "stand": ("ostand", "kickstand", "phone stand", "rotating stand", "支架", "支撑", "支点"),
}
PRODUCT_FAMILY_BRANDS = {"手机壳": {"torras"}}


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


def load_daily_history():
    """Load the last public daily snapshots, never an in-flight pool rewrite."""
    for path in (INSIGHT_DIR / "data.raw.json", DATA_DIR / "published.json"):
        payload = load_json(path, {})
        groups = payload.get("daily_groups") if isinstance(payload, dict) else None
        if groups:
            return groups
    return []


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


def semantic_title_tokens(value):
    """Normalize product titles for conservative same-category near-duplicate checks."""
    value = unicodedata.normalize("NFKC", value or "").lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value)
    tokens = []
    for token in value.split():
        if token in SEMANTIC_TITLE_NOISE:
            continue
        if token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("ies") and len(token) > 5:
            token = token[:-3] + "y"
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        if token and token not in SEMANTIC_TITLE_NOISE:
            tokens.append(token)
    return tokens


def semantic_title_duplicate(left, right):
    left_tokens = semantic_title_tokens(left)
    right_tokens = semantic_title_tokens(right)
    left_set = set(left_tokens)
    right_set = set(right_tokens)
    if len(left_set) >= 2 and len(right_set) >= 2:
        overlap = len(left_set & right_set) / len(left_set | right_set)
        if overlap >= 0.60:
            return True
    left_text = " ".join(left_tokens)
    right_text = " ".join(right_tokens)
    if len(left_text) < 8 or len(right_text) < 8:
        return False
    length_ratio = min(len(left_text), len(right_text)) / max(len(left_text), len(right_text))
    return length_ratio >= 0.72 and SequenceMatcher(None, left_text, right_text).ratio() >= 0.90


def product_identity_text(item):
    """Return the short, product-specific text before scraped article evidence."""
    title = clean_title(item.get("title") or "")
    summary = str(item.get("reason") or item.get("summary") or item.get("ai_reason") or "")
    summary = re.split(r"页面证据|page evidence", summary, maxsplit=1, flags=re.IGNORECASE)[0]
    return f"{title} {summary[:320]}".strip()


def product_identity_tokens(item):
    """Extract conservative brand/model tokens used for cross-source identity matching."""
    value = unicodedata.normalize("NFKC", product_identity_text(item))
    raw_tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", value)
    tokens = []
    for raw in raw_tokens:
        token = raw.lower().replace("-", "")
        if token in PRODUCT_IDENTITY_NOISE or len(token) < 3:
            continue
        if token not in tokens:
            tokens.append(token)
    return tokens[:8]


def product_brand_token(item):
    """Extract a likely brand from the headline, then fall back to explicit caps."""
    title = unicodedata.normalize("NFKC", clean_title(item.get("title") or ""))
    title_tokens = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", title):
        token = raw.lower().replace("-", "")
        if token not in PRODUCT_IDENTITY_NOISE:
            title_tokens.append((raw, token))
    if title_tokens:
        return title_tokens[0][1]

    value = unicodedata.normalize("NFKC", product_identity_text(item))
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", value):
        token = raw.lower().replace("-", "")
        if raw.isupper() and token not in PRODUCT_IDENTITY_NOISE:
            return token
    return ""


def product_identity_parts(item):
    """Return normalized and original brand/model tokens from the short product text."""
    value = unicodedata.normalize("NFKC", product_identity_text(item))
    candidates = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", value):
        token = raw.lower().replace("-", "")
        if token in PRODUCT_IDENTITY_NOISE:
            continue
        candidates.append((token, raw))
    brand = product_brand_token(item)
    model = next(((token, raw) for token, raw in candidates if token != brand), ("", ""))
    brand_raw = next((raw for token, raw in candidates if token == brand), "")
    return brand, brand_raw, model[0], model[1]


def is_stylized_model_token(raw):
    if not raw:
        return False
    has_digit = any(char.isdigit() for char in raw)
    has_internal_cap = any(char.isupper() for char in raw[1:]) and not raw.isupper()
    return has_digit or has_internal_cap or raw.isupper() or len(raw) >= 7


def product_identity_keys(item):
    """Build stable keys for the same named product or tightly scoped product family."""
    category = item.get("category") or guess_category(
        item.get("title") or "",
        item.get("reason") or item.get("summary") or "",
    ) or "未分类"
    keys = set()
    brand, brand_raw, model, model_raw = product_identity_parts(item)
    brand_is_stylized = bool(brand_raw) and not brand_raw.isupper() and is_stylized_model_token(brand_raw)
    if brand and model and (brand_is_stylized or is_stylized_model_token(model_raw)):
        keys.add(f"identity:{category}:{brand}:{model}")

    if brand in PRODUCT_FAMILY_BRANDS.get(category, set()):
        text = product_identity_text(item).lower()
        if brand:
            for concept, markers in PRODUCT_FAMILY_CONCEPTS.items():
                if any(marker in text for marker in markers):
                    keys.add(f"family:{category}:{brand}:{concept}")
    return keys


def semantic_product_duplicate(left, right):
    """Detect the same product even when different sites use different headlines."""
    left_category = left.get("category") or ""
    right_category = right.get("category") or ""
    if left_category and right_category and left_category != right_category:
        return False
    if semantic_title_duplicate(left.get("title") or "", right.get("title") or ""):
        return True
    return bool(product_identity_keys(left) & product_identity_keys(right))


def is_ordinary_laptop_stand(item, category=None):
    """Block the saturated laptop-stand direction from creative desk picks."""
    category = category or item.get("category") or ""
    if category != "创意桌搭":
        return False
    review = item.get("category_review") or {}
    text = " ".join(
        str(value or "")
        for value in (
            item.get("title"),
            item.get("summary"),
            item.get("reason"),
            review.get("reason"),
        )
    ).lower()
    laptop_terms = ("laptop", "notebook computer", "macbook", "笔记本电脑", "笔记本")
    stand_terms = ("stand", "riser", "support", "prop up", "支架", "托架", "增高架", "支撑架")
    return any(term in text for term in laptop_terms) and any(term in text for term in stand_terms)


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
