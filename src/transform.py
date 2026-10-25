"""Limpieza de precios y detección de anomalías con Z-Score móvil."""

from __future__ import annotations

import numpy as np
import pandas as pd


SIGNAL_COLUMNS = ("ticker", "date", "close", "moving_average", "rolling_std", "z_score", "signal")


def calculate_signals(
    ticker: str,
    prices: pd.DataFrame,
    window: int = 20,
    threshold: float = 2.0,
) -> pd.DataFrame:
    """Calcula señales usando únicamente las observaciones previas a cada fecha."""
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker no puede estar vacío.")
    if window < 2:
        raise ValueError("window debe ser al menos 2.")
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold debe ser un número finito mayor que cero.")
    if "Close" not in prices.columns:
        raise ValueError("prices debe incluir la columna 'Close'.")

    close = pd.to_numeric(prices["Close"], errors="coerce")
    dates = pd.to_datetime(prices.index, errors="coerce")
    cleaned = pd.DataFrame({"date": dates, "close": close.to_numpy()})
    cleaned = cleaned.dropna(subset=["date", "close"])
    cleaned = cleaned.loc[np.isfinite(cleaned["close"]) & (cleaned["close"] > 0)]
    cleaned = cleaned.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    if cleaned.empty:
        raise ValueError("No hay precios de cierre positivos y válidos para analizar.")

    prior_close = cleaned["close"].shift(1)
    rolling = prior_close.rolling(window=window, min_periods=window)
    cleaned["moving_average"] = rolling.mean()
    cleaned["rolling_std"] = rolling.std(ddof=1)
    standard_deviation = cleaned["rolling_std"].replace(0, np.nan)
    cleaned["z_score"] = (cleaned["close"] - cleaned["moving_average"]) / standard_deviation

    cleaned["signal"] = "normal"
    insufficient_history = cleaned["moving_average"].isna() | standard_deviation.isna()
    cleaned.loc[insufficient_history, "signal"] = "insufficient_history"
    cleaned.loc[cleaned["z_score"] <= -threshold, "signal"] = "oversold"
    cleaned.loc[cleaned["z_score"] >= threshold, "signal"] = "overbought"
    cleaned.insert(0, "ticker", normalized_ticker)
    return cleaned.loc[:, SIGNAL_COLUMNS]
