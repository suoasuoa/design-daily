import datetime as dt
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from company_multimodal_review import normalize_review
from local_dual_model_update import phase_target


class CompanyMultimodalReviewTests(unittest.TestCase):
    def test_normalizes_zero_to_one_scores(self):
        item = {"id": "lamp-1", "image": "https://example.com/lamp.jpg"}
        row = {
            "id": "lamp-1",
            "keep": True,
            "category": "氛围灯",
            "confidence": 0.9,
            "relevance": 0.9,
            "utility": 0.8,
            "frequency": 0.7,
            "broad_appeal": 0.8,
            "functionality": 0.8,
            "innovation": 0.9,
            "price_power": 0.8,
            "clarity": 0.9,
            "emotion": 0.8,
            "image_status": "loaded",
            "product_visible": True,
            "title_image_match": 0.9,
            "visual_evidence": "A folding lamp is visible.",
            "reason": "The folding structure changes both form and light distribution.",
        }

        result = normalize_review(item, row)

        self.assertTrue(result["keep"])
        self.assertEqual(result["confidence"], 9)
        self.assertEqual(result["innovation"], 9)
        self.assertEqual(result["title_image_match"], 9)

    def test_rejects_loaded_mismatched_image(self):
        item = {"id": "lamp-2", "image": "https://example.com/building.jpg"}
        row = {
            "id": "lamp-2",
            "keep": True,
            "category": "氛围灯",
            "confidence": 9,
            "relevance": 9,
            "utility": 8,
            "frequency": 8,
            "broad_appeal": 8,
            "functionality": 8,
            "innovation": 9,
            "price_power": 8,
            "clarity": 8,
            "emotion": 8,
            "image_status": "loaded",
            "product_visible": False,
            "title_image_match": 2,
            "visual_evidence": "Only a building is visible.",
            "reason": "The image does not show the claimed lamp.",
        }

        self.assertFalse(normalize_review(item, row)["keep"])

    def test_phase_targets(self):
        self.assertEqual(phase_target(dt.datetime(2026, 7, 20, 8, 45)), 15)
        self.assertEqual(phase_target(dt.datetime(2026, 7, 20, 12, 45)), 30)
        self.assertEqual(phase_target(dt.datetime(2026, 7, 20, 16, 15)), 40)


if __name__ == "__main__":
    unittest.main()
