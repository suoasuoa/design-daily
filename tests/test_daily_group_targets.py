import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_site import category_under_cap, daily_group_limit, merge_historical_snapshots, sorted_daily_items
from deepseek_search_agent import fallback_query_jobs


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

    def test_daily_items_are_displayed_by_score_descending(self):
        items = [
            {"title": "72", "score": 72, "quality_score": 80, "innovation": 8},
            {"title": "91", "score": 91, "quality_score": 75, "innovation": 9},
            {"title": "84", "score": 84, "quality_score": 90, "innovation": 8},
        ]

        ranked = sorted_daily_items(items)

        self.assertEqual([item["score"] for item in ranked], [91, 84, 72])

    def test_equal_scores_use_quality_then_innovation(self):
        items = [
            {"title": "lower-quality", "score": 88, "quality_score": 80, "innovation": 9},
            {"title": "higher-quality", "score": 88, "quality_score": 90, "innovation": 7},
        ]

        ranked = sorted_daily_items(items)

        self.assertEqual(ranked[0]["title"], "higher-quality")

    def test_phone_case_hard_cap_survives_relaxed_fill(self):
        picks = [{"category": "手机壳"} for _ in range(3)]

        self.assertFalse(category_under_cap(picks, "手机壳", relaxed=True))

    def test_power_bank_hard_cap_survives_relaxed_fill(self):
        picks = [{"category": "充电宝"} for _ in range(3)]

        self.assertFalse(category_under_cap(picks, "充电宝", relaxed=True))

    def test_fallback_queries_limit_phone_cases_and_power_banks(self):
        jobs = fallback_query_jobs(50, 0)
        categories = [job.get("category") for job in jobs]

        self.assertLessEqual(categories.count("手机壳"), 3)
        self.assertLessEqual(categories.count("充电宝"), 3)


if __name__ == "__main__":
    unittest.main()
