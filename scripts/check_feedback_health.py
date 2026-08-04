#!/usr/bin/env python3
"""Check that the Supabase feedback store is reachable and summarize activity."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


WORKSPACE = "design-daily"


def request_json(base_url, api_key, params, *, count=False, attempts=6):
    endpoint = (
        f"{base_url.rstrip('/')}/rest/v1/feedback_events?"
        + urllib.parse.urlencode(params)
    )
    headers = {"apikey": api_key}
    if count:
        headers.update({"Prefer": "count=exact", "Range": "0-0", "Range-Unit": "items"})
    request = urllib.request.Request(endpoint, headers=headers)
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
                content_range = response.headers.get("Content-Range", "")
            return body, content_range
        except urllib.error.HTTPError as exc:
            if exc.code not in {502, 503, 504, 521} or attempt == attempts:
                error_body = exc.read().decode("utf-8", errors="replace")[:500]
                print(
                    f"feedback_health=http_error status={exc.code} "
                    f"body={error_body}"
                )
                raise
            print(f"feedback_health=retry attempt={attempt} status={exc.code}")
        except urllib.error.URLError as exc:
            if attempt == attempts:
                raise
            print(f"feedback_health=retry attempt={attempt} reason={exc.reason}")
        time.sleep(20)
    raise RuntimeError("Supabase feedback health retry loop exhausted")


def count_from_range(content_range):
    if "/" not in content_range:
        return 0
    total = content_range.rsplit("/", 1)[-1]
    return int(total) if total.isdigit() else 0


def action_count(base_url, api_key, action):
    _, content_range = request_json(
        base_url,
        api_key,
        {
            "select": "event_id",
            "workspace": f"eq.{WORKSPACE}",
            "action": f"eq.{action}",
            "limit": "1",
        },
        count=True,
    )
    return count_from_range(content_range)


def main():
    base_url = os.environ.get("SUPABASE_URL", "").strip()
    api_key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if not base_url or not api_key:
        raise SystemExit("feedback_health=failed reason=missing_supabase_secret")

    key_type = (
        "secret" if api_key.startswith("sb_secret_")
        else "publishable" if api_key.startswith("sb_publishable_")
        else "legacy_or_unknown"
    )
    print(f"feedback_health=credentials key_type={key_type} key_length={len(api_key)}")

    latest, _ = request_json(
        base_url,
        api_key,
        {
            "select": "event_id,action,created_at",
            "workspace": f"eq.{WORKSPACE}",
            "order": "created_at.desc",
            "limit": "1",
        },
    )
    likes = action_count(base_url, api_key, "like")
    passes = action_count(base_url, api_key, "pass")
    latest_at = latest[0].get("created_at", "none") if latest else "none"
    print(
        "feedback_health=ok "
        f"likes={likes} passes={passes} latest_at={latest_at}"
    )


if __name__ == "__main__":
    main()
