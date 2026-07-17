#!/usr/bin/env python3
"""Top up same-day product discovery until the daily group reaches a target size."""

import argparse
import subprocess
import sys

from build_site import build_daily_groups, record, sorted_products
from insight_common import DATA_DIR, load_json, today


def run(cmd):
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def today_count():
    products = load_json(DATA_DIR / "products.json", [])
    current_day = today()
    items = [record(item) for item in sorted_products(products)]
    groups = build_daily_groups(items, per_day=30, max_days=1)
    for group in groups:
        if group.get("date") == current_day:
            return int(group.get("actual_count") or len(group.get("items") or []))
    return 0


def job_count():
    payload = load_json(DATA_DIR / "search_jobs.json", {})
    return len(payload.get("jobs", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=30, help="Required same-day accepted products.")
    parser.add_argument("--batch-jobs", type=int, default=180, help="Deprecated fixed-search compatibility option.")
    parser.add_argument("--per-job", type=int, default=6, help="Search results per DeepSeek-planned query.")
    parser.add_argument("--max-passes", type=int, default=3, help="Maximum DeepSeek agent top-up rounds.")
    parser.add_argument("--review-batch-size", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--curated-limit", type=int, default=320)
    parser.add_argument("--shopify-pages", type=int, default=6)
    parser.add_argument("--agent-queries", type=int, default=60)
    parser.add_argument("--agent-pages", type=int, default=280)
    parser.add_argument("--agent-screen-workers", type=int, default=6)
    args = parser.parse_args()

    total_jobs = job_count()
    if total_jobs <= 0:
        raise SystemExit("No search jobs found. Run scripts/search_jobs.py first.")

    count = today_count()
    print(f"daily_minimum initial={count} target={args.target} jobs={total_jobs}", flush=True)
    if count >= args.target:
        return

    for index in range(args.max_passes):
        run(
            [
                sys.executable,
                "scripts/deepseek_search_agent.py",
                "--target",
                str(args.target),
                "--round",
                str(index + 1),
                "--query-count",
                str(args.agent_queries),
                "--per-query",
                str(args.per_job),
                "--max-pages",
                str(args.agent_pages),
                "--search-workers",
                str(args.workers),
                "--screen-workers",
                str(args.agent_screen_workers),
            ]
        )
        run(
            [
                sys.executable,
                "scripts/collect_curated_pages.py",
                "--limit",
                str(args.curated_limit),
                "--shopify-pages",
                str(args.shopify_pages),
                "--page-offset",
                str(index * args.shopify_pages),
            ]
        )
        run([sys.executable, "scripts/dedupe.py"])
        run([sys.executable, "scripts/review_categories.py", "--batch-size", str(args.review_batch_size)])

        count = today_count()
        print(f"daily_minimum pass={index + 1} count={count} target={args.target}", flush=True)
        if count >= args.target:
            return

    print(
        f"daily_minimum warning: only {count}/{args.target} same-day accepted products after top-up. "
        "The dashboard will still publish the best available new products.",
        flush=True,
    )


if __name__ == "__main__":
    main()
