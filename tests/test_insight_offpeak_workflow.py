from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InsightOffPeakWorkflowTests(unittest.TestCase):
    def test_schedules_stay_inside_deepseek_windows(self):
        workflow = (ROOT / ".github/workflows/insight-pool.yml").read_text(encoding="utf-8")
        for cron in (
            'cron: "10 16 * * 0-4"',
            'cron: "0 20 * * 0-4"',
            'cron: "10 23 * * 0-4"',
        ):
            self.assertIn(cron, workflow)
        self.assertEqual(workflow.count("- cron:"), 3)
        self.assertNotIn('cron: "5 4 * * 1-5"', workflow)
        self.assertNotIn('cron: "30 3 * * 1-5"', workflow)
        self.assertNotIn('cron: "30 7 * * 1-5"', workflow)
        self.assertIn('DEEPSEEK_ALLOWED_WINDOWS: "00:00-08:40"', workflow)
        self.assertNotIn("18:01-23:59", workflow)
        self.assertIn('DEEPSEEK_DAILY_MAX_CALLS: "0"', workflow)
        self.assertIn('DEEPSEEK_DAILY_MAX_TOKENS: "0"', workflow)
        self.assertIn('TOPUP_MAX_PASSES=7', workflow)
        self.assertIn('TOPUP_MAX_PASSES=6', workflow)
        self.assertIn('TOPUP_MAX_PASSES=2', workflow)
        self.assertIn('topup_passes:', workflow)
        self.assertIn("github.event.inputs.topup_passes || '4'", workflow)
        self.assertIn('echo "AGENT_QUERIES=180"', workflow)
        self.assertIn('echo "AGENT_PAGES=800"', workflow)
        self.assertIn('echo "TOPUP_AGENT_QUERIES=180"', workflow)
        self.assertIn('echo "TOPUP_AGENT_PAGES=800"', workflow)
        self.assertIn("Final overnight search-provider fallback", workflow)
        self.assertIn("github.event.schedule == '10 23 * * 0-4'", workflow)
        self.assertIn('USE_TAVILY_SEARCH: "1"', workflow)
        self.assertIn('--search-workers 3', workflow)
        self.assertIn('--curated-limit 180', workflow)
        self.assertIn('--shopify-pages 3', workflow)
        self.assertIn('DEEPSEEK_ALLOW_OUTSIDE_WINDOW: "0"', workflow)
        self.assertIn("ref: main", workflow)
        self.assertIn("Enforce daily quality gate", workflow)
        self.assertIn("python3 scripts/verify_daily_quality.py", workflow)
        self.assertNotIn("allow_peak:", workflow)
        self.assertNotIn('cron: "10 10 * * 1-5"', workflow)

    def test_backlog_only_mode_never_calls_deepseek(self):
        workflow = (ROOT / ".github/workflows/insight-pool.yml").read_text(encoding="utf-8")
        self.assertIn("backlog_only:", workflow)
        self.assertIn('echo "RUN_MODE=backlog"', workflow)
        self.assertIn("run_mode != \"backlog\" and", workflow)
        self.assertIn("Promote reviewed backlog without DeepSeek", workflow)
        self.assertIn("env.RUN_MODE != 'backlog'", workflow)

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
