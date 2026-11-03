"""Validated public API contracts. All portfolio totals and returns use USD."""
from datetime import date
from enum import Enum
from typing import Literal
from uuid import UUID
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
    logo_url: str | None = None
    current_price: float | None = None
    market_value: float | None = None
    cost_basis_usd: float
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None
    quote_at: str | None = None
    quote_error: str | None = None


class AssetSearchResult(BaseModel):
    ticker: str
    name: str
    asset_type: AssetType | None = None
    currency: Literal["ARS", "USD"]
    instrument: str | None = None
    exchange: str
    logo_url: str | None = None


class ScreenshotRequest(BaseModel):
    mime_type: Literal["image/png", "image/jpeg", "image/webp"]
    image_base64: str = Field(min_length=1, max_length=7_000_000)


class ExtractedPosition(BaseModel):
    """Untrusted draft: unknown information remains null until reviewed."""
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    name: str | None = Field(None, max_length=200)
    ticker: str | None = Field(None, max_length=30)
    asset_type: AssetType | None = None
    currency: Literal["ARS", "USD"] | None = None
    quantity: float | None = Field(None, gt=0)
    buy_price: float | None = Field(None, gt=0)
    buy_date: date | None = None
    buy_fx_rate: float | None = Field(None, gt=0)
    notes: str = Field("", max_length=1000)


class ScreenshotDraft(BaseModel):
    positions: list[ExtractedPosition] = Field(max_length=40)
    warnings: list[str] = Field(default_factory=list, max_length=40)


class ImportPositionsRequest(BaseModel):
    import_id: UUID
    positions: list[PositionCreate] = Field(min_length=1, max_length=40)


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
