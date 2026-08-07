import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_site import display_eligible
from insight_common import semantic_title_duplicate
from promote_reviewed_backlog import clean_candidate_title


class SemanticDedupeTests(unittest.TestCase):
    def test_detects_same_product_worded_as_light_and_lighting(self):
        self.assertTrue(
            semantic_title_duplicate(
                "Red Dot Design Award: Bladeless Fan For Home Lighting",
                "Red Dot Design Award: Bladeless Fan Light",
            )
        )

    def test_does_not_merge_distinct_bottle_names(self):
        self.assertFalse(
            semantic_title_duplicate(
                "Red Dot Design Award: Vacuum Bottles",
                "Red Dot Design Award: MyBottle",
            )
        )

    def test_backlog_recheck_keeps_high_innovation_direction_item(self):
        item = {
            "title": "A modular light",
            "url": "https://example.com/product/modular-light",
            "category": "氛围灯",
            "review_policy_version": 3,
            "review_source": "deepseek_backlog_recheck",
            "review_reason": "模块可重新组合，结构创新明确",
            "quality_score": 65,
            "innovation": 8,
            "relevance": 9,
            "review_confidence": 8,
            "source_quality": "standard",
            "summary": "模块可重新组合",
        }

        self.assertTrue(display_eligible(item))

    def test_low_innovation_backlog_item_is_not_displayed(self):
        item = {
            "title": "A basic light",
            "url": "https://example.com/product/basic-light",
            "category": "氛围灯",
            "review_policy_version": 3,
            "review_source": "deepseek_backlog_recheck",
            "review_reason": "基础款",
            "quality_score": 69,
            "innovation": 7,
            "relevance": 9,
            "review_confidence": 8,
            "source_quality": "standard",
            "summary": "基础款",
        }

        self.assertFalse(display_eligible(item))

    def test_cleans_scraped_source_suffixes(self):
        self.assertEqual(
            clean_candidate_title("Moon Gift :: Behance Adobe, Inc. Behance"),
            "Moon Gift",
        )


if __name__ == "__main__":
    unittest.main()
