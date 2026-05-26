#!/usr/bin/env python3
"""Collect public RSS product/design leads into data/raw."""

import argparse
import datetime as dt
import re
import ssl
import urllib.request
from xml.etree import ElementTree

from insight_common import RAW_DIR, ensure_dirs, guess_category, stable_hash, strip_html, write_json
from insight_config import RSS_FEEDS

CTX = ssl._create_unverified_context()


def child_text(node, names):
    for name in names:
        child = node.find(name)
        if child is not None and child.text:
            return child.text.strip()
    return ""


def child_image(node, description=""):
    for child in list(node):
        tag = child.tag.lower()
        if tag.endswith("thumbnail") or tag.endswith("content"):
            url = child.attrib.get("url", "")
            if url and (url.startswith("http://") or url.startswith("https://")):
                return url
        if tag.endswith("enclosure"):
            url = child.attrib.get("url", "")
            media_type = child.attrib.get("type", "")
            if url and media_type.startswith("image/"):
                return url
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', description or "", re.IGNORECASE)
    if match:
        image = match.group(1).strip()
        if image.startswith("//"):
            image = "https:" + image
        if image.startswith(("http://", "https://")):
            return image
    return ""


def collect_feed(feed, timeout=30):
    req = urllib.request.Request(feed["url"], headers={"User-Agent": "DesignDailyInsight/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        raw = resp.read()
    text = raw.decode("utf-8", errors="replace")
    start = text.find("<")
    if start > 0:
        text = text[start:]
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    root = ElementTree.fromstring(text)
    items = []
    for node in root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = child_text(node, ["title", "{http://www.w3.org/2005/Atom}title"])
        link = child_text(node, ["link", "{http://www.w3.org/2005/Atom}link"])
        if not link:
            link_node = node.find("{http://www.w3.org/2005/Atom}link")
            if link_node is not None:
                link = link_node.attrib.get("href", "")
        description = child_text(
            node,
            [
                "description",
                "summary",
                "{http://www.w3.org/2005/Atom}summary",
                "{http://purl.org/rss/1.0/modules/content/}encoded",
            ],
        )
        image = child_image(node, description)
        description = strip_html(description)
        if not title or not link:
            continue
        category = guess_category(title, description)
        if not category:
            continue
        items.append(
            {
                "id": stable_hash(f"{feed['source']}|{link}"),
                "title": title,
                "reason": description[:240],
                "source": feed["source"],
                "category": category,
                "creator": feed["source"],
                "score": 0,
                "likes": 0,
                "url": link,
                "image": image,
                "tags": [category, feed["source"], "公开来源"],
                "added": dt.date.today().isoformat(),
                "collected_at": dt.date.today().isoformat(),
            }
        )
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Maximum items to save.")
    args = parser.parse_args()

    ensure_dirs()
    collected = []
    for feed in RSS_FEEDS:
        try:
            items = collect_feed(feed)
            print(f"{feed['source']}: {len(items)}")
            collected.extend(items)
        except Exception as exc:
            print(f"{feed['source']}: failed ({exc})")

    if args.limit:
        collected = collected[: args.limit]
    path = RAW_DIR / f"public-{dt.date.today().isoformat()}.json"
    write_json(path, collected)
    print(f"saved={path} items={len(collected)}")


if __name__ == "__main__":
    main()
