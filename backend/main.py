"""Servidor API REST FastAPI para Portfolio Manager."""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    PositionCreate,
    PositionResponse,
    OptimizationRequest,
    OptimizationResponse,
    FrontierPoint,
)
from .db.storage import init_db, save_position, list_positions, delete_position
from .market.prices import fetch_historical_prices, fetch_multiple_tickers, get_current_price
from .market.dolar import get_dolar_rates, get_mep_rate
from .finance.returns import calculate_log_returns
from .finance.metrics import (
    calculate_expected_returns,
    calculate_covariance_matrix,
    calculate_portfolio_performance,
    calculate_sharpe_ratio,
)
from .finance.optimizer import (
    optimize_minimum_variance,
    optimize_maximum_sharpe,
    calculate_efficient_frontier,
)

# Inicializar Base de Datos
init_db()

app = FastAPI(
    title="Portfolio Manager API",
    description="Backend para seguimiento y optimización de carteras según el modelo de Markowitz.",
    version="1.0.0",
)

# Configuración de CORS para permitir peticiones desde React / Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Endpoint de estado del servicio."""
    return {"status": "ok", "app": "Portfolio Manager", "version": "1.0.0"}


@app.get("/api/market/dolar", tags=["Market"])
def get_dolar_quotations():
    """Retorna las cotizaciones del dólar en Argentina desde dolarapi.com."""
    return get_dolar_rates()


@app.get("/api/positions", response_model=List[PositionResponse], tags=["Positions"])
def get_positions():
    """Recupera la lista de posiciones del usuario con valuación a precios actuales."""
    positions = list_positions()
    enriched = []
    for pos in positions:
        ticker = pos["ticker"]
        try:
            curr_price = get_current_price(ticker)
        except Exception:
            curr_price = pos["buy_price"]

        qty = pos["quantity"]
        market_val = qty * curr_price
        cost_val = qty * pos["buy_price"]
        pnl = market_val - cost_val
        pnl_pct = (pnl / cost_val) if cost_val > 0 else 0.0

        enriched.append({
            **pos,
            "current_price": round(curr_price, 2),
            "market_value": round(market_val, 2),
            "unrealized_pnl": round(pnl, 2),
            "unrealized_pnl_pct": round(pnl_pct, 4),
        })
    return enriched


@app.post("/api/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED, tags=["Positions"])
def create_position(pos: PositionCreate):
    """Registra una nueva posición en el portafolio."""
    created = save_position(
        ticker=pos.ticker,
        asset_type=pos.asset_type.value,
        quantity=pos.quantity,
        buy_price=pos.buy_price,
        buy_date=pos.buy_date,
    )
    return {
        **created,
        "current_price": pos.buy_price,
        "market_value": round(pos.quantity * pos.buy_price, 2),
        "unrealized_pnl": 0.0,
        "unrealized_pnl_pct": 0.0,
    }


@app.delete("/api/positions/{position_id}", tags=["Positions"])
def remove_position(position_id: str):
    """Elimina una posición por su identificador."""
    success = delete_position(position_id)
    if not success:
        raise HTTPException(status_code=404, detail="Posición no encontrada.")
    return {"message": "Posición eliminada correctamente"}


@app.post("/api/optimize", response_model=OptimizationResponse, tags=["Optimization"])
def optimize_portfolio(request: OptimizationRequest):
    """Ejecuta la optimización de Markowitz sobre una lista de activos.

    Calcula el portafolio de mínima varianza (GMVP), de máximo Sharpe (tangencia)
    y los puntos de la frontera eficiente.
    """
    tickers = [t.strip().upper() for t in request.tickers]
    if len(tickers) < 2:
        raise HTTPException(
            status_code=400,
            detail="Se requieren al menos 2 activos distintos para calcular la optimización y frontera de Markowitz.",
        )

    try:
        prices_df = fetch_multiple_tickers(tickers, period=request.period)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error obteniendo precios: {str(e)}")

    try:
        log_ret = calculate_log_returns(prices_df)
        annualization = 252  # estándar para activos financieros
        exp_ret = calculate_expected_returns(log_ret, annualization_factor=annualization)
        cov_mat = calculate_covariance_matrix(log_ret, annualization_factor=annualization)

        # 1. Mínima varianza
        gmvp_res = optimize_minimum_variance(
            exp_ret, cov_mat, risk_free_rate=request.risk_free_rate, allow_short=request.allow_short
        )
        gmvp_weights = {tickers[i]: round(float(gmvp_res["weights"][i]), 4) for i in range(len(tickers))}

        # 2. Máximo Sharpe
        max_sharpe_res = optimize_maximum_sharpe(
            exp_ret, cov_mat, risk_free_rate=request.risk_free_rate, allow_short=request.allow_short
        )
        tangency_weights = {tickers[i]: round(float(max_sharpe_res["weights"][i]), 4) for i in range(len(tickers))}

        # 3. Frontera eficiente
        frontier_points = calculate_efficient_frontier(
            exp_ret, cov_mat, num_portfolios=30, risk_free_rate=request.risk_free_rate, allow_short=request.allow_short
        )
        frontier_output = []
        for pt in frontier_points:
            pt_weights = {tickers[i]: round(float(pt["weights"][i]), 4) for i in range(len(tickers))}
            frontier_output.append(FrontierPoint(
                expected_return=round(float(pt["expected_return"]), 4),
                volatility=round(float(pt["volatility"]), 4),
                sharpe_ratio=round(float(pt["sharpe_ratio"]), 4),
                weights=pt_weights,
            ))

        return OptimizationResponse(
            gmvp=FrontierPoint(
                expected_return=round(float(gmvp_res["expected_return"]), 4),
                volatility=round(float(gmvp_res["volatility"]), 4),
                sharpe_ratio=round(float(gmvp_res["sharpe_ratio"]), 4),
                weights=gmvp_weights,
            ),
            tangency=FrontierPoint(
                expected_return=round(float(max_sharpe_res["expected_return"]), 4),
                volatility=round(float(max_sharpe_res["volatility"]), 4),
                sharpe_ratio=round(float(max_sharpe_res["sharpe_ratio"]), 4),
                weights=tangency_weights,
            ),
            frontier=frontier_output,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante el cálculo cuantitativo: {str(e)}")

