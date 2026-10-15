"""Optimizador de portafolios según el modelo de media-varianza de Markowitz.

Funciones puras para:
1. Portafolio de Mínima Varianza Global (GMVP).
2. Portafolio de Máximo Sharpe (Portafolio de Tangencia).
3. Frontera Eficiente de Markowitz (barrido de retornos objetivo).
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .metrics import calculate_portfolio_performance, calculate_sharpe_ratio


def optimize_minimum_variance(
    expected_returns: Union[pd.Series, np.ndarray],
    cov_matrix: Union[pd.DataFrame, np.ndarray],
    risk_free_rate: float = 0.0,
    allow_short: bool = False,
) -> Dict[str, Any]:
    """Calcula el portafolio de Mínima Varianza Global (GMVP).

    Minimiza w^T * Sigma * w sujeto a sum(w) = 1 y (por defecto) w_i >= 0.

    Parámetros:
        expected_returns: Vector de retornos esperados anualizados.
        cov_matrix: Matriz de covarianza anualizada.
        risk_free_rate: Tasa libre de riesgo para calcular el Sharpe resultante.
        allow_short: Si es False, impone restricción long-only (0 <= w_i <= 1).

    Retorna:
        Dict con 'weights', 'expected_return', 'volatility', 'sharpe_ratio'.
    """
    mu = np.asarray(expected_returns, dtype=float)
    sigma = np.asarray(cov_matrix, dtype=float)
    n = len(mu)

    if n == 0:
        raise ValueError("El vector de retornos esperados no puede estar vacío.")

    # Caso especial de un solo activo
    if n == 1:
        weights = np.array([1.0])
        ret, vol = calculate_portfolio_performance(weights, mu, sigma)
        sharpe = calculate_sharpe_ratio(ret, vol, risk_free_rate) if vol > 0 else 0.0
        return {
            "weights": weights,
            "expected_return": ret,
            "volatility": vol,
            "sharpe_ratio": sharpe,
        }

    # Función objetivo: Varianza del portafolio w^T * Sigma * w
    def objective(w: np.ndarray) -> float:
        return float(np.dot(w.T, np.dot(sigma, w)))

    # Restricción: sum(w) = 1
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    # Límites: w_i in [0, 1] si no se permiten ventas en corto
    bounds = [(0.0, 1.0) for _ in range(n)] if not allow_short else [(-1.0, 1.0) for _ in range(n)]

    # Punto inicial: equiponderado
    initial_weights = np.ones(n) / n

    result = minimize(
        objective,
        initial_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-9, "maxiter": 500},
    )

    if not result.success:
        raise RuntimeError(f"La optimización de mínima varianza no convergió: {result.message}")

    optimal_weights = result.x
    # Normalizar para garantizar suma 1 exacta frente a errores de precisión numérica
    optimal_weights = optimal_weights / np.sum(optimal_weights)

    ret, vol = calculate_portfolio_performance(optimal_weights, mu, sigma)
    sharpe = calculate_sharpe_ratio(ret, vol, risk_free_rate) if vol > 0 else 0.0

    return {
        "weights": optimal_weights,
        "expected_return": ret,
        "volatility": vol,
        "sharpe_ratio": sharpe,
    }


def optimize_maximum_sharpe(
    expected_returns: Union[pd.Series, np.ndarray],
    cov_matrix: Union[pd.DataFrame, np.ndarray],
    risk_free_rate: float = 0.0,
    allow_short: bool = False,
) -> Dict[str, Any]:
    """Calcula el portafolio de Máximo Ratio de Sharpe (Portafolio de Tangencia).

    Maximiza (mu_p - r_f) / sigma_p, sujeto a sum(w) = 1 y w_i >= 0.

    Parámetros:
        expected_returns: Vector de retornos esperados anualizados.
        cov_matrix: Matriz de covarianza anualizada.
        risk_free_rate: Tasa libre de riesgo anualizada (r_f).
        allow_short: Si es False, impone restricción long-only (0 <= w_i <= 1).

    Retorna:
        Dict con 'weights', 'expected_return', 'volatility', 'sharpe_ratio'.
    """
    mu = np.asarray(expected_returns, dtype=float)
    sigma = np.asarray(cov_matrix, dtype=float)
    n = len(mu)

    if n == 0:
        raise ValueError("El vector de retornos esperados no puede estar vacío.")

    # Caso especial de un solo activo
    if n == 1:
        weights = np.array([1.0])
        ret, vol = calculate_portfolio_performance(weights, mu, sigma)
        sharpe = calculate_sharpe_ratio(ret, vol, risk_free_rate) if vol > 0 else 0.0
        return {
            "weights": weights,
            "expected_return": ret,
            "volatility": vol,
            "sharpe_ratio": sharpe,
        }

    # Función objetivo: Negativo del Ratio de Sharpe para minimizar
    def objective(w: np.ndarray) -> float:
        port_ret = np.dot(w, mu)
        port_var = np.dot(w.T, np.dot(sigma, w))
        port_vol = np.sqrt(max(port_var, 1e-12))
        return -float((port_ret - risk_free_rate) / port_vol)

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [(0.0, 1.0) for _ in range(n)] if not allow_short else [(-1.0, 1.0) for _ in range(n)]
    initial_weights = np.ones(n) / n

    result = minimize(
        objective,
        initial_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-9, "maxiter": 500},
    )

    if not result.success:
        raise RuntimeError(f"La optimización de máximo Sharpe no convergió: {result.message}")

    optimal_weights = result.x
    optimal_weights = optimal_weights / np.sum(optimal_weights)

    ret, vol = calculate_portfolio_performance(optimal_weights, mu, sigma)
    sharpe = calculate_sharpe_ratio(ret, vol, risk_free_rate) if vol > 0 else 0.0

    return {
        "weights": optimal_weights,
        "expected_return": ret,
        "volatility": vol,
        "sharpe_ratio": sharpe,
    }


def calculate_efficient_frontier(
    expected_returns: Union[pd.Series, np.ndarray],
    cov_matrix: Union[pd.DataFrame, np.ndarray],
    num_portfolios: int = 50,
    risk_free_rate: float = 0.0,
    allow_short: bool = False,
) -> List[Dict[str, Any]]:
    """Calcula los puntos que componen la Frontera Eficiente de Markowitz.

    Para una grilla de retornos objetivo entre el retorno de mínima varianza y
    el retorno máximo posible, minimiza la varianza para cada nivel.

    Parámetros:
        expected_returns: Vector de retornos esperados anualizados.
        cov_matrix: Matriz de covarianza anualizada.
        num_portfolios: Cantidad de puntos a evaluar en la curva.
        risk_free_rate: Tasa libre de riesgo para computar Sharpe.
        allow_short: Restricción de ventas en corto.

    Retorna:
        Lista de diccionarios con la composición y métricas de cada punto eficiente.
    """
    mu = np.asarray(expected_returns, dtype=float)
    sigma = np.asarray(cov_matrix, dtype=float)
    n = len(mu)

    if n < 2:
        # Con menos de 2 activos, la frontera es simplemente el punto individual
        single_opt = optimize_minimum_variance(mu, sigma, risk_free_rate, allow_short)
        return [single_opt]

    # 1. Encontrar el retorno mínimo viable (el del GMVP)
    gmvp = optimize_minimum_variance(mu, sigma, risk_free_rate, allow_short)
    min_ret = gmvp["expected_return"]
    max_ret = float(np.max(mu))

    # Si todos los activos tienen el mismo retorno
    if np.isclose(min_ret, max_ret):
        return [gmvp]

    target_returns = np.linspace(min_ret, max_ret, num_portfolios)
    frontier: List[Dict[str, Any]] = []

    bounds = [(0.0, 1.0) for _ in range(n)] if not allow_short else [(-1.0, 1.0) for _ in range(n)]
    initial_weights = np.ones(n) / n

    for target in target_returns:
        def objective(w: np.ndarray) -> float:
            return float(np.dot(w.T, np.dot(sigma, w)))

        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w, t=target: np.dot(w, mu) - t},
        ]

        res = minimize(
            objective,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 300},
        )

        if res.success:
            w_opt = res.x / np.sum(res.x)
            ret, vol = calculate_portfolio_performance(w_opt, mu, sigma)
            sharpe = calculate_sharpe_ratio(ret, vol, risk_free_rate) if vol > 0 else 0.0
            frontier.append({
                "weights": w_opt,
                "expected_return": ret,
                "volatility": vol,
                "sharpe_ratio": sharpe,
            })

    return frontier

