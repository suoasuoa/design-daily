#!/usr/bin/env python3
"""One-command DeepSeek workflow: discover, verify, review, score, and build."""

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
    parser.add_argument("--skip-search", action="store_true", help="Skip DeepSeek open-web discovery.")
    parser.add_argument("--daily-target", type=int, default=40, help="Required accepted products for today.")
    parser.add_argument("--agent-queries", type=int, default=70, help="DeepSeek-planned searches per round.")
    parser.add_argument("--agent-pages", type=int, default=320, help="Maximum fresh pages screened per round.")
    parser.add_argument("--search-results", type=int, default=10, help="Search results inspected per query.")
    parser.add_argument("--max-passes", type=int, default=3, help="Maximum DeepSeek top-up rounds.")
    parser.add_argument("--score-limit", type=int, default=200, help="Number of products to score.")
    parser.add_argument("--trend-limit", type=int, default=80, help="Number of products to include in trend report.")
    parser.add_argument("--weekly-limit", type=int, default=100, help="Number of products to include in weekly report.")
    parser.add_argument("--force-score", action="store_true", help="Rescore already-scored products.")
    args = parser.parse_args()

    py = sys.executable
    if not args.skip_collect:
        run([py, "scripts/collect_public.py"])
        run([py, "scripts/collect_curated_pages.py", "--limit", "90", "--shopify-pages", "1"])
    if not args.skip_search:
        run([py, "scripts/search_jobs.py"])
        run(
            [
                py,
                "scripts/deepseek_search_agent.py",
                "--target",
                str(args.daily_target),
                "--query-count",
                str(args.agent_queries),
                "--per-query",
                str(args.search_results),
                "--max-pages",
                str(args.agent_pages),
            ]
        )
    run([py, "scripts/dedupe.py"])
    run([py, "scripts/review_categories.py"])
    if not args.skip_search:
        run(
            [
                py,
                "scripts/ensure_daily_minimum.py",
                "--target",
                str(args.daily_target),
                "--per-job",
                str(args.search_results),
                "--max-passes",
                str(args.max_passes),
                "--agent-queries",
                str(args.agent_queries),
                "--agent-pages",
                str(args.agent_pages),
            ]
        )
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
