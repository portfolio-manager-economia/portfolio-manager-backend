"""DolarAPI quotes: never fabricate a fallback exchange rate."""
from copy import deepcopy
from threading import RLock
from time import monotonic
import math
import httpx

DOLAR_API_BASE_URL = "https://dolarapi.com/v1/dolares"
_CACHE: tuple[float, dict] | None = None
_LOCK = RLock()


def get_dolar_rates(refresh: bool = False) -> dict:
    global _CACHE
    with _LOCK:
        cached = _CACHE
    if not refresh and cached and monotonic() - cached[0] < 60:
        return deepcopy(cached[1])
    try:
        response = httpx.get(DOLAR_API_BASE_URL, timeout=10)
        response.raise_for_status()
        rates = {item["casa"]: item for item in response.json()}
        if not rates:
            raise ValueError("Respuesta vacía")
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("No se pudieron obtener las cotizaciones de DolarAPI.") from exc
    with _LOCK:
        _CACHE = (monotonic(), deepcopy(rates))
    return rates


def get_mep_rate(refresh: bool = False) -> float:
    try:
        value = float(get_dolar_rates(refresh)["bolsa"]["venta"])
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Cotización no positiva")
        return value
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("No hay una cotización MEP válida para convertir ARS a USD.") from exc
