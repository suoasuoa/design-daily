#!/usr/bin/env python3
"""Sync anonymous product feedback from Supabase into the local data pool."""

import json
import os
import urllib.parse
import urllib.request

from insight_common import DATA_DIR, ensure_dirs, load_json, write_json


PAGE_SIZE = 1000


def merge_events(existing, incoming):
    merged = {}
    for event in [*existing, *incoming]:
        event_id = str(event.get("event_id") or "").strip()
        if event_id:
            merged[event_id] = event
    return sorted(
        merged.values(),
        key=lambda event: (
            str(event.get("created_at") or ""),
            str(event.get("event_id") or ""),
        ),
    )


def fetch_events(base_url, api_key, workspace="design-daily"):
    endpoint = (
        f"{base_url.rstrip('/')}/rest/v1/feedback_events?"
        + urllib.parse.urlencode(
            {
                "select": (
                    "event_id,workspace,actor_id,product_id,action,reason,"
                    "context,item_snapshot,created_at"
                ),
                "workspace": f"eq.{workspace}",
                "order": "created_at.asc,event_id.asc",
            }
        )
    )
    events = []
    offset = 0
    while True:
        request = urllib.request.Request(
            endpoint,
            headers={
                "apikey": api_key,
                "Range": f"{offset}-{offset + PAGE_SIZE - 1}",
                "Range-Unit": "items",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            page = json.loads(response.read().decode("utf-8"))
        if not isinstance(page, list):
            raise ValueError("Supabase feedback response must be a list")
        events.extend(
            event
            for event in page
            if not (event.get("context") or {}).get("system_test")
        )
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return events


def main():
    ensure_dirs()
    output = DATA_DIR / "feedback_events.json"
    base_url = os.environ.get("SUPABASE_URL", "").strip()
    api_key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if not base_url or not api_key:
        print("feedback_sync=skipped reason=missing_supabase_secret")
        return

    existing = load_json(output, [])
    try:
        incoming = fetch_events(base_url, api_key)
    except Exception as exc:
        print(f"feedback_sync=warning reason={exc}")
        return

    merged = merge_events(existing, incoming)
    write_json(output, merged)
    print(
        f"feedback_sync=done remote:{len(incoming)} "
        f"existing:{len(existing)} merged:{len(merged)}"
    )


if __name__ == "__main__":
    main()
