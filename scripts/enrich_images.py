#!/usr/bin/env python3
"""Enrich product records with Open Graph images from their source URLs."""

import argparse
from html.parser import HTMLParser
import ssl
import urllib.parse
import urllib.request

from insight_common import DATA_DIR, load_json, now_iso, write_json


SSL_CONTEXT = ssl._create_unverified_context()


class MetaImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        attrs = {key.lower(): value for key, value in attrs if key}
        prop = (attrs.get("property") or attrs.get("name") or "").lower()
        content = attrs.get("content", "")
        if prop in {"og:image", "og:image:url", "twitter:image", "twitter:image:src"} and content:
            self.images.append(content.strip())


def source_url(item):
    if item.get("url"):
        return item["url"]
    for source in item.get("sources") or []:
        if source.get("url"):
            return source["url"]
    return ""


def absolute_url(base, value):
    if not value:
        return ""
    return urllib.parse.urljoin(base, value)


def fetch_image(url, timeout=18):
    if not url or not url.startswith(("http://", "https://")):
        return ""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 DesignDailyInsight/1.0",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
        ctype = resp.headers.get("content-type", "")
        if "text/html" not in ctype and "application/xhtml" not in ctype:
            return ""
        html = resp.read(400_000).decode("utf-8", errors="replace")
    parser = MetaImageParser()
    parser.feed(html)
    for image in parser.images:
        image = absolute_url(url, image)
        if image.startswith(("http://", "https://")):
            return image
    return ""


def enrich(products, limit=60):
    changed = 0
    checked = 0
    candidates = sorted(
        [item for item in products if not item.get("image") and source_url(item)],
        key=lambda item: (int(item.get("selection_score") or 0), item.get("last_seen") or ""),
        reverse=True,
    )
    for item in candidates:
        if checked >= limit:
            break
        checked += 1
        url = source_url(item)
        try:
            image = fetch_image(url)
        except Exception as exc:
            print(f"image_skip={item.get('title')} ({exc})")
            continue
        if image:
            item["image"] = image
            item["image_enriched_at"] = now_iso()
            changed += 1
            print(f"image_ok={item.get('title')}")
    return checked, changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()

    products = load_json(DATA_DIR / "products.json", [])
    checked, changed = enrich(products, args.limit)
    write_json(DATA_DIR / "products.json", products)
    print(f"image_enrich checked={checked} changed={changed}")


if __name__ == "__main__":
    main()
