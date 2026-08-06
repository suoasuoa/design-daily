#!/usr/bin/env python3
"""Install the weekday macOS Feishu dispatch backstop."""

import os
from pathlib import Path
import plistlib
import subprocess
import sys

from insight_common import ROOT


LABEL = "com.design-daily.feishu-dispatch"
DEFAULT_TIMES = ((18, 0), (18, 20))


def calendar_intervals(times):
    return [
        {"Weekday": weekday, "Hour": hour, "Minute": minute}
        for weekday in range(2, 7)
        for hour, minute in times
    ]


def main():
    launch_dir = Path.home() / "Library" / "LaunchAgents"
    launch_dir.mkdir(parents=True, exist_ok=True)
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    plist_path = launch_dir / f"{LABEL}.plist"
    domain = f"gui/{os.getuid()}"

    payload = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(ROOT / "scripts" / "dispatch_feishu_workflow.py")],
        "WorkingDirectory": str(ROOT),
        "StartCalendarInterval": calendar_intervals(DEFAULT_TIMES),
        "StandardOutPath": str(log_dir / "feishu-dispatch.out.log"),
        "StandardErrorPath": str(log_dir / "feishu-dispatch.err.log"),
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        "ProcessType": "Background",
        "ThrottleInterval": 60,
    }

    with plist_path.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=True)

    subprocess.run(
        ["launchctl", "bootout", domain, str(plist_path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(["launchctl", "bootstrap", domain, str(plist_path)], check=True)
    subprocess.run(["launchctl", "enable", f"{domain}/{LABEL}"], check=True)
    print(f"installed={plist_path}")
    print("schedule=weekdays 18:00; recovery check 18:20 Asia/Shanghai")
    print(f"logs={log_dir}")


if __name__ == "__main__":
    main()
