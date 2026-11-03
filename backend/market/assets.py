"""Asset discovery with bounded caching. Financial calculations remain in finance/."""
import re
from threading import RLock
from time import monotonic
import yfinance as yf

_CACHE: dict[str, tuple[float, list[dict]]] = {}
_LOCK = RLock()
SEARCH_TTL = 3600
# Only known CEDEARs can be classified automatically. Other Buenos Aires equities
# require the user to distinguish local shares from depositary receipts.
CEDEARS = {"AAPL.BA", "MSFT.BA", "GOOGL.BA", "AMZN.BA", "TSLA.BA", "NVDA.BA",
           "MELI.BA", "KO.BA", "SPY.BA", "QQQ.BA", "VIST.BA"}
US_EXCHANGES = {"NMS", "NGM", "NCM", "NYQ", "ASE", "PCX", "BTS", "BATS", "NAS", "NYSE", "AMEX"}


def asset_logo_url(ticker: str) -> str | None:
    """Best-effort logo; no network calls while valuing a portfolio."""
    if not re.fullmatch(r"[A-Z0-9.^=\-]{1,30}", ticker):
        return None
    if ticker.endswith("-USD"):
        symbol = ticker.replace("-USD", "USD")
    elif ticker.endswith(".BA"):
        symbol = {"YPFD": "YPF", "PAMP": "PAM"}.get(ticker[:-3], ticker[:-3])
        if re.fullmatch(r"(?:AL|GD)\d+D?", symbol):
            return None
    else:
        symbol = ticker
    return f"https://financialmodelingprep.com/image-stock/{symbol}.png"


def search_assets(query: str) -> list[dict]:
    key = query.strip().casefold()
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and monotonic() - cached[0] < SEARCH_TTL:
            return [dict(row) for row in cached[1]]
    try:
        quotes = yf.Search(query.strip(), max_results=20, news_count=0, lists_count=0,
                           include_cb=False, timeout=10, raise_errors=True).quotes
    except Exception as exc:
        raise ValueError("No se pudo consultar el buscador de activos. Probá nuevamente o usá el catálogo.") from exc
    results, seen = [], set()
    for quote in quotes:
        ticker = str(quote.get("symbol", "")).upper()
        kind, exchange = quote.get("quoteType"), quote.get("exchange")
        if ticker in seen or not re.fullmatch(r"[A-Z0-9.^=\-]{1,30}", ticker):
            continue
        if kind == "CRYPTOCURRENCY" and ticker.endswith("-USD"):
            asset_type, currency = "crypto", "USD"
        elif kind in ("EQUITY", "ETF") and exchange in US_EXCHANGES:
            asset_type, currency = "stock", "USD"
        elif kind in ("EQUITY", "ETF") and (exchange == "BUE" or ticker.endswith(".BA")):
            name = str(quote.get("longname") or quote.get("shortname") or "")
            asset_type = "cedear" if ticker in CEDEARS or "CEDEAR" in name.upper() else None
            if re.fullmatch(r"(?:AL|GD)\d+D?\.BA", ticker):
                asset_type = "bond"
            currency = "USD" if re.fullmatch(r"(?:AL|GD)\d+D\.BA", ticker) else "ARS"
        else:
            continue
        seen.add(ticker)
        results.append({"ticker": ticker,
            "name": quote.get("longname") or quote.get("shortname") or ticker,
            "asset_type": asset_type, "currency": currency, "instrument": "ETF" if kind == "ETF" else None,
            "exchange": quote.get("exchDisp") or exchange or "",
            "logo_url": asset_logo_url(ticker)})
    with _LOCK:
        if len(_CACHE) >= 128:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = (monotonic(), results)
    return [dict(row) for row in results]
