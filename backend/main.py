"""Authenticated portfolio API, USD valuation and comparable Markowitz results."""
from datetime import datetime, timezone
from uuid import UUID
import os
import numpy as np
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .auth import User, require_user
from .schemas import PositionCreate, PositionResponse, OptimizationRequest, OptimizationResponse, FrontierPoint
from .db.storage import list_positions, save_position, delete_position
from .market.prices import fetch_multiple_tickers, get_currency, get_current_quote, get_mep_history, get_mep_on_date
from .market.dolar import get_dolar_rates, get_mep_rate
from .finance.returns import calculate_log_returns
from .finance.metrics import (calculate_expected_returns, calculate_covariance_matrix,
                              calculate_portfolio_performance, calculate_sharpe_ratio)
from .finance.optimizer import optimize_minimum_variance, optimize_maximum_sharpe, calculate_efficient_frontier
from .finance.valuation import annualization_factor, convert_history_to_usd, position_value

app = FastAPI(title="Portfolio Manager API", version="2.0.0")
app.add_middleware(CORSMiddleware,
    allow_origins=[v.strip() for v in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if v.strip()],
    allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Portfolio Manager", "version": "2.0.0"}


@app.get("/api/market/dolar")
def get_dolar_quotations(refresh: bool = False):
    try:
        return get_dolar_rates(refresh=refresh)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc


def enrich_positions(positions: list[dict], refresh: bool = False) -> list[dict]:
    fx, fx_error = 1.0, None
    if any(p["currency"] == "ARS" for p in positions):
        try:
            fx = get_mep_rate(refresh=refresh)
        except ValueError as exc:
            fx_error = str(exc)
    quotes = {}
    for ticker in dict.fromkeys(p["ticker"] for p in positions):
        try:
            quotes[ticker] = get_current_quote(ticker, refresh=refresh)
        except ValueError as exc:
            quotes[ticker] = {"error": str(exc)}
    result = []
    for p in positions:
        quantity, buy_price = float(p["quantity"]), float(p["buy_price"])
        cost = position_value(quantity, buy_price, p["currency"], float(p["buy_fx_rate"]), p["asset_type"])
        quote = quotes[p["ticker"]]
        error = quote.get("error") or (fx_error if p["currency"] == "ARS" else None)
        value = None if error else position_value(quantity, quote["price"], p["currency"], fx, p["asset_type"])
        result.append({**p, "cost_basis_usd": cost,
            "current_price": quote.get("price"), "market_value": value,
            "unrealized_pnl": None if value is None else value - cost,
            "unrealized_pnl_pct": None if value is None else (value - cost) / cost,
            "quote_at": quote.get("quote_at"), "quote_error": error})
    return result


@app.get("/api/positions", response_model=list[PositionResponse])
def get_positions(refresh: bool = False, user: User = Depends(require_user)):
    return enrich_positions(list_positions(user), refresh)


@app.post("/api/positions", response_model=PositionResponse, status_code=201)
def create_position(pos: PositionCreate, user: User = Depends(require_user)):
    try:
        currency = get_currency(pos.ticker)
        if currency != pos.currency:
            raise ValueError(f"{pos.ticker} cotiza en {currency}; corregí la moneda de compra.")
        fx = 1.0 if currency == "USD" else (pos.buy_fx_rate or get_mep_on_date(pos.buy_date))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    values = pos.model_dump(mode="json")
    values["buy_fx_rate"] = fx
    created = save_position(user, values)
    # Persist first; unavailable market data cannot make a successful insert look like a failed one.
    return enrich_positions([created])[0]


@app.delete("/api/positions/{position_id}")
def remove_position(position_id: UUID, user: User = Depends(require_user)):
    if not delete_position(user, str(position_id)):
        raise HTTPException(404, "Posición no encontrada.")
    return {"message": "Posición eliminada correctamente"}


@app.post("/api/optimize", response_model=OptimizationResponse)
def optimize_portfolio(request: OptimizationRequest, user: User = Depends(require_user)):
    tickers = request.tickers
    positions = list_positions(user) if request.compare_current else []
    if request.compare_current and (not positions or not {p["ticker"] for p in positions}.issubset(tickers)):
        raise HTTPException(422, "Incluí todos los activos de tu cartera para comparar sin omitir posiciones.")
    try:
        prices = fetch_multiple_tickers(tickers, period=request.period)
        currencies = {t: get_currency(t) for t in tickers}
        mep = get_mep_history(request.period) if "ARS" in currencies.values() else None
        prices = convert_history_to_usd(prices.loc[:, tickers], currencies, mep)
        returns = calculate_log_returns(prices)
        factor = annualization_factor(tickers)
        mu = calculate_expected_returns(returns, factor)
        cov = calculate_covariance_matrix(returns, factor)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    def point(result: dict) -> FrontierPoint:
        return FrontierPoint(expected_return=float(result["expected_return"]),
            volatility=float(result["volatility"]), sharpe_ratio=float(result["sharpe_ratio"]),
            weights={t: float(w) for t, w in zip(tickers, result["weights"], strict=True)})

    current, valuation_at = None, None
    if request.compare_current:
        valued = enrich_positions(positions)
        if any(p["quote_error"] for p in valued):
            raise HTTPException(503, "No se pudo valuar toda la cartera; reintentá cuando haya cotizaciones disponibles.")
        values = {t: 0.0 for t in tickers}
        for p in valued:
            values[p["ticker"]] += p["market_value"]
        total = sum(values.values())
        if not np.isfinite(total) or total <= 0:
            raise HTTPException(422, "La valuación total de la cartera debe ser positiva.")
        weights = np.array([values[t] / total for t in tickers])
        ret, vol = calculate_portfolio_performance(weights, mu, cov)
        current = point({"weights": weights, "expected_return": ret, "volatility": vol,
                         "sharpe_ratio": calculate_sharpe_ratio(ret, vol, request.risk_free_rate) if vol else 0.0})
        valuation_at = datetime.now(timezone.utc).isoformat()
    try:
        gmvp = optimize_minimum_variance(mu, cov, request.risk_free_rate, request.allow_short)
        tangency = optimize_maximum_sharpe(mu, cov, request.risk_free_rate, request.allow_short)
        frontier = calculate_efficient_frontier(mu, cov, 30, request.risk_free_rate, request.allow_short)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, f"No se pudo resolver la optimización: {exc}") from exc
    return OptimizationResponse(gmvp=point(gmvp), tangency=point(tangency),
        frontier=[point(p) for p in frontier], current_portfolio=current,
        annualization_factor=factor, observations=len(returns),
        start_date=prices.index[0].date().isoformat(), end_date=prices.index[-1].date().isoformat(),
        valuation_at=valuation_at,
        fx_method="MEP histórico de venta · ArgentinaDatos" if mep is not None else "Activos cotizados en USD")
