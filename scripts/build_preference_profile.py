#!/usr/bin/env python3
"""Compile raw feedback events into the preference profile used by AI stages."""

from insight_common import DATA_DIR, ensure_dirs, load_json, write_json
from preference_profile import build_profile


def main():
    ensure_dirs()
    events = load_json(DATA_DIR / "feedback_events.json", [])
    profile = build_profile(events)
    write_json(DATA_DIR / "preference_profile.json", profile)
    stats = profile["stats"]
    print(
        "preference_profile="
        f"events:{stats['events']} active:{stats['active_decisions']} "
        f"likes:{stats['likes']} passes:{stats['passes']}"
    )


if __name__ == "__main__":
    main()
