"""Persistencia idempotente de precios y señales en PostgreSQL."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg2
from dotenv import dotenv_values


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS historical_prices (
    ticker TEXT NOT NULL,
    price_date DATE NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC NOT NULL,
    volume BIGINT,
    PRIMARY KEY (ticker, price_date)
);

CREATE TABLE IF NOT EXISTS market_signals (
    ticker TEXT NOT NULL,
    signal_date DATE NOT NULL,
    close NUMERIC NOT NULL,
    moving_average NUMERIC,
    rolling_std NUMERIC,
    z_score NUMERIC,
    signal TEXT NOT NULL,
    PRIMARY KEY (ticker, signal_date),
    FOREIGN KEY (ticker, signal_date)
        REFERENCES historical_prices (ticker, price_date)
        ON DELETE CASCADE
);
"""

UPSERT_PRICES_SQL = """
INSERT INTO historical_prices (ticker, price_date, open, high, low, close, volume)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (ticker, price_date) DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    volume = EXCLUDED.volume;
"""

UPSERT_SIGNALS_SQL = """
INSERT INTO market_signals
    (ticker, signal_date, close, moving_average, rolling_std, z_score, signal)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (ticker, signal_date) DO UPDATE SET
    close = EXCLUDED.close,
    moving_average = EXCLUDED.moving_average,
    rolling_std = EXCLUDED.rolling_std,
    z_score = EXCLUDED.z_score,
    signal = EXCLUDED.signal;
"""


def database_config_from_env() -> dict[str, Any]:
    """Lee la configuración PostgreSQL solo del .env de este subproyecto."""
    values = dotenv_values(ENV_FILE)
    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    missing = [name for name in required if not values.get(name)]
    if missing:
        raise ValueError(f"Faltan variables de entorno: {', '.join(missing)}.")

    try:
        port = int(values.get("POSTGRES_PORT") or "5432")
    except ValueError as exc:
        raise ValueError("POSTGRES_PORT debe ser un número entero.") from exc
    if not 1 <= port <= 65535:
        raise ValueError("POSTGRES_PORT debe estar entre 1 y 65535.")

    return {
        "host": values.get("POSTGRES_HOST") or "localhost",
        "port": port,
        "dbname": values["POSTGRES_DB"],
        "user": values["POSTGRES_USER"],
        "password": values["POSTGRES_PASSWORD"],
    }


def _as_db_value(value: object) -> object:
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if hasattr(value, "item"):
        return value.item()
    return value


def _price_rows(ticker: str, prices: pd.DataFrame) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for date, row in prices.iterrows():
        rows.append(
            (
                ticker,
                pd.Timestamp(date).date(),
                *(_as_db_value(row.get(column)) for column in ("Open", "High", "Low")),
                _as_db_value(row["Close"]),
                _as_db_value(row.get("Volume")),
            )
        )
    return rows


def _signal_rows(signals: pd.DataFrame) -> list[tuple[object, ...]]:
    return [
        (
            row.ticker,
            pd.Timestamp(row.date).date(),
            _as_db_value(row.close),
            _as_db_value(row.moving_average),
            _as_db_value(row.rolling_std),
            _as_db_value(row.z_score),
            row.signal,
        )
        for row in signals.itertuples(index=False)
    ]


def load_data(
    ticker: str,
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    config: Mapping[str, Any],
) -> tuple[int, int]:
    """Crea las tablas y actualiza precios/señales dentro de una transacción."""
    if prices.empty or signals.empty:
        raise ValueError("No se cargan DataFrames vacíos.")

    price_rows = _price_rows(ticker.strip().upper(), prices)
    signal_rows = _signal_rows(signals)
    connection = psycopg2.connect(**config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLES_SQL)
            cursor.executemany(UPSERT_PRICES_SQL, price_rows)
            cursor.executemany(UPSERT_SIGNALS_SQL, signal_rows)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return len(price_rows), len(signal_rows)
