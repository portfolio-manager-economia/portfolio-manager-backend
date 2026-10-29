"""Yahoo prices with bounded TTL caches, explicit refresh and dated quotes."""
from datetime import date, timedelta
from time import monotonic
from threading import RLock
import numpy as np
import pandas as pd
import yfinance as yf
import httpx

_PRICE_CACHE: dict[tuple, tuple[float, pd.DataFrame]] = {}
_CURRENCY_CACHE: dict[str, tuple[float, str]] = {}
_LOCK = RLock()
HISTORY_TTL = 3600
QUOTE_TTL = 60
_FX_CACHE: tuple[float, pd.Series] | None = None


def _history(ticker: str, *, period: str = "1y", interval: str = "1d",
             adjusted: bool = True, refresh: bool = False,
             start: str | None = None, end: str | None = None) -> pd.DataFrame:
    ticker = ticker.strip().upper()
    key = (ticker, period, interval, adjusted, start, end)
    ttl = QUOTE_TTL if interval == "1m" or (period == "5d" and not adjusted) else HISTORY_TTL
    with _LOCK:
        cached = _PRICE_CACHE.get(key)
    if not refresh and cached and monotonic() - cached[0] < ttl:
        return cached[1].copy()
    instrument = yf.Ticker(ticker)
    kwargs = {"start": start, "end": end} if start else {"period": period}
    try:
        history = instrument.history(interval=interval, auto_adjust=adjusted, timeout=15, **kwargs)
        if history is None or history.empty:
            raise ValueError(f"No hay cotizaciones disponibles para {ticker}.")
        currency = instrument.get_history_metadata().get("currency")
        if currency not in ("ARS", "USD"):
            raise ValueError(f"{ticker}: moneda no soportada ({currency}); se admite ARS o USD.")
        close = history["Close"].dropna()
        if close.empty or not np.isfinite(close).all() or (close <= 0).any():
            raise ValueError(f"Precios inválidos para {ticker}.")
    except Exception as exc:
        raise ValueError(f"No se pudieron consultar precios de {ticker}: {exc}") from exc
    with _LOCK:
        if len(_PRICE_CACHE) >= 256:
            _PRICE_CACHE.pop(next(iter(_PRICE_CACHE)))
        _PRICE_CACHE[key] = (monotonic(), history.copy())
        if len(_CURRENCY_CACHE) >= 256:
            _CURRENCY_CACHE.pop(next(iter(_CURRENCY_CACHE)))
        _CURRENCY_CACHE[ticker] = (monotonic(), currency)
    return history.copy()


def get_currency(ticker: str) -> str:
    with _LOCK:
        cached = _CURRENCY_CACHE.get(ticker)
    if cached and monotonic() - cached[0] < HISTORY_TTL:
        return cached[1]
    _history(ticker, period="5d")
    return _CURRENCY_CACHE[ticker][1]


def fetch_historical_prices(ticker: str, period: str = "1y", interval: str = "1d",
                            use_cache: bool = True, adjusted: bool = True,
                            start: str | None = None, end: str | None = None) -> pd.Series:
    history = _history(ticker, period=period, interval=interval, adjusted=adjusted,
                       refresh=not use_cache, start=start, end=end)
    series = history["Close"].dropna()
    series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
    return series


def fetch_multiple_tickers(tickers: list[str], period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    df = pd.DataFrame({t: fetch_historical_prices(t, period, interval) for t in tickers}).dropna()
    if len(df) < 3:
        raise ValueError("Se requieren al menos 3 precios en fechas comunes.")
    return df.sort_index()


def get_current_quote(ticker: str, refresh: bool = False) -> dict:
    try:
        history = _history(ticker, period="5d", interval="1m", adjusted=False, refresh=refresh)
    except ValueError:
        # Some instruments have no intraday feed. The returned timestamp exposes the age of the last close.
        history = _history(ticker, period="5d", adjusted=False, refresh=refresh)
    series = history["Close"].dropna()
    return {"price": float(series.iloc[-1]), "quote_at": series.index[-1].isoformat()}


def get_current_price(ticker: str) -> float:
    return get_current_quote(ticker)["price"]


def get_mep_history(period: str = "1y", *, on_date: date | None = None) -> pd.Series:
    # Download once per hour. Callers select exact historical price dates, never today's FX.
    global _FX_CACHE
    with _LOCK:
        cached = _FX_CACHE
    if cached and monotonic() - cached[0] < HISTORY_TTL:
        rates = cached[1].copy()
    else:
        try:
            response = httpx.get("https://api.argentinadatos.com/v1/cotizaciones/dolares/bolsa",
                                 timeout=20, follow_redirects=True)
            response.raise_for_status()
            data = pd.DataFrame(response.json())
            rates = pd.Series(pd.to_numeric(data["venta"], errors="coerce").to_numpy(),
                              index=pd.to_datetime(data["fecha"]).dt.normalize(), dtype=float)
            rates = rates[np.isfinite(rates) & (rates > 0)].sort_index()
            rates = rates[~rates.index.duplicated(keep="last")]
            if rates.empty:
                raise ValueError("Serie vacía")
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ValueError("No se pudo obtener el MEP histórico de ArgentinaDatos.") from exc
        with _LOCK:
            _FX_CACHE = (monotonic(), rates.copy())
    if on_date:
        rates = rates.loc[(rates.index <= pd.Timestamp(on_date)) &
                          (rates.index >= pd.Timestamp(on_date - timedelta(days=10)))]
    return rates


def get_mep_on_date(on_date: date) -> float:
    rates = get_mep_history(on_date=on_date)
    past = rates.loc[rates.index <= pd.Timestamp(on_date)]
    if past.empty:
        raise ValueError("No hay MEP histórico para la fecha de compra; ingresalo manualmente.")
    return float(past.iloc[-1])
