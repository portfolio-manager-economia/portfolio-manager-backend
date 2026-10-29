"""Validated public API contracts. All portfolio totals and returns use USD."""
from datetime import date
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssetType(str, Enum):
    STOCK = "stock"
    CEDEAR = "cedear"
    CRYPTO = "crypto"
    BOND = "bond"


class PositionCreate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    ticker: str = Field(pattern=r"^[A-Z0-9.^=\-]{1,30}$")
    asset_type: AssetType = AssetType.STOCK
    currency: Literal["ARS", "USD"]
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)
    buy_date: date
    buy_fx_rate: float | None = Field(None, gt=0, description="ARS por USD en la compra; opcional, se estima con MEP histórico")

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("buy_date")
    @classmethod
    def past_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("La fecha de compra no puede ser futura.")
        return value


class PositionResponse(PositionCreate):
    id: str
    current_price: float | None = None
    market_value: float | None = None
    cost_basis_usd: float
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None
    quote_at: str | None = None
    quote_error: str | None = None


class OptimizationRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    tickers: list[str] = Field(min_length=2, max_length=40)
    risk_free_rate: float = Field(0.04, ge=0, le=1)
    allow_short: Literal[False] = False
    period: Literal["6mo", "1y", "2y", "5y"] = "1y"
    compare_current: bool = False

    @field_validator("tickers")
    @classmethod
    def normalize_tickers(cls, values: list[str]) -> list[str]:
        import re
        tickers = [v.strip().upper() for v in values]
        if len(set(tickers)) != len(tickers):
            raise ValueError("Los activos deben ser distintos.")
        if any(not re.fullmatch(r"[A-Z0-9.^=\-]{1,30}", t) for t in tickers):
            raise ValueError("Ticker inválido.")
        return tickers


class FrontierPoint(BaseModel):
    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: dict[str, float]


class OptimizationResponse(BaseModel):
    gmvp: FrontierPoint
    tangency: FrontierPoint
    frontier: list[FrontierPoint]
    current_portfolio: FrontierPoint | None = None
    currency: Literal["USD"] = "USD"
    annualization_factor: int
    observations: int
    start_date: str
    end_date: str
    valuation_at: str | None = None
    fx_method: str
