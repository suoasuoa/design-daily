import sys
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_site import build_daily_groups, display_eligible
from insight_common import load_daily_history, product_identity_keys, semantic_product_duplicate, semantic_title_duplicate
from promote_reviewed_backlog import clean_candidate_title


class SemanticDedupeTests(unittest.TestCase):
    def test_daily_history_prefers_last_public_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            insight_dir = root / "insight"
            data_dir = root / "data"
            insight_dir.mkdir()
            data_dir.mkdir()
            (insight_dir / "data.raw.json").write_text(
                json.dumps({"daily_groups": [{"date": "2026-08-17", "items": [{"id": "public"}]}]}),
                encoding="utf-8",
            )
            (data_dir / "published.json").write_text(
                json.dumps({"items": [{"id": "in-flight"}]}),
                encoding="utf-8",
            )

            with patch("insight_common.INSIGHT_DIR", insight_dir), patch("insight_common.DATA_DIR", data_dir):
                groups = load_daily_history()

        self.assertEqual(groups[0]["items"][0]["id"], "public")

    def test_detects_gerber_compleat_across_different_sites(self):
        uncrate = {
            "title": "Gerber Compleat Tool Set",
            "summary": "The ComplEAT tool set includes a fork and spoon.",
            "category": "创意厨具",
        }
        yanko = {
            "title": "The Gerber ComplEAT puts an entire cutlery set into your pocket - Yanko Design",
            "summary": "Gerber ComplEAT 将完整厨房工具集成到口袋大小。",
            "category": "创意厨具",
        }

        self.assertTrue(semantic_product_duplicate(uncrate, yanko))
        self.assertTrue(product_identity_keys(uncrate) & product_identity_keys(yanko))

    def test_detects_torras_ostand_family_across_headlines(self):
        earlier = {
            "title": "TORRAS Ostand Case Adds a Magnetic Twist Apple Didn't Think Of",
            "summary": "TORRAS Ostand手机壳，内置磁吸支架。",
            "category": "手机壳",
        }
        current = {
            "title": "Regular Phone Cases are Dead - These Phone Stands from TORRAS",
            "summary": "TORRAS Ostand R手机壳内置可旋转支架。",
            "category": "手机壳",
        }

        self.assertTrue(semantic_product_duplicate(earlier, current))

    def test_detects_exovault_across_design_sites(self):
        earlier = {
            "title": "EXOvault Metal iPhone Case | Cool Material",
            "summary": "A solid metal protective enclosure.",
            "category": "手机壳",
        }
        current = {
            "title": "Exovault iPhone Case",
            "summary": "Exovault 金属手机壳采用锁闭结构。",
            "category": "手机壳",
        }

        self.assertTrue(semantic_product_duplicate(earlier, current))

    def test_detects_vollebak_full_metal_jacket_across_headlines(self):
        earlier = {
            "title": "virus-killing copper jacket by vollebak wipes out bacteria and germs",
            "summary": "Vollebak copper Full Metal Jacket.",
            "category": "冲锋衣",
        }
        current = {
            "title": "Vollebak Full Metal Jacket",
            "summary": "Copper Edition uses woven copper wire.",
            "category": "冲锋衣",
        }

        self.assertTrue(semantic_product_duplicate(earlier, current))

    def test_explicit_product_identity_drives_future_cross_site_dedupe(self):
        earlier = {
            "title": "A protective phone accessory with a hidden stand",
            "product_identity": "ESR Cyber Tough Magnetic Case",
            "category": "手机壳",
        }
        current = {
            "title": "Apple says its newest phone is tough",
            "product_identity": "ESR Cyber Tough Magnetic Case for iPhone 17",
            "category": "手机壳",
        }

        self.assertTrue(semantic_product_duplicate(earlier, current))

    def test_human_confirmed_duplicate_url_is_not_displayed(self):
        item = {
            "title": "Exovault iPhone Case",
            "category": "手机壳",
            "url": "https://design-milk.com/exovault-iphone-case",
            "review_policy_version": 3,
            "quality_score": 90,
            "innovation": 9,
            "relevance": 9,
        }

        self.assertFalse(display_eligible(item))

    def test_does_not_merge_different_torras_product_categories(self):
        phone_case = {
            "title": "TORRAS Ostand phone case",
            "summary": "Integrated rotating stand.",
            "category": "手机壳",
        }
        charger = {
            "title": "Meet TORRAS Flexline 67W Retractable Charger",
            "summary": "A retractable GaN charger.",
            "category": "创意桌搭",
        }

        self.assertFalse(semantic_product_duplicate(phone_case, charger))

    def test_detects_same_product_worded_as_light_and_lighting(self):
        self.assertTrue(
            semantic_title_duplicate(
                "Red Dot Design Award: Bladeless Fan For Home Lighting",
                "Red Dot Design Award: Bladeless Fan Light",
            )
        )

    def test_detects_anker_nano_across_award_sites(self):
        self.assertTrue(
            semantic_title_duplicate(
                "iF Design - Anker Nano Power Bank (10K, 45W)",
                "Red Dot Design Award: Anker Nano Power Bank",
            )
        )

    def test_current_daily_group_blocks_historical_cross_site_product(self):
        common = {
            "category": "充电宝",
            "score": 82,
            "quality_score": 82,
            "innovation": 8,
            "relevance": 9,
            "review_confidence": 9,
            "review_policy_version": 3,
            "source_quality": "premium",
            "source_name": "iF Design",
            "source_family": "奖项案例",
            "action_lane": "适合改造",
            "summary": "品牌型号与功能证据明确",
            "first_seen": "2026-08-18",
        }
        duplicate = {
            **common,
            "id": "anker-if",
            "title": "iF Design - Anker Nano Power Bank (10K, 45W)",
            "url": "https://ifdesign.com/anker-nano",
        }
        unique = {
            **common,
            "id": "unique-power",
            "title": "Orbit emergency crank power bank",
            "url": "https://example.com/orbit-power-bank",
        }
        previous = [{
            "date": "2026-08-17",
            "items": [{
                "title": "Red Dot Design Award: Anker Nano Power Bank",
                "category": "充电宝",
                "url": "https://red-dot.org/anker-nano",
            }],
        }]

        groups = build_daily_groups(
            [duplicate, unique],
            per_day=2,
            max_days=1,
            previous_groups=previous,
            current_date="2026-08-18",
        )

        self.assertEqual([item["id"] for item in groups[0]["items"]], ["unique-power"])

    def test_does_not_merge_distinct_bottle_names(self):
        self.assertFalse(
            semantic_title_duplicate(
                "Red Dot Design Award: Vacuum Bottles",
                "Red Dot Design Award: MyBottle",
            )
        )

    def test_backlog_recheck_keeps_high_quality_innovation_item(self):
        item = {
            "title": "A modular light",
            "url": "https://example.com/product/modular-light",
            "category": "氛围灯",
            "review_policy_version": 3,
            "review_source": "deepseek_backlog_recheck",
            "review_reason": "模块可重新组合，结构创新明确",
            "quality_score": 74,
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
