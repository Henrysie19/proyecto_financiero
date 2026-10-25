"""Orquestador CLI del pipeline de extracción, transformación y carga."""

from __future__ import annotations

import argparse
import sys

import psycopg2

from .extract import download_history
from .load import database_config_from_env, load_data
from .transform import calculate_signals


def run_pipeline(tickers: list[str], period: str, window: int, threshold: float) -> None:
    config = database_config_from_env()

    for ticker in tickers:
        normalized_ticker = ticker.strip().upper()
        prices = download_history(normalized_ticker, period)
        signals = calculate_signals(normalized_ticker, prices, window, threshold)
        prices_written, signals_written = load_data(normalized_ticker, prices, signals, config)
        print(
            f"{normalized_ticker}: {prices_written} precios y "
            f"{signals_written} señales cargados/actualizados."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta el pipeline financiero ETL.")
    parser.add_argument("--tickers", nargs="+", default=["SPY"], help="Símbolos, por ejemplo SPY AAPL.")
    parser.add_argument("--period", default="6mo", help="Periodo admitido por yfinance (por defecto: 6mo).")
    parser.add_argument("--window", type=int, default=20, help="Ventana móvil en sesiones anteriores.")
    parser.add_argument("--threshold", type=float, default=2.0, help="Umbral absoluto del Z-Score.")
    args = parser.parse_args()

    try:
        run_pipeline(args.tickers, args.period, args.window, args.threshold)
    except (ValueError, psycopg2.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
