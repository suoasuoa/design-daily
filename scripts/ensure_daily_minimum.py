#!/usr/bin/env python3
"""Top up same-day product discovery until the daily group reaches a target size."""

import argparse
import subprocess
import sys

from build_site import build_daily_groups, record, sorted_products
from insight_common import DATA_DIR, load_daily_history, load_json, today


def run(cmd):
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def today_count(target=40):
    products = load_json(DATA_DIR / "products.json", [])
    current_day = today()
    items = [record(item) for item in sorted_products(products)]
    groups = build_daily_groups(
        items,
        per_day=max(40, target),
        max_days=1,
        previous_groups=load_daily_history(),
        current_date=current_day,
    )
    for group in groups:
        if group.get("date") == current_day:
            return int(group.get("actual_count") or len(group.get("items") or []))
    return 0


def job_count():
    payload = load_json(DATA_DIR / "search_jobs.json", {})
    return len(payload.get("jobs", []))


def agent_round_offset():
    """Continue today's search rounds across separate scheduled workflow runs."""
    payload = load_json(
        DATA_DIR / "reports" / f"deepseek-search-agent-{today()}.json",
        {},
    )
    return len(payload.get("rounds", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=40, help="Required same-day accepted products.")
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
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Search once even when 40 items exist so stronger candidates can replace the bottom of today's group.",
    )
    args = parser.parse_args()

    total_jobs = job_count()
    if total_jobs <= 0:
        raise SystemExit("No search jobs found. Run scripts/search_jobs.py first.")

    count = today_count(args.target)
    print(f"daily_minimum initial={count} target={args.target} jobs={total_jobs}", flush=True)
    if count >= args.target and not args.refresh:
        return

    # Use already-reviewed, never-published candidates before spending time and
    # API calls on another search round. Search remains the fallback when the
    # reviewed reserve cannot satisfy the target.
    if not args.refresh:
        run(
            [
                sys.executable,
                "scripts/promote_reviewed_backlog.py",
                "--target",
                str(args.target),
            ]
        )
        count = today_count(args.target)
        print(f"daily_minimum reserve_count={count} target={args.target}", flush=True)
        if count >= args.target:
            return

    round_offset = agent_round_offset()
    for index in range(args.max_passes):
        # Keep a broad candidate pool even when the display deficit is small.
        # The review gate decides quality; the remaining gap only decides
        # whether another search round is necessary.
        gap = max(1, args.target - count)
        # More generic fallback queries reduce quality after a point. Keep each
        # round broad but bounded, and spend the remaining overnight budget on
        # rotating to a new round/source offset instead.
        pass_queries = min(
            240,
            args.agent_queries + index * max(20, args.agent_queries // 2),
        )
        pass_pages = min(
            1400,
            args.agent_pages + index * max(80, args.agent_pages // 2),
        )
        round_index = round_offset + index
        print(
            f"daily_minimum broad_search pass={index + 1} round={round_index + 1} gap={gap} "
            f"queries={pass_queries} pages={pass_pages}",
            flush=True,
        )
        run(
            [
                sys.executable,
                "scripts/deepseek_search_agent.py",
                "--target",
                str(args.target),
                "--round",
                str(round_index),
                "--query-count",
                str(pass_queries),
                "--per-query",
                str(args.per_job),
                "--max-pages",
                str(pass_pages),
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
                str(round_index * args.shopify_pages),
            ]
        )
        run([sys.executable, "scripts/dedupe.py"])
        run([sys.executable, "scripts/review_categories.py", "--batch-size", str(args.review_batch_size)])

        count = today_count(args.target)
        print(f"daily_minimum pass={index + 1} count={count} target={args.target}", flush=True)
        if count >= args.target:
            return

    run(
        [
            sys.executable,
            "scripts/promote_reviewed_backlog.py",
            "--target",
            str(args.target),
        ]
    )
    count = today_count(args.target)
    print(f"daily_minimum backlog_count={count} target={args.target}", flush=True)
    if count < args.target:
        print(
            f"daily_minimum incomplete: {count}/{args.target} accepted products; "
            "saving progress for the next scheduled top-up",
            flush=True,
        )


if __name__ == "__main__":
    main()
