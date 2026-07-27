import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from preference_profile import build_profile


def event(actor, product, action, created_at, reason="", category="氛围灯", axis="结构启发"):
    return {
        "actor_id": actor,
        "product_id": product,
        "action": action,
        "reason": reason,
        "created_at": created_at,
        "item_snapshot": {
            "title": product,
            "category": category,
            "source_family": "媒体案例",
            "action_lane": "适合改造",
            "axes": [axis],
            "tags": ["结构创新"],
        },
    }


class PreferenceProfileTests(unittest.TestCase):
    def test_latest_decision_replaces_previous_vote(self):
        profile = build_profile(
            [
                event("a", "lamp-1", "pass", "2026-07-27T08:00:00Z", "too_ordinary"),
                event("a", "lamp-1", "like", "2026-07-27T08:01:00Z"),
            ]
        )

        self.assertEqual(profile["stats"]["active_decisions"], 1)
        self.assertEqual(profile["stats"]["likes"], 1)
        self.assertEqual(profile["stats"]["passes"], 0)
        self.assertNotIn("lamp-1", profile["blocked_product_ids"])

    def test_team_pass_majority_blocks_exact_product(self):
        profile = build_profile(
            [
                event("a", "cup-1", "pass", "2026-07-27T08:00:00Z", "weak_function", "水杯"),
                event("b", "cup-1", "pass", "2026-07-27T08:01:00Z", "too_ordinary", "水杯"),
                event("c", "cup-1", "like", "2026-07-27T08:02:00Z", category="水杯"),
            ]
        )

        self.assertIn("cup-1", profile["blocked_product_ids"])
        self.assertEqual(profile["negative_patterns"]["category"][0]["name"], "水杯")


if __name__ == "__main__":
    unittest.main()
