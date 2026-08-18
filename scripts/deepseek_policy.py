#!/usr/bin/env python3
"""Enforce DeepSeek access windows and keep a lightweight per-run usage ledger."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("Asia/Shanghai")
DEFAULT_WINDOWS = "00:00-08:59,12:01-13:59,18:01-23:59"
DEFAULT_USAGE_FILE = "/tmp/design-daily-deepseek-usage.json"


class DeepSeekPolicyError(RuntimeError):
    """Raised when a request would violate a time or call-budget rule."""


class DeepSeekWindowClosed(DeepSeekPolicyError):
    pass


class DeepSeekBudgetExceeded(DeepSeekPolicyError):
    pass


def _parse_clock(value: str) -> dt.time:
    hour, minute = value.strip().split(":", 1)
    return dt.time(int(hour), int(minute))


def allowed_windows() -> list[tuple[dt.time, dt.time]]:
    raw = os.environ.get("DEEPSEEK_ALLOWED_WINDOWS", DEFAULT_WINDOWS)
    windows = []
    for item in raw.split(","):
        start, end = item.strip().split("-", 1)
        windows.append((_parse_clock(start), _parse_clock(end)))
    return windows


def window_status(now: dt.datetime | None = None) -> dict:
    now = (now or dt.datetime.now(LOCAL_TZ)).astimezone(LOCAL_TZ)
    if os.environ.get("DEEPSEEK_ALLOW_OUTSIDE_WINDOW") == "1":
        return {
            "open": True,
            "now": now.isoformat(),
            "window": "explicit_override",
            "minutes_remaining": None,
        }

    buffer_minutes = max(0, int(os.environ.get("DEEPSEEK_WINDOW_END_BUFFER_MINUTES", "3")))
    for start, end in allowed_windows():
        start_at = dt.datetime.combine(now.date(), start, LOCAL_TZ)
        end_at = dt.datetime.combine(now.date(), end, LOCAL_TZ) - dt.timedelta(minutes=buffer_minutes)
        if start_at <= now <= end_at:
            return {
                "open": True,
                "now": now.isoformat(),
                "window": f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}",
                "minutes_remaining": max(0, int((end_at - now).total_seconds() // 60)),
            }
    return {
        "open": False,
        "now": now.isoformat(),
        "window": "",
        "minutes_remaining": 0,
    }


def require_deepseek_window(component: str = "deepseek") -> dict:
    status = window_status()
    if not status["open"]:
        configured = os.environ.get("DEEPSEEK_ALLOWED_WINDOWS", DEFAULT_WINDOWS)
        raise DeepSeekWindowClosed(
            f"DeepSeek blocked outside Beijing windows {configured}; "
            f"component={component} now={status['now']}"
        )
    return status


def _usage_path() -> Path:
    return Path(os.environ.get("DEEPSEEK_USAGE_FILE", DEFAULT_USAGE_FILE))


def _mutate_usage(mutator):
    path = _usage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        try:
            payload = json.loads(handle.read() or "{}")
        except json.JSONDecodeError:
            payload = {}
        current_day = dt.datetime.now(LOCAL_TZ).date().isoformat()
        if payload.get("date") != current_day:
            payload = {
                "date": current_day,
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "components": {},
            }
        result = mutator(payload)
        handle.seek(0)
        handle.truncate()
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.flush()
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return result


def reserve_deepseek_call(component: str = "deepseek") -> dict:
    status = require_deepseek_window(component)
    run_limit = max(0, int(os.environ.get("DEEPSEEK_MAX_CALLS", "80")))
    daily_limit = max(0, int(os.environ.get("DEEPSEEK_DAILY_MAX_CALLS", "0")))
    run_id = os.environ.get("GITHUB_RUN_ID") or os.environ.get("DEEPSEEK_RUN_ID") or "local"

    def reserve(payload):
        calls = int(payload.get("calls") or 0)
        runs = payload.setdefault("runs", {})
        run_row = runs.setdefault(run_id, {"calls": 0})
        run_calls = int(run_row.get("calls") or 0)
        if daily_limit and calls >= daily_limit:
            raise DeepSeekBudgetExceeded(
                f"DeepSeek daily call budget reached: {calls}/{daily_limit}; component={component}"
            )
        if run_limit and run_calls >= run_limit:
            raise DeepSeekBudgetExceeded(
                f"DeepSeek run call budget reached: {run_calls}/{run_limit}; component={component}"
            )
        payload["calls"] = calls + 1
        run_row["calls"] = run_calls + 1
        components = payload.setdefault("components", {})
        row = components.setdefault(component, {"calls": 0, "total_tokens": 0})
        row["calls"] = int(row.get("calls") or 0) + 1
        return {
            **status,
            "daily_calls": payload["calls"],
            "daily_limit": daily_limit,
            "run_calls": run_row["calls"],
            "run_limit": run_limit,
        }

    return _mutate_usage(reserve)


def record_deepseek_usage(component: str, response_payload: dict) -> None:
    usage = response_payload.get("usage") or {}
    prompt = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    total = int(usage.get("total_tokens") or prompt + completion)

    def record(payload):
        payload["prompt_tokens"] = int(payload.get("prompt_tokens") or 0) + prompt
        payload["completion_tokens"] = int(payload.get("completion_tokens") or 0) + completion
        payload["total_tokens"] = int(payload.get("total_tokens") or 0) + total
        row = payload.setdefault("components", {}).setdefault(
            component, {"calls": 0, "total_tokens": 0}
        )
        row["total_tokens"] = int(row.get("total_tokens") or 0) + total

    _mutate_usage(record)


def usage_report() -> dict:
    path = _usage_path()
    if not path.exists():
        return {"date": dt.datetime.now(LOCAL_TZ).date().isoformat(), "calls": 0}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"date": dt.datetime.now(LOCAL_TZ).date().isoformat(), "calls": 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--export-github-env", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    if args.report:
        print(json.dumps(usage_report(), ensure_ascii=False, indent=2, sort_keys=True))
        return

    status = window_status()
    print(
        f"deepseek_window open={status['open']} now={status['now']} "
        f"window={status['window'] or 'closed'} remaining={status['minutes_remaining']}"
    )
    if args.export_github_env and os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as handle:
            handle.write(f"DEEPSEEK_WINDOW_OPEN={'1' if status['open'] else '0'}\n")
    if args.check and not status["open"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
