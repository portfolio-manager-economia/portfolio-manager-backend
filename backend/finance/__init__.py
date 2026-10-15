"""Núcleo financiero de Portfolio Manager: cálculo puro de retornos, métricas y optimización."""

from .returns import calculate_log_returns, align_price_series
from .metrics import (
    calculate_expected_returns,
    calculate_covariance_matrix,
    calculate_portfolio_performance,
    calculate_sharpe_ratio,
)
from .optimizer import (
    optimize_minimum_variance,
    optimize_maximum_sharpe,
    calculate_efficient_frontier,
)

__all__ = [
    "calculate_log_returns",
    "align_price_series",
    "calculate_expected_returns",
    "calculate_covariance_matrix",
    "calculate_portfolio_performance",
    "calculate_sharpe_ratio",
    "optimize_minimum_variance",
    "optimize_maximum_sharpe",
    "calculate_efficient_frontier",
]

