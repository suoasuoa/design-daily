from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FeishuWorkflowGuardTests(unittest.TestCase):
    def test_manual_push_never_lowers_daily_minimum(self):
        workflow = (ROOT / ".github/workflows/feishu-daily-push.yml").read_text()

        self.assertIn('MIN_COUNT="40"', workflow)
        self.assertNotIn('MIN_COUNT="1"', workflow)
        self.assertIn("--force-resend", workflow)

    def test_force_resend_is_explicitly_supported(self):
        script = (ROOT / "scripts/push_feishu_daily.py").read_text()

        self.assertIn('parser.add_argument("--force-resend"', script)
        self.assertIn("and not args.force_resend", script)


if __name__ == "__main__":
    unittest.main()
