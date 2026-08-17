from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InsightOffPeakWorkflowTests(unittest.TestCase):
    def test_schedules_stay_inside_deepseek_windows(self):
        workflow = (ROOT / ".github/workflows/insight-pool.yml").read_text(encoding="utf-8")
        for cron in (
            'cron: "5 22 * * 0-4"',
            'cron: "35 23 * * 0-4"',
            'cron: "10 4 * * 1-5"',
            'cron: "10 5 * * 1-5"',
        ):
            self.assertIn(cron, workflow)
        self.assertNotIn('cron: "30 3 * * 1-5"', workflow)
        self.assertNotIn('cron: "30 7 * * 1-5"', workflow)
        self.assertIn('DEEPSEEK_ALLOWED_WINDOWS: "06:00-08:30,12:01-13:59"', workflow)
        self.assertIn('DEEPSEEK_DAILY_MAX_CALLS: "100"', workflow)

    def test_checks_only_fill_real_deficits(self):
        workflow = (ROOT / ".github/workflows/insight-pool.yml").read_text(encoding="utf-8")
        self.assertIn("elif event_name == \"schedule\":", workflow)
        self.assertNotIn("scheduled_quality_refresh", workflow)
        self.assertNotIn("refresh_args", workflow)
        self.assertNotIn("python3 scripts/score.py", workflow)


if __name__ == "__main__":
    unittest.main()
