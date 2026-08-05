import datetime as dt
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from push_feishu_recovery import recoverable_groups


class FeishuRecoveryTests(unittest.TestCase):
    def test_complete_missed_group_can_be_recovered(self):
        group = {
            "date": "2026-08-04",
            "items": [{"id": str(index)} for index in range(40)],
            "stats": {"backfill_count": 0},
        }

        groups = recoverable_groups(
            {"daily_groups": [group]},
            {},
            dt.date(2026, 8, 5),
            recover_days=7,
            min_count=40,
        )

        self.assertEqual(groups, [group])

    def test_retroactively_backfilled_group_is_not_pushed_as_yesterday(self):
        items = [{"id": str(index)} for index in range(39)]
        items.append({"id": "late", "is_backfill": True})
        group = {
            "date": "2026-08-04",
            "items": items,
            "stats": {"backfill_count": 1},
        }

        groups = recoverable_groups(
            {"daily_groups": [group]},
            {},
            dt.date(2026, 8, 5),
            recover_days=7,
            min_count=40,
        )

        self.assertEqual(groups, [])


if __name__ == "__main__":
    unittest.main()
