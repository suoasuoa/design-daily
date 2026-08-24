import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import deepseek_search_agent


class SearchScreenLedgerTests(unittest.TestCase):
    def test_only_returned_decisions_are_remembered(self):
        rows = [
            {"id": "a", "url": "https://example.com/product/a"},
            {"id": "b", "url": "https://example.com/product/b"},
        ]
        with tempfile.TemporaryDirectory() as directory, patch.object(
            deepseek_search_agent, "DATA_DIR", Path(directory)
        ), patch.object(deepseek_search_agent, "today", return_value="2026-08-24"):
            size = deepseek_search_agent.remember_screened_candidates({"a"}, rows)
            keys = deepseek_search_agent.screened_candidate_keys()

        self.assertEqual(size, 1)
        self.assertEqual(keys, {deepseek_search_agent.candidate_screen_key(rows[0])})

    def test_ledger_resets_on_a_new_day(self):
        row = {"id": "a", "url": "https://example.com/product/a"}
        with tempfile.TemporaryDirectory() as directory, patch.object(
            deepseek_search_agent, "DATA_DIR", Path(directory)
        ):
            with patch.object(deepseek_search_agent, "today", return_value="2026-08-24"):
                deepseek_search_agent.remember_screened_candidates({"a"}, [row])
            with patch.object(deepseek_search_agent, "today", return_value="2026-08-25"):
                self.assertEqual(deepseek_search_agent.screened_candidate_keys(), set())


if __name__ == "__main__":
    unittest.main()
