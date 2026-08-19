import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dedupe import build_pool


class CrossSourceDedupeTests(unittest.TestCase):
    def test_merges_gerber_compleat_from_two_sites(self):
        leads = [
            {
                "title": "Gerber Compleat Tool Set",
                "reason": "The ComplEAT tool set includes a fork and spoon.",
                "category": "创意厨具",
                "source": "Uncrate Shop",
                "url": "https://shop.example/gerber-compleat",
                "added": "2026-08-06",
            },
            {
                "title": "The Gerber ComplEAT puts an entire cutlery set into your pocket - Yanko Design",
                "reason": "Gerber ComplEAT 将完整厨房工具集成到口袋大小。",
                "category": "创意厨具",
                "source": "Yanko Design",
                "url": "https://editorial.example/gerber-compleat",
                "added": "2026-08-10",
            },
        ]

        products, _, _, entity_index = build_pool(leads)

        self.assertEqual(len(products), 1)
        product = next(iter(products.values()))
        self.assertEqual(product["seen_count"], 2)
        self.assertTrue(entity_index)
        self.assertEqual(len(set(entity_index.values())), 1)

    def test_torras_charger_does_not_merge_with_ostand_case(self):
        leads = [
            {
                "title": "TORRAS Ostand Case Adds a Magnetic Twist",
                "reason": "TORRAS Ostand手机壳，内置磁吸支架。",
                "category": "手机壳",
                "source": "Yanko Design",
                "url": "https://example.com/ostand",
            },
            {
                "title": "Meet TORRAS Flexline 67W Retractable Charger",
                "reason": "A retractable GaN charger.",
                "category": "创意桌搭",
                "source": "Yanko Design",
                "url": "https://example.com/flexline",
            },
        ]

        products, _, _, _ = build_pool(leads)

        self.assertEqual(len(products), 2)


if __name__ == "__main__":
    unittest.main()
