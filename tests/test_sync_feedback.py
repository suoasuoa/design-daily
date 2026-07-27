import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sync_feedback import merge_events


class SyncFeedbackTests(unittest.TestCase):
    def test_merge_events_deduplicates_and_sorts(self):
        existing = [
            {"event_id": "b", "created_at": "2026-07-27T08:01:00Z", "action": "pass"},
        ]
        incoming = [
            {"event_id": "a", "created_at": "2026-07-27T08:00:00Z", "action": "like"},
            {"event_id": "b", "created_at": "2026-07-27T08:01:00Z", "action": "like"},
        ]

        merged = merge_events(existing, incoming)

        self.assertEqual([event["event_id"] for event in merged], ["a", "b"])
        self.assertEqual(merged[1]["action"], "like")

    def test_merge_events_ignores_rows_without_event_id(self):
        self.assertEqual(merge_events([], [{"created_at": "2026-07-27T08:00:00Z"}]), [])


if __name__ == "__main__":
    unittest.main()
