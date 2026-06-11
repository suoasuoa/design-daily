#!/usr/bin/env python3
"""Top up same-day public social picks before filling the daily 30."""

import argparse
import subprocess
import sys

from collect_search import collect, merge_daily_leads
from insight_common import DATA_DIR, RAW_DIR, ensure_dirs, load_json, today, write_json


SOCIAL_SOURCES = {"抖音", "小红书", "Instagram"}
SOCIAL_SOURCE_TYPE = "social_signal"


def run(cmd):
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def is_target_social_product(item, current_day):
    if item.get("first_seen") != current_day:
        return False
    for source in item.get("sources", []):
        if source.get("source") in SOCIAL_SOURCES and source.get("source_type") == SOCIAL_SOURCE_TYPE:
            return True
    return False


def social_count():
    products = load_json(DATA_DIR / "products.json", [])
    current_day = today()
    return sum(1 for item in products if is_target_social_product(item, current_day))


def social_jobs():
    payload = load_json(DATA_DIR / "search_jobs.json", {})
    jobs = [
        job
        for job in payload.get("jobs", [])
        if job.get("source_group") == "social_public_index"
    ]
    return jobs


def collect_social_batch(jobs, args, offset):
    leads = collect(
        jobs,
        limit_jobs=args.batch_jobs,
        per_job=args.per_job,
        sleep=args.sleep,
        offset=offset,
        workers=args.workers,
    )
    path = RAW_DIR / f"social-public-{today()}.json"
    merged, existing_count, added_count = merge_daily_leads(path, leads)
    write_json(path, merged)
    print(
        f"social_minimum saved={path} fetched={len(leads)} "
        f"existing={existing_count} added={added_count} total={len(merged)}",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=10, help="Required same-day Douyin/XHS/Instagram accepted products.")
    parser.add_argument("--batch-jobs", type=int, default=120, help="Social search jobs per top-up pass.")
    parser.add_argument("--per-job", type=int, default=8, help="Search results per job.")
    parser.add_argument("--max-passes", type=int, default=4, help="Maximum social top-up passes.")
    parser.add_argument("--review-batch-size", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    ensure_dirs()
    if args.target <= 0:
        print("social_minimum skipped target=0", flush=True)
        return

    jobs = social_jobs()
    if not jobs:
        raise SystemExit("No social_public_index jobs found. Run scripts/search_jobs.py first.")

    count = social_count()
    print(f"social_minimum initial={count} target={args.target} jobs={len(jobs)}", flush=True)
    if count >= args.target:
        return

    for index in range(args.max_passes):
        offset = (index * args.batch_jobs) % len(jobs)
        collect_social_batch(jobs, args, offset)
        run([sys.executable, "scripts/dedupe.py"])
        run([sys.executable, "scripts/review_categories.py", "--batch-size", str(args.review_batch_size)])

        count = social_count()
        print(f"social_minimum pass={index + 1} count={count} target={args.target}", flush=True)
        if count >= args.target:
            return

    print(
        f"social_minimum warning: only {count}/{args.target} same-day accepted "
        "Douyin/XHS/Instagram products after top-up. No fake items were added.",
        flush=True,
    )


if __name__ == "__main__":
    main()
