"""Interpretación educativa de señales cuantitativas para el dashboard."""

from __future__ import annotations

import math


def build_strategy_analysis(
    ticker: str,
    close: float,
    moving_average: float | None,
    z_score: float | None,
    threshold: float,
) -> tuple[str, str, str]:
    """Devuelve categoría, título y explicación sin prometer resultados futuros."""
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold debe ser un número finito mayor que cero.")

    if z_score is None or not math.isfinite(z_score):
        return (
            "warning",
            "Análisis no disponible todavía",
            f"{ticker}: el histórico aún no tiene una desviación estándar válida. "
            "Se necesita completar la ventana de observaciones antes de interpretar el Z-Score.",
        )

    if z_score <= -threshold:
        category = "oversold"
        title = "Posible sobreventa estadística"
        price_context = (
            f"El cierre de {close:,.2f} está por debajo de la media móvil "
            f"({moving_average:,.2f})"
            if moving_average is not None and math.isfinite(moving_average)
            else f"El cierre es {close:,.2f}"
        )
        interpretation = (
            f"{price_context} y el Z-Score es {z_score:.2f}, igual o menor que "
            f"-{threshold:g}. Esto describe una desviación respecto al período de referencia; "
            "por sí sola no confirma una oportunidad ni anticipa un rebote."
        )
    elif z_score >= threshold:
        category = "overbought"
        title = "Posible sobrecompra estadística"
        price_context = (
            f"El cierre de {close:,.2f} está por encima de la media móvil "
            f"({moving_average:,.2f})"
            if moving_average is not None and math.isfinite(moving_average)
            else f"El cierre es {close:,.2f}"
        )
        interpretation = (
            f"{price_context} y el Z-Score es {z_score:.2f}, igual o mayor que "
            f"+{threshold:g}. Esto describe una desviación respecto al período de referencia; "
            "por sí sola no predice una corrección ni indica que el precio vaya a caer."
        )
    else:
        category = "neutral"
        title = "Rango estadístico neutral"
        if moving_average is None or not math.isfinite(moving_average):
            interpretation = (
                f"El Z-Score de {z_score:.2f} está dentro del umbral ±{threshold:g}. "
                "No hay una media móvil válida para comparar el último cierre."
            )
        else:
            interpretation = (
                f"El cierre de {close:,.2f} está dentro del rango ±{threshold:g} "
                f"(Z-Score {z_score:.2f}) y la media móvil es {moving_average:,.2f}. "
                "La señal no muestra una desviación extrema según esta regla."
            )

    context = (
        "Lectura educativa, no recomendación personalizada. El Z-Score mide desviación "
        "histórica; no estima probabilidad de rebote o caída. Antes de decidir, considera "
        "horizonte, riesgo, costos y otros factores, y valida esta estrategia con pruebas "
        "históricas incluyendo costos y riesgo."
    )
    return category, title, f"{interpretation}\n\n{context}"
