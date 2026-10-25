"""Extracción de históricos ajustados desde Yahoo Finance."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import yfinance as yf


PRICE_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


def download_history(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Descarga datos históricos ajustados y valida la respuesta de yfinance."""
    normalized_ticker = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z0-9.^=_-]{1,20}", normalized_ticker):
        raise ValueError("ticker contiene caracteres inválidos.")
    if not period.strip():
        raise ValueError("period no puede estar vacío.")

    history = yf.download(
        normalized_ticker,
        period=period.strip(),
        auto_adjust=True,
        progress=False,
        threads=False,
        multi_level_index=False,
    )
    if history.empty:
        raise ValueError(f"yfinance no devolvió datos para {normalized_ticker}.")

    missing = set(PRICE_COLUMNS).difference(history.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas de precios: {', '.join(sorted(missing))}.")

    result = history.loc[:, PRICE_COLUMNS].copy()
    result.index = pd.to_datetime(result.index, errors="coerce")
    result.index.name = "date"
    result = result.apply(pd.to_numeric, errors="coerce")
    result = result.loc[~result.index.isna()].sort_index()
    result = result.loc[~result.index.duplicated(keep="last")]
    result = result.dropna(subset=["Close"])
    result = result.loc[np.isfinite(result["Close"]) & (result["Close"] > 0)]
    if result.empty:
        raise ValueError(f"yfinance no devolvió precios de cierre válidos para {normalized_ticker}.")

    return result
