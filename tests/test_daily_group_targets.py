import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_site import daily_group_limit, merge_historical_snapshots


class DailyGroupTargetTests(unittest.TestCase):
    def test_legacy_dates_keep_thirty_item_target(self):
        self.assertEqual(daily_group_limit("2026-07-19", 40), 30)

    def test_forty_item_policy_survives_future_rebuilds(self):
        self.assertEqual(daily_group_limit("2026-07-20", 40), 40)
        self.assertEqual(daily_group_limit("2026-07-21", 40), 40)
        self.assertEqual(daily_group_limit("2026-07-22", 40), 40)

    def test_historical_snapshot_is_preserved_then_topped_up(self):
        previous_items = [{"id": f"old-{index}"} for index in range(30)]
        fresh_items = previous_items + [{"id": f"new-{index}"} for index in range(10)]
        groups = [{"date": "2026-07-21", "target_count": 40, "items": fresh_items}]
        previous = [{"date": "2026-07-21", "target_count": 30, "items": previous_items}]

        merged = merge_historical_snapshots(groups, previous, "2026-07-22")

        self.assertEqual(len(merged[0]["items"]), 40)
        self.assertEqual(merged[0]["items"][:30], previous_items)


if __name__ == "__main__":
    unittest.main()
