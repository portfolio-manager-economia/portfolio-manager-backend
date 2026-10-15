"""Gestión de datos de mercado con yfinance y almacenamiento en caché local.

Permite consultar precios históricos y cotizaciones actuales para acciones,
CEDEARs (sufijo .BA) y criptomonedas (ej: BTC-USD).
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import pandas as pd
import yfinance as yf


# Caché en memoria para evitar saturar las APIs de mercado
_PRICE_CACHE: Dict[str, pd.DataFrame] = {}


def fetch_historical_prices(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    use_cache: bool = True,
) -> pd.Series:
    """Descarga la serie histórica de precios de cierre ajustados de un activo.

    Parámetros:
        ticker: Símbolo del activo (ej: 'AAPL', 'GGAL.BA', 'BTC-USD').
        period: Rango temporal ('1mo', '3mo', '6mo', '1y', '2y', '5y').
        interval: Frecuencia de los datos ('1d', '1wk').
        use_cache: Si es True, reutiliza los datos si ya fueron consultados recientemente.

    Retorna:
        pd.Series con los precios de cierre y DatetimeIndex.

    Lanza:
        ValueError: Si el activo no existe o no tiene datos para el período solicitado.
    """
    cache_key = f"{ticker}_{period}_{interval}"
    if use_cache and cache_key in _PRICE_CACHE:
        return _PRICE_CACHE[cache_key]["Close"]

    clean_ticker = ticker.strip().upper()
    try:
        yf_ticker = yf.Ticker(clean_ticker)
        history = yf_ticker.history(period=period, interval=interval)
    except Exception as e:
        raise ValueError(f"Error al consultar cotizaciones para '{clean_ticker}': {str(e)}")

    if history is None or history.empty:
        raise ValueError(f"No se encontraron datos históricos para el ticker '{clean_ticker}'.")

    # Asegurar que la serie use el precio de cierre limpio
    history.index = pd.to_datetime(history.index).tz_localize(None)
    close_series = history["Close"].dropna()

    if close_series.empty:
        raise ValueError(f"La serie de precios de '{clean_ticker}' no contiene registros válidos.")

    if use_cache:
        _PRICE_CACHE[cache_key] = history

    return close_series


def fetch_multiple_tickers(
    tickers: List[str],
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Descarga y alinea las series de precios de múltiples tickers en un único DataFrame.

    Retorna:
        pd.DataFrame con columnas [ticker_1, ticker_2, ...] y fechas comunes.
    """
    series_map: Dict[str, pd.Series] = {}
    for ticker in tickers:
        clean = ticker.strip().upper()
        series_map[clean] = fetch_historical_prices(clean, period=period, interval=interval)

    # Alinear fechas comunes (intersección)
    df = pd.DataFrame(series_map).dropna()
    if df.empty:
        raise ValueError("No se encontraron fechas de cotización simultáneas para los activos solicitados.")
    return df


def get_current_price(ticker: str) -> float:
    """Obtiene el último precio de cotización disponible de un ticker."""
    series = fetch_historical_prices(ticker, period="5d", interval="1d")
    return float(series.iloc[-1])

