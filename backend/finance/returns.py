"""Cálculo y procesamiento de retornos financieros.

Funciones puras para el cálculo de retornos logarítmicos, alineación de series temporales
y manejo estricto de casos de borde según la Teoría Moderna de Portafolios.
"""

from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd


def calculate_log_returns(
    prices: Union[pd.Series, pd.DataFrame]
) -> Union[pd.Series, pd.DataFrame]:
    """Calcula los retornos logarítmicos r_t = ln(P_t / P_{t-1}).

    Parámetros:
        prices: pd.Series o pd.DataFrame con precios históricos ordenados cronológicamente.

    Retorna:
        pd.Series o pd.DataFrame con los retornos logarítmicos, omitiendo el primer valor NaN.

    Lanza:
        ValueError: Si la serie está vacía, tiene menos de 2 observaciones o contiene valores <= 0.
    """
    if prices is None or prices.empty:
        raise ValueError("La serie o DataFrame de precios no puede estar vacía.")

    if len(prices) < 2:
        raise ValueError(
            "Se requieren al menos 2 observaciones consecutivas de precios para calcular retornos."
        )

    # Validar que no existan valores <= 0 ni nulos antes del logaritmo
    if (prices <= 0).any().any() if isinstance(prices, pd.DataFrame) else (prices <= 0).any():
        raise ValueError("Los precios deben ser estrictamente positivos para calcular retornos logarítmicos.")

    # r_t = ln(P_t / P_{t-1}) = ln(P_t) - ln(P_{t-1})
    log_returns = np.log(prices / prices.shift(1)).dropna()
    return log_returns


def align_price_series(
    series_dict: Dict[str, pd.Series],
    how: str = "inner",
) -> pd.DataFrame:
    """Alinea múltiples series de precios por fechas en común.

    Útil para carteras que combinan activos tradicionales (252 días hábiles) con crypto (365 días).

    Parámetros:
        series_dict: Diccionario {ticker: pd.Series de precios con DatetimeIndex}.
        how: Método de unión ('inner' por defecto para intersección de fechas comunes).

    Retorna:
        pd.DataFrame con columnas correspondientes a cada ticker y fechas alineadas sin NaNs.

    Lanza:
        ValueError: Si el diccionario está vacío o si la intersección no deja fechas comunes.
    """
    if not series_dict:
        raise ValueError("El diccionario de series no puede estar vacío.")

    df = pd.DataFrame(series_dict)
    if how == "inner":
        df = df.dropna()

    if df.empty:
        raise ValueError("No se encontraron fechas comunes entre las series proporcionadas.")

    return df

