"""Esquemas de datos y validación de entrada/salida (Pydantic)."""

from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AssetType(str, Enum):
    STOCK = "stock"
    CEDEAR = "cedear"
    CRYPTO = "crypto"
    BOND = "bond"


class PositionBase(BaseModel):
    ticker: str = Field(..., description="Ticker o símbolo del activo (ej: AAPL, GGAL.BA, BTC-USD)")
    asset_type: AssetType = Field(AssetType.STOCK, description="Tipo de activo financiero")
    quantity: float = Field(..., gt=0, description="Cantidad nominal de títulos")
    buy_price: float = Field(..., gt=0, description="Precio unitario de compra")
    buy_date: date = Field(..., description="Fecha de adquisición")


class PositionCreate(PositionBase):
    pass


class PositionResponse(PositionBase):
    id: Optional[str] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None


class PortfolioPerformanceResponse(BaseModel):
    expected_return: float = Field(..., description="Retorno anualizado esperado")
    volatility: float = Field(..., description="Volatilidad anualizada (desvío estándar)")
    sharpe_ratio: float = Field(..., description="Ratio de Sharpe")
    weights: Dict[str, float] = Field(..., description="Ponderación por activo en el portafolio")


class OptimizationRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, description="Lista de activos a incluir en el análisis")
    risk_free_rate: float = Field(0.0, ge=0.0, description="Tasa libre de riesgo anualizada (ej: 0.04 para 4%)")
    allow_short: bool = Field(False, description="Permitir ventas en corto (long-only por defecto)")
    period: str = Field("1y", description="Período de datos históricos (ej: '6mo', '1y', '2y', '5y')")


class FrontierPoint(BaseModel):
    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]


class OptimizationResponse(BaseModel):
    gmvp: FrontierPoint = Field(..., description="Portafolio de Mínima Varianza Global")
    tangency: FrontierPoint = Field(..., description="Portafolio de Máximo Ratio de Sharpe")
    frontier: List[FrontierPoint] = Field(default_factory=list, description="Puntos de la Frontera Eficiente")
    current_portfolio: Optional[FrontierPoint] = Field(None, description="Métricas de la cartera actual para comparación")

