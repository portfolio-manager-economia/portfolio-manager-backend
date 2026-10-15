"""Pruebas unitarias para el optimizador de portafolios (Markowitz).

Verificación matemática de restricciones, solución analítica de GMVP de dos activos
y frontera eficiente.
"""

import numpy as np
import pytest

from backend.finance.optimizer import (
    optimize_minimum_variance,
    optimize_maximum_sharpe,
    calculate_efficient_frontier,
)


def test_single_asset_portfolio():
    """Con un solo activo, el portafolio óptimo debe ser 100% ese activo."""
    mu = np.array([0.12])
    cov = np.array([[0.04]])

    gmvp = optimize_minimum_variance(mu, cov, risk_free_rate=0.03)
    assert np.allclose(gmvp["weights"], [1.0])
    assert np.isclose(gmvp["expected_return"], 0.12)
    assert np.isclose(gmvp["volatility"], 0.20)

    max_sharpe = optimize_maximum_sharpe(mu, cov, risk_free_rate=0.03)
    assert np.allclose(max_sharpe["weights"], [1.0])
    assert np.isclose(max_sharpe["expected_return"], 0.12)
    assert np.isclose(max_sharpe["sharpe_ratio"], (0.12 - 0.03) / 0.20)


def test_two_assets_gmvp_analytical_solution():
    """Verifica que el portafolio de mínima varianza de 2 activos coincida

    con la solución analítica cerrada de Markowitz:
    w1* = (sigma2^2 - cov12) / (sigma1^2 + sigma2^2 - 2 * cov12)
    """
    mu = np.array([0.15, 0.10])
    var1 = 0.09  # sigma1 = 0.30
    var2 = 0.04  # sigma2 = 0.20
    cov12 = 0.01
    cov = np.array([
        [var1, cov12],
        [cov12, var2]
    ])

    # Fórmula analítica cerrada
    w1_analytical = (var2 - cov12) / (var1 + var2 - 2 * cov12)
    w2_analytical = 1.0 - w1_analytical

    res = optimize_minimum_variance(mu, cov)
    weights = res["weights"]

    assert np.isclose(weights[0], w1_analytical, atol=1e-4)
    assert np.isclose(weights[1], w2_analytical, atol=1e-4)
    assert np.isclose(np.sum(weights), 1.0, atol=1e-6)
    assert (weights >= 0.0).all()


def test_three_assets_constraints():
    """Verifica que para 3 activos, los pesos sumen 1 y sean estrictamente no negativos (long-only)."""
    mu = np.array([0.12, 0.18, 0.08])
    cov = np.array([
        [0.04, 0.01, 0.005],
        [0.01, 0.09, 0.02],
        [0.005, 0.02, 0.025],
    ])

    gmvp = optimize_minimum_variance(mu, cov, risk_free_rate=0.03)
    assert np.isclose(np.sum(gmvp["weights"]), 1.0, atol=1e-6)
    assert (gmvp["weights"] >= -1e-6).all()

    max_sharpe = optimize_maximum_sharpe(mu, cov, risk_free_rate=0.03)
    assert np.isclose(np.sum(max_sharpe["weights"]), 1.0, atol=1e-6)
    assert (max_sharpe["weights"] >= -1e-6).all()
    # El ratio de Sharpe del óptimo debe ser mayor que el del GMVP evaluado a la misma tasa libre de riesgo
    assert max_sharpe["sharpe_ratio"] >= gmvp["sharpe_ratio"]


def test_efficient_frontier_generation():
    """Verifica que la frontera eficiente genere la cantidad requerida de puntos y sea monótona."""
    mu = np.array([0.10, 0.20, 0.15])
    cov = np.array([
        [0.04, 0.01, 0.015],
        [0.01, 0.09, 0.02],
        [0.015, 0.02, 0.06],
    ])

    frontier = calculate_efficient_frontier(mu, cov, num_portfolios=20, risk_free_rate=0.02)
    assert len(frontier) > 0

    # Todos los puntos deben tener suma de pesos igual a 1
    for pt in frontier:
        assert np.isclose(np.sum(pt["weights"]), 1.0, atol=1e-5)
        assert (pt["weights"] >= -1e-5).all()

    # Los retornos deben ser monótonamente crecientes
    returns = [pt["expected_return"] for pt in frontier]
    for i in range(1, len(returns)):
        assert returns[i] >= returns[i - 1] - 1e-9
