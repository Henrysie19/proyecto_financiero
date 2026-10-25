"""Consultas de solo lectura para el dashboard de Streamlit."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import psycopg2


def fetch_tickers(config: Mapping[str, Any]) -> list[str]:
    """Devuelve los tickers con precios persistidos."""
    connection = psycopg2.connect(**config)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT ticker FROM historical_prices ORDER BY ticker;")
            return [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()


def fetch_ticker_history(config: Mapping[str, Any], ticker: str) -> pd.DataFrame:
    """Combina precios y señal asociada en orden cronológico."""
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker no puede estar vacío.")

    connection = psycopg2.connect(**config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    prices.price_date,
                    prices.close,
                    signals.moving_average,
                    signals.rolling_std,
                    signals.z_score,
                    signals.signal
                FROM historical_prices AS prices
                LEFT JOIN market_signals AS signals
                    ON signals.ticker = prices.ticker
                    AND signals.signal_date = prices.price_date
                WHERE prices.ticker = %s
                ORDER BY prices.price_date;
                """,
                (normalized_ticker,),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()

    history = pd.DataFrame(
        rows,
        columns=("date", "close", "moving_average", "rolling_std", "z_score", "signal"),
    )
    history["date"] = pd.to_datetime(history["date"])
    for column in ("close", "moving_average", "rolling_std", "z_score"):
        history[column] = pd.to_numeric(history[column], errors="coerce")
    return history
