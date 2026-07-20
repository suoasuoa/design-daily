#!/usr/bin/env python3
"""Install the weekday macOS scheduler for the dual-model review pipeline."""

import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys

from insight_common import ROOT


LABEL = "com.design-daily.dual-model"
DEFAULT_TIMES = ((8, 45), (12, 45), (16, 15))


def calendar_intervals(times):
    return [
        {"Weekday": weekday, "Hour": hour, "Minute": minute}
        for weekday in range(1, 6)
        for hour, minute in times
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--company-workers", type=int, default=3)
    parser.add_argument("--max-top-up-passes", type=int, default=3)
    args = parser.parse_args()

    launch_dir = Path.home() / "Library" / "LaunchAgents"
    launch_dir.mkdir(parents=True, exist_ok=True)
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    plist_path = launch_dir / f"{LABEL}.plist"
    domain = f"gui/{os.getuid()}"

    payload = {
        "Label": LABEL,
        "ProgramArguments": [
            sys.executable,
            str(ROOT / "scripts" / "local_dual_model_update.py"),
            "--company-workers",
            str(args.company_workers),
            "--max-top-up-passes",
            str(args.max_top_up_passes),
        ],
        "WorkingDirectory": str(ROOT),
        "StartCalendarInterval": calendar_intervals(DEFAULT_TIMES),
        "StandardOutPath": str(log_dir / "dual-model.out.log"),
        "StandardErrorPath": str(log_dir / "dual-model.err.log"),
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "COMPANY_GPT_BASE_URL": "https://ai-gateway.insta360.cn/v1",
            "COMPANY_GPT_MODEL": "gpt-5.5",
            "DEEPSEEK_MODEL": "deepseek-v4-flash",
        },
        "ProcessType": "Background",
        "ThrottleInterval": 60,
    }

    with plist_path.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=True)

    subprocess.run(["launchctl", "bootout", domain, str(plist_path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["launchctl", "bootstrap", domain, str(plist_path)], check=True)
    subprocess.run(["launchctl", "enable", f"{domain}/{LABEL}"], check=True)
    print(f"installed={plist_path}")
    print("schedule=weekdays 08:45, 12:45, 16:15 Asia/Shanghai")
    print(f"working_directory={ROOT}")
    print(f"logs={log_dir}")


if __name__ == "__main__":
    main()
