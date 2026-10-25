import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

from src.dashboard_data import fetch_ticker_history, fetch_tickers


class DashboardDataTests(unittest.TestCase):
    @patch("src.dashboard_data.psycopg2.connect")
    def test_fetches_tickers_and_closes_connection(self, connect):
        cursor = MagicMock()
        cursor.fetchall.return_value = [("AAPL",), ("SPY",)]
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection

        tickers = fetch_tickers({"dbname": "test"})

        self.assertEqual(tickers, ["AAPL", "SPY"])
        connection.close.assert_called_once_with()

    @patch("src.dashboard_data.psycopg2.connect")
    def test_fetches_ordered_ticker_history_and_closes_connection(self, connect):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(date(2025, 1, 1), 100, None, None, None, "insufficient_history")]
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection

        history = fetch_ticker_history({"dbname": "test"}, "spy")

        self.assertEqual(history.columns.tolist(), ["date", "close", "moving_average", "rolling_std", "z_score", "signal"])
        self.assertEqual(history.iloc[0]["close"], 100)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(history["date"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(history["close"]))
        self.assertEqual(cursor.execute.call_args.args[1], ("SPY",))
        connection.close.assert_called_once_with()

    def test_rejects_blank_ticker(self):
        with self.assertRaises(ValueError):
            fetch_ticker_history({}, " ")


if __name__ == "__main__":
    unittest.main()
