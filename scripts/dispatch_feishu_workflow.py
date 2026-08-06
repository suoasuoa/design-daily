#!/usr/bin/env python3
"""Dispatch the Feishu workflow from the weekday Mac as a schedule backstop."""

import argparse
import datetime as dt
import os
import subprocess
import time
from zoneinfo import ZoneInfo

from company_gpt import keychain_secret
from insight_common import ROOT, load_env


LOCAL_TZ = ZoneInfo("Asia/Shanghai")
GITHUB_KEYCHAIN_SERVICE = "design-daily-github-token"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="suoasuoa/design-daily")
    parser.add_argument("--force-weekend", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    now = dt.datetime.now(LOCAL_TZ)
    if now.weekday() >= 5 and not args.force_weekend:
        print(f"feishu_dispatch=skipped reason=weekend date={now.date().isoformat()}")
        return

    load_env()
    if not os.environ.get("GH_TOKEN"):
        token = keychain_secret(GITHUB_KEYCHAIN_SERVICE)
        if token:
            os.environ["GH_TOKEN"] = token
    if not os.environ.get("GH_TOKEN"):
        raise RuntimeError("GitHub token is missing from the environment and macOS Keychain")

    command = [
        "gh",
        "workflow",
        "run",
        "feishu-daily-push.yml",
        "--repo",
        args.repo,
        "-f",
        "force_send=false",
    ]
    if args.dry_run:
        print("feishu_dispatch=dry_run command=" + " ".join(command))
        return

    last_error = ""
    for attempt in range(1, 4):
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode == 0:
            print(f"feishu_dispatch=triggered attempt={attempt} time={now.isoformat()}")
            return
        last_error = result.stderr.strip()
        if attempt < 3:
            time.sleep(attempt * 5)
    raise RuntimeError(f"Could not dispatch Feishu workflow: {last_error}")


if __name__ == "__main__":
    main()
