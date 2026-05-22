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
    parser.add_argument("--score-limit", type=int, default=200, help="Number of products to score.")
    parser.add_argument("--trend-limit", type=int, default=80, help="Number of products to include in trend report.")
    parser.add_argument("--force-score", action="store_true", help="Rescore already-scored products.")
    args = parser.parse_args()

    py = sys.executable
    if not args.skip_collect:
        run([py, "scripts/collect_public.py"])
    run([py, "scripts/dedupe.py"])
    run([py, "scripts/review_categories.py"])
    score_cmd = [py, "scripts/score.py", "--limit", str(args.score_limit)]
    if args.force_score:
        score_cmd.append("--force")
    run(score_cmd)
    run([py, "scripts/trend_agent.py", "--limit", str(args.trend_limit)])
    run([py, "scripts/build_site.py"])
    print("agent_update=done")


if __name__ == "__main__":
    main()
