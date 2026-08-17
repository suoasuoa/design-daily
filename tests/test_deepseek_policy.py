import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from scripts.deepseek_policy import (
    DeepSeekBudgetExceeded,
    reserve_deepseek_call,
    window_status,
)


TZ = ZoneInfo("Asia/Shanghai")


class DeepSeekPolicyTests(unittest.TestCase):
    def test_only_configured_beijing_windows_are_open(self):
        self.assertTrue(window_status(dt.datetime(2026, 8, 17, 6, 0, tzinfo=TZ))["open"])
        self.assertTrue(window_status(dt.datetime(2026, 8, 17, 8, 27, tzinfo=TZ))["open"])
        self.assertFalse(window_status(dt.datetime(2026, 8, 17, 9, 0, tzinfo=TZ))["open"])
        self.assertTrue(window_status(dt.datetime(2026, 8, 17, 12, 1, tzinfo=TZ))["open"])
        self.assertFalse(window_status(dt.datetime(2026, 8, 17, 14, 0, tzinfo=TZ))["open"])

    def test_call_budget_is_hard_limited(self):
        with tempfile.TemporaryDirectory() as directory:
            usage_file = Path(directory) / "usage.json"
            env = {
                "DEEPSEEK_ALLOW_OUTSIDE_WINDOW": "1",
                "DEEPSEEK_MAX_CALLS": "2",
                "DEEPSEEK_USAGE_FILE": str(usage_file),
            }
            with patch.dict(os.environ, env, clear=False):
                reserve_deepseek_call("test")
                reserve_deepseek_call("test")
                with self.assertRaises(DeepSeekBudgetExceeded):
                    reserve_deepseek_call("test")
            payload = json.loads(usage_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["calls"], 2)


if __name__ == "__main__":
    unittest.main()
