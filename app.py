"""Dashboard Streamlit para precios y señales del pipeline financiero."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import psycopg2
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard_data import fetch_ticker_history, fetch_tickers
from src.analysis import build_strategy_analysis
from src.load import database_config_from_env


st.set_page_config(page_title="Market Signals", page_icon="📈", layout="wide")


def _get_signal_label(z_score: float | None, threshold: float) -> tuple[str, str]:
    if z_score is None or pd.isna(z_score):
        return "⚪ DATOS INSUFICIENTES", "Aún no hay una desviación estándar válida para comparar."
    if z_score <= -threshold:
        return "🟢 OPORTUNIDAD DE COMPRA (Oversold)", "El precio está por debajo del umbral estadístico configurado."
    if z_score >= threshold:
        return "🔴 ALERTA DE VENTA / SOBRECOMPRA (Overbought)", "El precio está por encima del umbral estadístico configurado."
    return "⚪ NEUTRAL / Esperar", "El Z-Score está dentro del rango configurado."


def _build_price_figure(history: pd.DataFrame, ticker: str) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=history["date"],
            y=history["close"],
            mode="lines",
            name="Precio de cierre ajustado",
            line={"color": "#2563eb", "width": 2},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=history["date"],
            y=history["moving_average"],
            mode="lines",
            name="Media móvil",
            line={"color": "#f59e0b", "width": 2, "dash": "dash"},
        )
    )
    figure.update_layout(
        title=f"{ticker}: precio de cierre vs. media móvil",
        xaxis_title="Fecha",
        yaxis_title="Precio ajustado",
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.12},
        margin={"t": 75, "b": 25},
    )
    return figure


def _build_zscore_figure(history: pd.DataFrame, ticker: str, threshold: float) -> go.Figure:
    figure = go.Figure(
        go.Bar(
            x=history["date"],
            y=history["z_score"],
            name="Z-Score",
            marker_color=[
                "#16a34a" if value <= -threshold else "#dc2626" if value >= threshold else "#64748b"
                for value in history["z_score"]
            ],
        )
    )
    figure.add_hline(
        y=threshold,
        line_dash="dash",
        line_color="#dc2626",
        annotation_text=f"+{threshold:g}",
    )
    figure.add_hline(
        y=-threshold,
        line_dash="dash",
        line_color="#16a34a",
        annotation_text=f"-{threshold:g}",
    )
    figure.add_hline(y=0, line_color="#94a3b8", line_width=1)
    figure.update_layout(
        title=f"{ticker}: evolución del Z-Score",
        xaxis_title="Fecha",
        yaxis_title="Z-Score",
        showlegend=False,
        margin={"t": 65, "b": 25},
    )
    return figure


def main() -> None:
    st.title("📈 Dashboard de análisis cuantitativo")
    st.caption("Históricos y señales calculados por el pipeline ETL.")

    try:
        config = database_config_from_env()
        tickers = fetch_tickers(config)
    except (ValueError, psycopg2.Error) as exc:
        st.error(
            "No pude conectar con PostgreSQL. Confirma que Docker Desktop esté activo, "
            "que el contenedor esté saludable y que el `.env` de `proyecto_financiero` "
            f"tenga la configuración correcta. Detalle: {exc}"
        )
        st.info(
            "En DBeaver, conéctate a la base `financial_market` en `localhost:5432` "
            "con el usuario `market_user`."
        )
        return

    if not tickers:
        st.warning("La base está conectada, pero aún no hay tickers guardados.")
        st.code("py -m src.main --tickers SPY --period 6mo --window 20 --threshold 2", language="powershell")
        return

    with st.sidebar:
        st.header("Panel de control")
        ticker = st.selectbox("Ticker", tickers)
        threshold = st.slider(
            "Umbral del Z-Score",
            min_value=0.5,
            max_value=4.0,
            value=2.0,
            step=0.1,
            help="El umbral se aplica a la etiqueta y a las líneas del gráfico.",
        )

    try:
        history = fetch_ticker_history(config, ticker)
    except (ValueError, psycopg2.Error) as exc:
        st.error(f"No pude cargar el histórico de {ticker}. Detalle: {exc}")
        return

    if history.empty:
        st.warning(f"No hay históricos disponibles para {ticker}.")
        return

    latest_price = history.iloc[-1]
    current_z_score = latest_price["z_score"]
    if pd.isna(current_z_score):
        current_z_score = None
    signal_label, signal_description = _get_signal_label(current_z_score, threshold)

    price_column, zscore_column = st.columns(2)
    price_column.metric(
        "Precio de cierre más reciente",
        f"{latest_price['close']:,.2f}",
        help=f"Fecha: {latest_price['date']:%Y-%m-%d}; cierre ajustado.",
    )
    zscore_column.metric(
        "Z-Score más reciente",
        f"{current_z_score:.2f}" if current_z_score is not None else "N/D",
    )
    st.subheader(signal_label)
    st.write(signal_description)

    price_chart, zscore_chart = st.columns(2)
    with price_chart:
        st.plotly_chart(_build_price_figure(history, ticker), width="stretch")
    with zscore_chart:
        st.plotly_chart(_build_zscore_figure(history, ticker, threshold), width="stretch")

    st.markdown("---")
    st.subheader("💡 Análisis de estrategia y contexto")
    moving_average = latest_price["moving_average"]
    if pd.isna(moving_average):
        moving_average = None
    category, analysis_title, analysis_text = build_strategy_analysis(
        ticker=ticker,
        close=float(latest_price["close"]),
        moving_average=float(moving_average) if moving_average is not None else None,
        z_score=float(current_z_score) if current_z_score is not None else None,
        threshold=threshold,
    )
    message = f"**{analysis_title}**\n\n{analysis_text}"
    if category == "oversold":
        st.success(message)
    elif category == "overbought":
        st.error(message)
    elif category == "warning":
        st.warning(message)
    else:
        st.info(message)

    st.caption(
        f"Histórico: {history['date'].min():%Y-%m-%d} a {history['date'].max():%Y-%m-%d} "
        f"({len(history)} sesiones). Las señales son estadísticas educativas, no recomendaciones "
        "ni garantías de rendimiento."
    )


if __name__ == "__main__":
    main()
