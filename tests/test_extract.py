import unittest
from unittest.mock import patch

import pandas as pd

from src.extract import download_history


class DownloadHistoryTests(unittest.TestCase):
    @patch("src.extract.yf.download")
    def test_normalizes_ticker_and_download_options(self, download):
        index = pd.date_range("2025-01-01", periods=2)
        expected = pd.DataFrame(
            {
                "Open": [10, 11],
                "High": [12, 13],
                "Low": [9, 10],
                "Close": [11, 12],
                "Volume": [100, 120],
            },
            index=index,
        )
        download.return_value = expected

        actual = download_history(" spy ", period="3mo")

        self.assertEqual(actual.index.name, "date")
        self.assertEqual(actual.columns.tolist(), ["Open", "High", "Low", "Close", "Volume"])
        self.assertEqual(download.call_args.args, ("SPY",))
        self.assertEqual(download.call_args.kwargs["period"], "3mo")
        self.assertTrue(download.call_args.kwargs["auto_adjust"])
        self.assertFalse(download.call_args.kwargs["multi_level_index"])

    def test_rejects_invalid_ticker(self):
        with self.assertRaises(ValueError):
            download_history("SPY; DROP TABLE")

    @patch("src.extract.yf.download")
    def test_drops_missing_invalid_closes_and_duplicate_dates(self, download):
        index = pd.to_datetime(["2025-01-01", "2025-01-01", "2025-01-02", "2025-01-03"])
        download.return_value = pd.DataFrame(
            {
                "Open": [10, 11, 12, 13],
                "High": [12, 13, 14, 15],
                "Low": [9, 10, 11, 12],
                "Close": [10, 11, float("nan"), -1],
                "Volume": [100, 110, 120, 130],
            },
            index=index,
        )

        result = download_history("SPY")

        self.assertEqual(result.index.tolist(), [pd.Timestamp("2025-01-01")])
        self.assertEqual(result["Close"].tolist(), [11])


if __name__ == "__main__":
    unittest.main()
