#!/usr/bin/env python3
"""Run the DeepSeek + internal GPT-5.5 quality loop on a weekday Mac."""

import argparse
import datetime as dt
import fcntl
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

from company_gpt import keychain_secret
from ensure_daily_minimum import today_count
from insight_common import ROOT, load_env, today
from nightly_social_update import publish


LOCAL_TZ = ZoneInfo("Asia/Shanghai")
DEEPSEEK_KEYCHAIN_SERVICE = "design-daily-deepseek-api-key"


def run(cmd, check=True):
    print("+ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=check)


def phase_target(now=None):
    now = now or dt.datetime.now(LOCAL_TZ)
    clock = now.hour * 100 + now.minute
    if clock < 1100:
        return 15
    if clock < 1500:
        return 30
    return 40


def sync_main():
    result = run(["git", "pull", "--rebase", "--autostash", "origin", "main"], check=False)
    if result.returncode:
        raise RuntimeError("Could not synchronize the local runner with origin/main")


def ensure_secrets():
    load_env()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        secret = keychain_secret(DEEPSEEK_KEYCHAIN_SERVICE)
        if secret:
            os.environ["DEEPSEEK_API_KEY"] = secret
    os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-v4-flash")
    os.environ.setdefault("COMPANY_GPT_MODEL", "gpt-5.5")
    os.environ.setdefault("COMPANY_GPT_BASE_URL", "https://ai-gateway.insta360.cn/v1")
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DeepSeek key is missing from the environment and macOS Keychain")


def run_company_review(workers):
    run(
        [
            sys.executable,
            "scripts/company_multimodal_review.py",
            "--date",
            today(),
            "--workers",
            str(workers),
        ]
    )


def top_up(target, pass_index, workers):
    reserve = target + max(5, int(round(target * 0.3)))
    if target <= 15:
        queries, pages = 50, 220
    elif target <= 30:
        queries, pages = 70, 320
    else:
        queries, pages = 90, 420
    run([sys.executable, "scripts/collect_public.py"])
    run([sys.executable, "scripts/collect_curated_pages.py", "--limit", "90", "--shopify-pages", "1"])
    run([sys.executable, "scripts/search_jobs.py"])
    run(
        [
            sys.executable,
            "scripts/ensure_daily_minimum.py",
            "--target",
            str(reserve),
            "--max-passes",
            "2",
            "--workers",
            "8",
            "--agent-queries",
            str(queries),
            "--agent-pages",
            str(pages),
            "--agent-screen-workers",
            "5",
            "--shopify-pages",
            "1",
        ]
    )
    run_company_review(workers)
    print(
        f"dual_model_top_up pass={pass_index} target={target} reserve={reserve} "
        f"accepted={today_count(target)}",
        flush=True,
    )


def rebuild_and_publish(repo, score_limit, skip_publish):
    run([sys.executable, "scripts/enrich_images.py", "--limit", "80"])
    run([sys.executable, "scripts/score.py", "--limit", str(score_limit)])
    run([sys.executable, "scripts/trend_agent.py", "--limit", "100"])
    run([sys.executable, "scripts/build_site.py"])
    run([sys.executable, "scripts/weekly_report.py", "--limit", "100"])
    run([sys.executable, "scripts/build_site.py"])
    if not skip_publish:
        publish(repo, f"Update dual-model insight pool {today()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, choices=(15, 30, 40), default=0)
    parser.add_argument("--max-top-up-passes", type=int, default=3)
    parser.add_argument("--company-workers", type=int, default=3)
    parser.add_argument("--score-limit", type=int, default=100)
    parser.add_argument("--repo", default="suoasuoa/design-daily")
    parser.add_argument("--skip-publish", action="store_true")
    parser.add_argument("--force-weekend", action="store_true")
    args = parser.parse_args()

    now = dt.datetime.now(LOCAL_TZ)
    if now.weekday() >= 5 and not args.force_weekend:
        print(f"dual_model_update=skipped reason=weekend date={now.date().isoformat()}")
        return

    lock_path = Path.home() / "Library" / "Caches" / "design-daily-dual-model.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("dual_model_update=skipped reason=already_running")
            return

        ensure_secrets()
        sync_main()
        target = args.target or phase_target(now)
        run_company_review(args.company_workers)
        count = today_count(target)
        print(f"dual_model_phase date={today()} target={target} after_review={count}", flush=True)

        for pass_index in range(1, args.max_top_up_passes + 1):
            if count >= target:
                break
            top_up(target, pass_index, args.company_workers)
            count = today_count(target)

        rebuild_and_publish(args.repo, args.score_limit, args.skip_publish)
        status = "complete" if count >= target else "incomplete"
        print(f"dual_model_update={status} date={today()} accepted={count} target={target}", flush=True)


if __name__ == "__main__":
    main()
