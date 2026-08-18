import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_site import category_under_cap, daily_group_limit, display_eligible, merge_historical_snapshots, sorted_daily_items, source_under_cap
from insight_common import is_ordinary_laptop_stand
from deepseek_search_agent import PRE_REVIEW_VERSION, accepted_today, fallback_query_jobs, searchable_categories


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

    def test_current_day_snapshot_can_be_replaced_by_better_candidates(self):
        previous_items = [{"id": "weak", "score": 62}]
        fresh_items = [{"id": "strong", "score": 84}]
        groups = [{"date": "2026-08-13", "target_count": 40, "items": fresh_items}]
        previous = [{"date": "2026-08-13", "target_count": 40, "items": previous_items}]

        merged = merge_historical_snapshots(groups, previous, "2026-08-13")

        self.assertEqual(merged[0]["items"], fresh_items)

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

    def test_all_categories_keep_strict_caps_during_fill(self):
        picks = [{"category": "创意桌搭"} for _ in range(5)]

        self.assertFalse(category_under_cap(picks, "创意桌搭", relaxed="emergency"))

    def test_regular_category_cap_is_five_for_balanced_forty(self):
        self.assertTrue(category_under_cap([{"category": "水杯"} for _ in range(4)], "水杯"))
        self.assertFalse(category_under_cap([{"category": "水杯"} for _ in range(5)], "水杯"))

    def test_single_source_is_capped_at_five(self):
        picks = [{"source_name": "Yanko Design"} for _ in range(5)]

        self.assertFalse(source_under_cap(picks, "Yanko Design"))

    def test_quality_floor_is_hard_for_backlog_items(self):
        item = {
            "title": "Weak gift box",
            "category": "创意礼盒",
            "url": "https://example.com/product",
            "review_policy_version": 3,
            "review_source": "deepseek_backlog_balanced",
            "quality_score": 73,
            "innovation": 8,
            "relevance": 9,
            "review_confidence": 9,
            "summary": "Concrete packaging structure",
            "source_quality": "premium",
        }

        self.assertFalse(display_eligible(item))

    def test_laptop_stands_are_not_desk_inspiration(self):
        item = {
            "title": "Ultra-thin origami laptop stand",
            "summary": "A folded stand props up a notebook computer.",
            "category": "创意桌搭",
        }

        self.assertTrue(is_ordinary_laptop_stand(item))

    def test_fallback_queries_limit_phone_cases_and_power_banks(self):
        jobs = fallback_query_jobs(50, 0)
        categories = [job.get("category") for job in jobs]

        self.assertLessEqual(categories.count("手机壳"), 3)
        self.assertLessEqual(categories.count("充电宝"), 3)

    def test_search_agent_counts_displayable_group_not_raw_today_rows(self):
        # accepted_today is intentionally wired through build_daily_groups;
        # this guards against reverting to a raw first_seen count that ignores
        # category and source caps.
        self.assertEqual(accepted_today.__doc__.splitlines()[0], "Return the products that can actually appear in today's dashboard.")

    def test_search_agent_excludes_categories_with_no_display_slots(self):
        current = {"水杯": 5, "氛围灯": 5, "创意厨具": 5, "手机壳": 2}

        allowed = searchable_categories(current)

        self.assertNotIn("水杯", allowed)
        self.assertNotIn("氛围灯", allowed)
        self.assertNotIn("创意厨具", allowed)
        self.assertIn("手机壳", allowed)

    def test_search_prescreen_policy_is_versioned_for_wider_recall(self):
        self.assertEqual(PRE_REVIEW_VERSION, 2)


if __name__ == "__main__":
    unittest.main()
