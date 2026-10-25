import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from src.load import database_config_from_env, load_data


class LoadDataTests(unittest.TestCase):
    def setUp(self):
        self.prices = pd.DataFrame(
            {
                "Open": [99.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [98.0, 100.0],
                "Close": [100.0, 102.0],
                "Volume": [1000, 1100],
            },
            index=pd.date_range("2025-01-01", periods=2),
        )
        self.signals = pd.DataFrame(
            {
                "ticker": ["SPY", "SPY"],
                "date": pd.date_range("2025-01-01", periods=2),
                "close": [100.0, 102.0],
                "moving_average": [np.nan, 100.0],
                "rolling_std": [np.nan, 1.0],
                "z_score": [np.nan, 2.0],
                "signal": ["insufficient_history", "overbought"],
            }
        )

    @patch("src.load.psycopg2.connect")
    def test_upserts_prices_and_signals_in_one_transaction(self, connect):
        cursor = MagicMock()
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection

        counts = load_data("spy", self.prices, self.signals, {"dbname": "test"})

        self.assertEqual(counts, (2, 2))
        self.assertEqual(cursor.executemany.call_count, 2)
        connection.commit.assert_called_once_with()
        connection.rollback.assert_not_called()
        connection.close.assert_called_once_with()
        price_rows = cursor.executemany.call_args_list[0].args[1]
        self.assertEqual(price_rows[0][0:2], ("SPY", pd.Timestamp("2025-01-01").date()))
        signal_rows = cursor.executemany.call_args_list[1].args[1]
        self.assertIsNone(signal_rows[0][3])
        self.assertIsNone(signal_rows[0][5])

    @patch("src.load.psycopg2.connect")
    def test_rolls_back_and_reraises_database_errors(self, connect):
        cursor = MagicMock()
        cursor.executemany.side_effect = RuntimeError("database failure")
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        connect.return_value = connection

        with self.assertRaisesRegex(RuntimeError, "database failure"):
            load_data("SPY", self.prices, self.signals, {"dbname": "test"})

        connection.rollback.assert_called_once_with()
        connection.close.assert_called_once_with()
        connection.commit.assert_not_called()

    @patch("src.load.dotenv_values", return_value={})
    def test_requires_database_credentials(self, dotenv_values):
        with self.assertRaisesRegex(ValueError, "POSTGRES_DB"):
            database_config_from_env()


if __name__ == "__main__":
    unittest.main()
