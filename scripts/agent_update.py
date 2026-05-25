#!/usr/bin/env python3
"""One-command agent workflow: collect, dedupe, score, report, and build."""

import argparse
import subprocess
import sys

from insight_common import load_env


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-collect", action="store_true", help="Skip public RSS collection.")
    parser.add_argument("--skip-search", action="store_true", help="Skip open-web search collection.")
    parser.add_argument("--search-jobs", type=int, default=40, help="Number of open-web search jobs to run.")
    parser.add_argument("--search-results", type=int, default=4, help="Number of search results to keep per job.")
    parser.add_argument("--score-limit", type=int, default=200, help="Number of products to score.")
    parser.add_argument("--trend-limit", type=int, default=80, help="Number of products to include in trend report.")
    parser.add_argument("--weekly-limit", type=int, default=100, help="Number of products to include in weekly report.")
    parser.add_argument("--force-score", action="store_true", help="Rescore already-scored products.")
    args = parser.parse_args()

    py = sys.executable
    if not args.skip_collect:
        run([py, "scripts/collect_public.py"])
    if not args.skip_search:
        run([py, "scripts/search_jobs.py"])
        run([py, "scripts/collect_search.py", "--limit-jobs", str(args.search_jobs), "--per-job", str(args.search_results)])
    run([py, "scripts/dedupe.py"])
    run([py, "scripts/review_categories.py"])
    run([py, "scripts/enrich_images.py", "--limit", "80"])
    score_cmd = [py, "scripts/score.py", "--limit", str(args.score_limit)]
    if args.force_score:
        score_cmd.append("--force")
    run(score_cmd)
    run([py, "scripts/trend_agent.py", "--limit", str(args.trend_limit)])
    run([py, "scripts/build_site.py"])
    run([py, "scripts/weekly_report.py", "--limit", str(args.weekly_limit)])
    run([py, "scripts/build_site.py"])
    print("agent_update=done")


if __name__ == "__main__":
    main()
