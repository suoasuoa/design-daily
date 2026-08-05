import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from push_feishu_daily import card_elements


class FeishuTextCardTests(unittest.TestCase):
    def test_card_does_not_emit_image_elements(self):
        item = {
            "title": "Creative product",
            "category": "创意厨具",
            "source_name": "Example",
            "url": "https://example.com/product",
            "image": "https://example.com/product.jpg",
            "_feishu_image_key": "img_v2_test",
            "score": 92,
        }

        elements = card_elements({"date": "2026-08-05"}, [item], 40)

        self.assertNotIn("img", [element.get("tag") for element in elements])
        body = "\n".join(
            element.get("text", {}).get("content", "")
            for element in elements
            if element.get("tag") == "div"
        )
        self.assertIn("Creative product", body)
        self.assertIn("92/100", body)
        self.assertIn("https://example.com/product", body)


if __name__ == "__main__":
    unittest.main()
