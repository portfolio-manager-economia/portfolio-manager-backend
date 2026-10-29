"""Pure currency conversion and valuation, shared by tracking and comparison."""
import numpy as np
import pandas as pd


def convert_history_to_usd(prices: pd.DataFrame, currencies: dict[str, str],
                           mep: pd.Series | None = None) -> pd.DataFrame:
    result = prices.copy()
    for ticker in result:
        currency = currencies[ticker]
        if currency == "ARS":
            if mep is None:
                raise ValueError("Falta la serie histórica MEP para los activos en ARS.")
            # Exact historical dates only: never use today's FX or backfill future FX.
            result[ticker] = result[ticker] / mep.reindex(result.index)
        elif currency != "USD":
            raise ValueError(f"Moneda no soportada: {currency}.")
    result = result.dropna()
    if len(result) < 3 or not np.isfinite(result.to_numpy()).all() or (result <= 0).any().any():
        raise ValueError("No hay suficientes precios y tipos de cambio históricos válidos en común.")
    return result


def annualization_factor(tickers: list[str]) -> int:
    # Mixed portfolios use common trading sessions, including accumulated weekend crypto moves.
    return 365 if all(t.endswith("-USD") for t in tickers) else 252


def position_value(quantity: float, price: float, currency: str, fx: float,
                   asset_type: str) -> float:
    values = np.array([quantity, price, fx], dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Cantidad, precio y tipo de cambio deben ser positivos y finitos.")
    if currency not in ("USD", "ARS"):
        raise ValueError("Moneda no soportada.")
    # Argentine sovereign bonds quote per 100 nominal units.
    divisor = 100 if asset_type == "bond" else 1
    return float(quantity * price / divisor / (fx if currency == "ARS" else 1))
