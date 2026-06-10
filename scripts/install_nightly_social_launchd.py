#!/usr/bin/env python3
"""Install a macOS LaunchAgent for the local nightly social collector."""

import argparse
import plistlib
import subprocess
import sys
from pathlib import Path

from insight_common import ROOT


LABEL = "com.design-daily.nightly-social"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hour", type=int, default=0, help="Local hour to run, 0-23.")
    parser.add_argument("--minute", type=int, default=30, help="Local minute to run, 0-59.")
    parser.add_argument("--target-total", type=int, default=80)
    parser.add_argument("--min-social", type=int, default=10)
    args = parser.parse_args()

    launch_dir = Path.home() / "Library" / "LaunchAgents"
    launch_dir.mkdir(parents=True, exist_ok=True)
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    plist_path = launch_dir / f"{LABEL}.plist"
    python = sys.executable

    payload = {
        "Label": LABEL,
        "ProgramArguments": [
            python,
            str(ROOT / "scripts" / "nightly_social_update.py"),
            "--target-total",
            str(args.target_total),
            "--min-social",
            str(args.min_social),
        ],
        "WorkingDirectory": str(ROOT),
        "StartCalendarInterval": {"Hour": args.hour, "Minute": args.minute},
        "StandardOutPath": str(log_dir / "nightly-social.out.log"),
        "StandardErrorPath": str(log_dir / "nightly-social.err.log"),
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
    }

    with plist_path.open("wb") as f:
        plistlib.dump(payload, f)

    subprocess.run(["launchctl", "unload", str(plist_path)], check=False)
    subprocess.run(["launchctl", "load", str(plist_path)], check=True)
    print(f"installed={plist_path}")
    print(f"schedule={args.hour:02d}:{args.minute:02d} local time")
    print(f"logs={log_dir}")


if __name__ == "__main__":
    main()
