"""Pruebas unitarias para el cálculo de retornos financieros.

Verificación matemática contra casos analíticos conocidos y casos de borde.
"""

import numpy as np
import pandas as pd
import pytest

from backend.finance.returns import calculate_log_returns, align_price_series


def test_calculate_log_returns_simple_value():
    """Verifica que el retorno logarítmico de 100 a 110 sea exactamente ln(1.10)."""
    prices = pd.Series([100.0, 110.0])
    returns = calculate_log_returns(prices)

    expected = np.log(110.0 / 100.0)
    assert len(returns) == 1
    assert np.isclose(returns.iloc[0], expected, atol=1e-12)


def test_calculate_log_returns_dataframe():
    """Verifica el cálculo matricial en un DataFrame con dos activos."""
    df_prices = pd.DataFrame({
        "AAPL": [150.0, 153.0, 156.06],
        "MSFT": [300.0, 303.0, 306.03],
    })
    returns = calculate_log_returns(df_prices)

    assert returns.shape == (2, 2)
    assert np.isclose(returns["AAPL"].iloc[0], np.log(153.0 / 150.0))
    assert np.isclose(returns["MSFT"].iloc[0], np.log(303.0 / 300.0))


def test_calculate_log_returns_empty_raises():
    """Valida que una serie vacía lance ValueError."""
    with pytest.raises(ValueError, match="no puede estar vacía"):
        calculate_log_returns(pd.Series([], dtype=float))


def test_calculate_log_returns_single_element_raises():
    """Valida que una serie con un solo elemento lance ValueError."""
    with pytest.raises(ValueError, match="al menos 2 observaciones"):
        calculate_log_returns(pd.Series([100.0]))


def test_calculate_log_returns_non_positive_price_raises():
    """Valida que precios menores o iguales a cero lancen ValueError."""
    with pytest.raises(ValueError, match="estrictamente positivos"):
        calculate_log_returns(pd.Series([100.0, 0.0, 105.0]))

    with pytest.raises(ValueError, match="estrictamente positivos"):
        calculate_log_returns(pd.Series([100.0, -5.0, 105.0]))


def test_align_price_series_inner_join():
    """Verifica la alineación de fechas de series desalineadas (tradicional vs crypto)."""
    dates_trad = pd.date_range("2024-01-01", periods=4, freq="B")  # Días hábiles
    dates_crypto = pd.date_range("2024-01-01", periods=6, freq="D")  # Todos los días

    s_trad = pd.Series([100.0, 101.0, 102.0, 103.0], index=dates_trad)
    s_crypto = pd.Series([50.0, 51.0, 52.0, 53.0, 54.0, 55.0], index=dates_crypto)

    aligned = align_price_series({"TRAD": s_trad, "CRYPTO": s_crypto})

    # Debe contener solo las fechas presentes en ambas series
    assert not aligned.isna().any().any()
    assert len(aligned) == len(dates_trad)
    assert list(aligned.columns) == ["TRAD", "CRYPTO"]

