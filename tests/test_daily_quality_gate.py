import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_daily_quality import verify_payload


def reviewed_item(item_id="product-1", quality=78, innovation=8, relevance=9):
    return {
        "id": item_id,
        "title": f"Modular product {item_id}",
        "url": f"https://example.com/product/{item_id}",
        "category": "创意厨具",
        "summary": "明确单品，通过模块结构解决高频使用问题",
        "quality_score": quality,
        "innovation": innovation,
        "relevance": relevance,
        "review_confidence": 8,
        "review_policy_version": 3,
        "source_quality": "standard",
        "source_name": "Design Media",
    }


class DailyQualityGateTests(unittest.TestCase):
    def test_accepts_strictly_reviewed_product(self):
        payload = {"daily_groups": [{"date": "2026-08-24", "items": [reviewed_item()]}]}
        self.assertEqual(verify_payload(payload, "2026-08-24"), [])

    def test_rejects_low_quality_product_even_when_count_is_needed(self):
        payload = {
            "daily_groups": [
                {"date": "2026-08-24", "items": [reviewed_item(quality=70)]},
            ]
        }
        errors = verify_payload(payload, "2026-08-24")
        self.assertTrue(any("quality gate failed" in error for error in errors))

    def test_rejects_historical_semantic_duplicate(self):
        current = reviewed_item("current")
        current["title"] = "Gerber Compleat Tool Set"
        old = reviewed_item("old")
        old["title"] = "The Gerber ComplEAT puts an entire cutlery set into your pocket"
        payload = {
            "daily_groups": [
                {"date": "2026-08-24", "items": [current]},
                {"date": "2026-08-21", "items": [old]},
            ]
        }
        errors = verify_payload(payload, "2026-08-24")
        self.assertTrue(any("historical duplicate" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
