#!/usr/bin/env python3
"""Top up same-day product discovery until the daily group reaches a target size."""

import argparse
import subprocess
import sys

from insight_common import DATA_DIR, load_json, today


def run(cmd):
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def today_count():
    products = load_json(DATA_DIR / "products.json", [])
    current_day = today()
    return sum(1 for item in products if item.get("first_seen") == current_day)


def job_count():
    payload = load_json(DATA_DIR / "search_jobs.json", {})
    return len(payload.get("jobs", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=30, help="Required same-day accepted products.")
    parser.add_argument("--batch-jobs", type=int, default=260, help="Search jobs per top-up pass.")
    parser.add_argument("--per-job", type=int, default=8, help="Search results per job.")
    parser.add_argument("--max-passes", type=int, default=4, help="Maximum top-up passes.")
    parser.add_argument("--review-batch-size", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    total_jobs = job_count()
    if total_jobs <= 0:
        raise SystemExit("No search jobs found. Run scripts/search_jobs.py first.")

    count = today_count()
    print(f"daily_minimum initial={count} target={args.target} jobs={total_jobs}", flush=True)
    if count >= args.target:
        return

    for index in range(args.max_passes):
        offset = ((index + 1) * args.batch_jobs) % total_jobs
        run(
            [
                sys.executable,
                "scripts/collect_search.py",
                "--limit-jobs",
                str(args.batch_jobs),
                "--per-job",
                str(args.per_job),
                "--offset",
                str(offset),
                "--sleep",
                str(args.sleep),
                "--workers",
                str(args.workers),
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
