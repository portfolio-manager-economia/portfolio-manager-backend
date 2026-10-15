"""Pruebas unitarias para las métricas estadísticas y financieras.

Verificación matemática rigurosa contra cálculo analítico de dos activos y casos de borde.
"""

import numpy as np
import pandas as pd
import pytest

from backend.finance.metrics import (
    calculate_expected_returns,
    calculate_covariance_matrix,
    calculate_portfolio_performance,
    calculate_sharpe_ratio,
)


def test_portfolio_performance_analytical_two_assets():
    """Verifica que la varianza de la cartera calculada matricialmente coincida

    exactamente con la fórmula cerrada analítica de 2 activos:
    sigma_p^2 = w1^2 * sigma1^2 + w2^2 * sigma2^2 + 2 * w1 * w2 * cov_12
    """
    w1, w2 = 0.6, 0.4
    weights = np.array([w1, w2])

    mu1, mu2 = 0.15, 0.10  # 15% y 10%
    expected_returns = np.array([mu1, mu2])

    var1 = 0.04   # desvío 20%
    var2 = 0.09   # desvío 30%
    cov12 = 0.015 # covarianza positiva
    cov_matrix = np.array([
        [var1, cov12],
        [cov12, var2]
    ])

    ret_calc, vol_calc = calculate_portfolio_performance(weights, expected_returns, cov_matrix)

    # Cálculo analítico manual
    expected_ret_manual = w1 * mu1 + w2 * mu2
    expected_var_manual = (w1 ** 2) * var1 + (w2 ** 2) * var2 + 2 * w1 * w2 * cov12
    expected_vol_manual = np.sqrt(expected_var_manual)

    assert np.isclose(ret_calc, expected_ret_manual, atol=1e-12)
    assert np.isclose(vol_calc, expected_vol_manual, atol=1e-12)


def test_annualization_factors():
    """Verifica la anualización con k=252 (acciones) vs k=365 (crypto)."""
    # 5 días de retornos
    daily_returns = pd.DataFrame({
        "STOCK": [0.01, -0.005, 0.008, -0.002, 0.012],
        "CRYPTO": [0.03, -0.02, 0.04, -0.01, 0.025],
    })

    mu_daily = daily_returns.mean()
    cov_daily = daily_returns.cov()

    # Anualización para acciones (k=252)
    mu_trad = calculate_expected_returns(daily_returns, annualization_factor=252)
    cov_trad = calculate_covariance_matrix(daily_returns, annualization_factor=252)
    assert np.isclose(mu_trad["STOCK"], mu_daily["STOCK"] * 252)
    assert np.isclose(cov_trad.loc["STOCK", "STOCK"], cov_daily.loc["STOCK", "STOCK"] * 252)

    # Anualización para crypto (k=365)
    mu_crypto = calculate_expected_returns(daily_returns, annualization_factor=365)
    cov_crypto = calculate_covariance_matrix(daily_returns, annualization_factor=365)
    assert np.isclose(mu_crypto["CRYPTO"], mu_daily["CRYPTO"] * 365)
    assert np.isclose(cov_crypto.loc["CRYPTO", "CRYPTO"], cov_daily.loc["CRYPTO", "CRYPTO"] * 365)


def test_sharpe_ratio():
    """Verifica el cálculo del ratio de Sharpe: S = (mu_p - r_f) / sigma_p."""
    ret = 0.18
    vol = 0.12
    rf = 0.04
    sharpe = calculate_sharpe_ratio(ret, vol, risk_free_rate=rf)

    expected_sharpe = (0.18 - 0.04) / 0.12
    assert np.isclose(sharpe, expected_sharpe, atol=1e-12)


def test_weights_sum_validation():
    """Valida que si los pesos no suman 1 se lance ValueError."""
    weights = np.array([0.5, 0.3]) # suma 0.8
    mu = np.array([0.1, 0.1])
    cov = np.eye(2) * 0.04

    with pytest.raises(ValueError, match="deben sumar 1.0"):
        calculate_portfolio_performance(weights, mu, cov)


def test_zero_variance_raises():
    """Valida que un activo con precios constantes (varianza cero) sea detectado."""
    constant_returns = pd.DataFrame({
        "ACTIVO_A": [0.0, 0.0, 0.0, 0.0],
        "ACTIVO_B": [0.01, -0.01, 0.02, -0.02]
    })
    with pytest.raises(ValueError, match="varianza nula o negativa"):
        calculate_covariance_matrix(constant_returns)

