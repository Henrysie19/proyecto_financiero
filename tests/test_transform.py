import unittest

import numpy as np
import pandas as pd

from src.transform import calculate_signals


class CalculateSignalsTests(unittest.TestCase):
    def test_uses_only_previous_sessions_and_detects_oversold_price(self):
        dates = pd.date_range("2025-01-01", periods=21, freq="B")
        closes = [99.0, 101.0] * 10 + [80.0]
        prices = pd.DataFrame({"Close": closes}, index=dates)

        result = calculate_signals("spy", prices, window=20, threshold=2)

        self.assertTrue((result.loc[:19, "signal"] == "insufficient_history").all())
        self.assertEqual(result.iloc[-1]["signal"], "oversold")
        self.assertEqual(result.iloc[-1]["moving_average"], 100.0)
        self.assertLess(result.iloc[-1]["z_score"], -2)

    def test_cleans_invalid_values_and_sorts_dates(self):
        dates = pd.to_datetime(["2025-01-03", "2025-01-01", "2025-01-02", "2025-01-04"])
        prices = pd.DataFrame({"Close": [103, 101, np.nan, -1]}, index=dates)

        result = calculate_signals("AAPL", prices, window=2)

        self.assertEqual(result["date"].tolist(), [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-03")])
        self.assertTrue((result["ticker"] == "AAPL").all())

    def test_rejects_invalid_window_threshold_and_missing_close(self):
        prices = pd.DataFrame({"Close": [10, 11]}, index=pd.date_range("2025-01-01", periods=2))

        with self.assertRaises(ValueError):
            calculate_signals("SPY", prices, window=1)
        with self.assertRaises(ValueError):
            calculate_signals("SPY", prices, threshold=0)
        with self.assertRaises(ValueError):
            calculate_signals("SPY", pd.DataFrame({"Open": [10]}))


if __name__ == "__main__":
    unittest.main()
