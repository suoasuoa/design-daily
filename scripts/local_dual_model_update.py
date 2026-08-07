#!/usr/bin/env python3
"""Run the DeepSeek + internal GPT-5.5 quality loop on a weekday Mac."""

import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from zoneinfo import ZoneInfo

from company_gpt import keychain_secret
from ensure_daily_minimum import today_count
from insight_common import ROOT, load_env, today
from nightly_social_update import publish_api_only


LOCAL_TZ = ZoneInfo("Asia/Shanghai")
DEEPSEEK_KEYCHAIN_SERVICE = "design-daily-deepseek-api-key"
GITHUB_KEYCHAIN_SERVICE = "design-daily-github-token"


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


def sync_main(repo):
    """Refresh cloud-produced data without relying on the broken local Git transport."""
    with tempfile.TemporaryDirectory(prefix="design-daily-sync-") as temp_dir:
        archive_path = Path(temp_dir) / "repo.tar.gz"
        with archive_path.open("wb") as archive:
            result = subprocess.run(
                ["gh", "api", f"repos/{repo}/tarball/main"],
                cwd=ROOT,
                stdout=archive,
                stderr=subprocess.PIPE,
                check=False,
            )
        if result.returncode:
            raise RuntimeError(f"Could not download the GitHub data snapshot: {result.stderr.decode().strip()}")
        extract_dir = Path(temp_dir) / "repo"
        extract_dir.mkdir()
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(extract_dir)
        roots = [path for path in extract_dir.iterdir() if path.is_dir()]
        if len(roots) != 1:
            raise RuntimeError("The GitHub data snapshot had an unexpected layout")
        snapshot = roots[0]
        for name in ("data", "insight"):
            source = snapshot / name
            destination = ROOT / name
            if not source.exists():
                continue
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)
    print(f"sync=github_api_snapshot repo={repo}", flush=True)


def ensure_secrets():
    load_env()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        secret = keychain_secret(DEEPSEEK_KEYCHAIN_SERVICE)
        if secret:
            os.environ["DEEPSEEK_API_KEY"] = secret
    if not os.environ.get("GH_TOKEN"):
        secret = keychain_secret(GITHUB_KEYCHAIN_SERVICE)
        if secret:
            os.environ["GH_TOKEN"] = secret
    os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-v4-flash")
    os.environ.setdefault("COMPANY_GPT_MODEL", "gpt-5.5")
    os.environ.setdefault("COMPANY_GPT_BASE_URL", "https://ai-gateway.insta360.cn/v1")
    os.environ["STAGE_COMPANY_REVIEW_CANDIDATES"] = "1"
    os.environ["USE_COMPANY_QUERY_PLANNER"] = "1"
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DeepSeek key is missing from the environment and macOS Keychain")
    if not os.environ.get("GH_TOKEN"):
        raise RuntimeError("GitHub token is missing from the environment and macOS Keychain")


def cloud_insight_active(repo):
    result = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--repo",
            repo,
            "--workflow",
            "Insight Pool",
            "--limit",
            "10",
            "--json",
            "status",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Could not check the cloud Insight Pool state: {result.stderr.strip()}")
    return any(row.get("status") in {"queued", "in_progress", "waiting", "pending"} for row in json.loads(result.stdout))


def run_company_review(workers, review_limit):
    run(
        [
            sys.executable,
            "scripts/company_multimodal_review.py",
            "--date",
            today(),
            "--workers",
            str(workers),
            "--limit",
            str(review_limit),
            "--include-rejected",
            "--lane",
            "company_gpt",
        ]
    )


def top_up(target, pass_index, workers, review_limit):
    if target <= 15:
        reserve = 30
    elif target <= 30:
        reserve = 50
    else:
        reserve = 80
    if target <= 15:
        queries, pages = 50, 220
    elif target <= 30:
        queries, pages = 70, 320
    else:
        queries, pages = 90, 420
    run(
        [
            sys.executable,
            "scripts/company_search_agent.py",
            "--target",
            str(target),
            "--round",
            str(pass_index - 1),
            "--query-count",
            str(queries),
            "--max-pages",
            str(pages),
            "--screen-workers",
            str(workers),
        ]
    )
    run([sys.executable, "scripts/dedupe.py"])
    run_company_review(workers, review_limit)
    company_count = today_count(target)
    print(
        f"company_lane pass={pass_index} target={target} accepted={company_count}",
        flush=True,
    )
    if company_count >= target:
        return

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
    print(
        f"dual_model_top_up pass={pass_index} target={target} reserve={reserve} "
        f"accepted={today_count(target)}",
        flush=True,
    )


def rebuild_and_publish(repo, score_limit, skip_publish):
    run([sys.executable, "scripts/enrich_images.py", "--limit", "80"])
    run([sys.executable, "scripts/score.py", "--limit", str(score_limit), "--date", today()])
    run([sys.executable, "scripts/trend_agent.py", "--limit", "100"])
    run([sys.executable, "scripts/build_site.py"])
    run([sys.executable, "scripts/weekly_report.py", "--limit", "100"])
    run([sys.executable, "scripts/build_site.py"])
    if not skip_publish:
        publish_api_only(repo, f"Update dual-model insight pool {today()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, choices=(15, 30, 40), default=0)
    parser.add_argument("--max-top-up-passes", type=int, default=3)
    parser.add_argument("--company-workers", type=int, default=3)
    parser.add_argument("--company-review-limit", type=int, default=160)
    parser.add_argument("--score-limit", type=int, default=100)
    parser.add_argument("--repo", default="suoasuoa/design-daily")
    parser.add_argument("--skip-publish", action="store_true")
    parser.add_argument("--force-weekend", action="store_true")
    parser.add_argument("--ignore-cloud-busy", action="store_true")
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
        if not args.ignore_cloud_busy and cloud_insight_active(args.repo):
            print("dual_model_update=skipped reason=cloud_insight_active")
            return
        sync_main(args.repo)
        target = args.target or phase_target(now)
        run_company_review(args.company_workers, args.company_review_limit)
        count = today_count(target)
        print(f"dual_model_phase date={today()} target={target} after_review={count}", flush=True)

        if now.hour >= 17 and count >= target:
            local_changes = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                check=True,
            ).stdout.strip()
            if not local_changes:
                print(f"dual_model_recovery=healthy date={today()} accepted={count} target={target}")
                return

        for pass_index in range(1, args.max_top_up_passes + 1):
            if count >= target:
                break
            top_up(target, pass_index, args.company_workers, args.company_review_limit)
            count = today_count(target)

        rebuild_and_publish(args.repo, args.score_limit, args.skip_publish)
        status = "complete" if count >= target else "incomplete"
        print(f"dual_model_update={status} date={today()} accepted={count} target={target}", flush=True)


if __name__ == "__main__":
    main()
