import json
import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ensure_daily_minimum


class DailyTopupRoundTests(unittest.TestCase):
    def test_round_offset_continues_previous_scheduled_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            report_dir = data_dir / "reports"
            report_dir.mkdir(parents=True)
            report = report_dir / "deepseek-search-agent-2026-08-21.json"
            report.write_text(
                json.dumps({"rounds": [{"round": 1}, {"round": 2}, {"round": 3}]}),
                encoding="utf-8",
            )

            with patch.object(ensure_daily_minimum, "DATA_DIR", data_dir), patch.object(
                ensure_daily_minimum, "today", return_value="2026-08-21"
            ):
                self.assertEqual(ensure_daily_minimum.agent_round_offset(), 3)

    def test_round_offset_starts_at_zero_without_report(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            ensure_daily_minimum, "DATA_DIR", Path(directory)
        ), patch.object(ensure_daily_minimum, "today", return_value="2026-08-21"):
            self.assertEqual(ensure_daily_minimum.agent_round_offset(), 0)

    def test_each_round_caps_generic_query_growth(self):
        source = inspect.getsource(ensure_daily_minimum.main)
        self.assertIn("pass_queries = min(", source)
        self.assertIn("240,", source)
        self.assertIn("pass_pages = min(", source)
        self.assertIn("1400,", source)


if __name__ == "__main__":
    unittest.main()
