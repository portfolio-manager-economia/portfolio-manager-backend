"""Métricas estadísticas y financieras de activos y portafolios.

Funciones puras para el cálculo de retornos esperados, matriz de covarianza,
desempeño de portafolios (retorno y volatilidad) y ratio de Sharpe.
"""

from typing import Tuple, Union
import numpy as np
import pandas as pd


def calculate_expected_returns(
    returns: pd.DataFrame,
    annualization_factor: int = 252,
) -> pd.Series:
    """Calcula el vector de retornos esperados anualizados.

    mu_anual = k * mu_diario

    Parámetros:
        returns: pd.DataFrame con los retornos periódicos de los activos.
        annualization_factor: Factor k de periodos por año (252 acciones/CEDEARs, 365 crypto).

    Retorna:
        pd.Series con el retorno esperado anualizado de cada activo.

    Lanza:
        ValueError: Si el DataFrame está vacío o tiene menos de 1 observación.
    """
    if returns is None or returns.empty:
        raise ValueError("El DataFrame de retornos no puede estar vacío.")

    if annualization_factor <= 0:
        raise ValueError("El factor de anualización debe ser un entero positivo.")

    # Retorno medio muestral anualizado
    return returns.mean() * annualization_factor


def calculate_covariance_matrix(
    returns: pd.DataFrame,
    annualization_factor: int = 252,
) -> pd.DataFrame:
    """Calcula la matriz de covarianza insesgada anualizada (N-1).

    Sigma_anual = k * Sigma_diario

    Parámetros:
        returns: pd.DataFrame con los retornos periódicos de los activos.
        annualization_factor: Factor k de periodos por año.

    Retorna:
        pd.DataFrame simétrico con la matriz de covarianza anualizada.

    Lanza:
        ValueError: Si el DataFrame está vacío o tiene menos de 2 observaciones.
    """
    if returns is None or returns.empty:
        raise ValueError("El DataFrame de retornos no puede estar vacío.")

    if len(returns) < 2:
        raise ValueError("Se requieren al menos 2 observaciones para calcular la covarianza muestral.")

    if annualization_factor <= 0:
        raise ValueError("El factor de anualización debe ser un entero positivo.")

    cov = returns.cov() * annualization_factor

    # Validar que ningún activo tenga varianza cero o nula
    variances = np.diag(cov.values)
    if (variances <= 0).any():
        raise ValueError("Uno o más activos presentan varianza nula o negativa (precios constantes).")

    return cov


def calculate_portfolio_performance(
    weights: Union[np.ndarray, list],
    expected_returns: Union[pd.Series, np.ndarray],
    cov_matrix: Union[pd.DataFrame, np.ndarray],
) -> Tuple[float, float]:
    """Calcula el retorno esperado y la volatilidad (desvío estándar) anualizada del portafolio.

    mu_p = w^T * mu
    sigma_p = sqrt(w^T * Sigma * w)

    Parámetros:
        weights: Vector de ponderaciones w de longitud n.
        expected_returns: Vector de retornos esperados anualizados de longitud n.
        cov_matrix: Matriz de covarianza anualizada (n x n).

    Retorna:
        Tupla (retorno_esperado, volatilidad).

    Lanza:
        ValueError: Si las dimensiones no coinciden o si los pesos no suman 1 (con tolerancia).
    """
    w = np.asarray(weights, dtype=float)
    mu = np.asarray(expected_returns, dtype=float)
    sigma = np.asarray(cov_matrix, dtype=float)

    n = len(w)
    if len(mu) != n:
        raise ValueError(
            f"La longitud de pesos ({n}) no coincide con la longitud de retornos esperados ({len(mu)})."
        )

    if sigma.shape != (n, n):
        raise ValueError(
            f"Las dimensiones de la matriz de covarianza ({sigma.shape}) no coinciden con el número de activos ({n})."
        )

    if not np.isclose(np.sum(w), 1.0, atol=1e-3):
        raise ValueError(f"Los pesos del portafolio deben sumar 1.0 (suma actual: {np.sum(w):.6f}).")

    port_return = float(np.dot(w, mu))
    port_variance = float(np.dot(w.T, np.dot(sigma, w)))

    # Asegurar no negatividad por posibles errores de redondeo de punto flotante
    port_volatility = float(np.sqrt(max(port_variance, 0.0)))

    return port_return, port_volatility


def calculate_sharpe_ratio(
    portfolio_return: float,
    portfolio_volatility: float,
    risk_free_rate: float = 0.0,
) -> float:
    """Calcula el ratio de Sharpe: S = (mu_p - r_f) / sigma_p.

    Parámetros:
        portfolio_return: Retorno esperado anualizado del portafolio.
        portfolio_volatility: Volatilidad anualizada del portafolio.
        risk_free_rate: Tasa libre de riesgo anualizada (r_f).

    Retorna:
        Ratio de Sharpe.

    Lanza:
        ValueError: Si la volatilidad es menor o igual a cero.
    """
    if portfolio_volatility <= 0:
        raise ValueError("La volatilidad debe ser estrictamente positiva para calcular el ratio de Sharpe.")

    return float((portfolio_return - risk_free_rate) / portfolio_volatility)

