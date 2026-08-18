from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InsightOffPeakWorkflowTests(unittest.TestCase):
    def test_schedules_stay_inside_deepseek_windows(self):
        workflow = (ROOT / ".github/workflows/insight-pool.yml").read_text(encoding="utf-8")
        for cron in (
            'cron: "30 16 * * 0-4"',
            'cron: "30 20 * * 0-4"',
            'cron: "0 23 * * 0-4"',
            'cron: "5 4 * * 1-5"',
        ):
            self.assertIn(cron, workflow)
        self.assertNotIn('cron: "30 3 * * 1-5"', workflow)
        self.assertNotIn('cron: "30 7 * * 1-5"', workflow)
        self.assertIn('DEEPSEEK_ALLOWED_WINDOWS: "00:00-08:59,12:01-13:59,18:01-23:59"', workflow)
        self.assertIn('DEEPSEEK_DAILY_MAX_CALLS: "0"', workflow)
        self.assertIn('echo "AGENT_QUERIES=140"', workflow)
        self.assertIn('echo "AGENT_PAGES=650"', workflow)
        self.assertIn("DEEPSEEK_ALLOW_OUTSIDE_WINDOW:", workflow)
        self.assertNotIn('cron: "10 10 * * 1-5"', workflow)

    def test_incomplete_days_are_reported_as_failures(self):
        workflow = (ROOT / ".github/workflows/insight-pool.yml").read_text(encoding="utf-8")
        self.assertIn("- name: Verify daily target", workflow)
        self.assertIn('raise SystemExit(f"Daily target incomplete: {report}")', workflow)

    def test_checks_only_fill_real_deficits(self):
        workflow = (ROOT / ".github/workflows/insight-pool.yml").read_text(encoding="utf-8")
        self.assertIn("elif event_name == \"schedule\":", workflow)
        self.assertIn('echo "TOPUP_AGENT_QUERIES=${{ github.event.inputs.agent_queries', workflow)
        self.assertIn('echo "TOPUP_AGENT_PAGES=${{ github.event.inputs.agent_pages', workflow)
        self.assertNotIn("scheduled_quality_refresh", workflow)
        self.assertNotIn("refresh_args", workflow)
        self.assertNotIn("python3 scripts/score.py", workflow)


if __name__ == "__main__":
    unittest.main()
