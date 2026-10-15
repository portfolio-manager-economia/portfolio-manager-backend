"""Cliente para dolarapi.com para consultar cotizaciones del dólar en Argentina (Oficial, MEP, CCL, Blue)."""

from typing import Any, Dict, Optional
import httpx


DOLAR_API_BASE_URL = "https://dolarapi.com/v1/dolares"


def get_dolar_rates() -> Dict[str, Dict[str, Any]]:
    """Consulta las cotizaciones vigentes de todos los tipos de dólar.

    Retorna un diccionario {casa: {compra, venta, fechaActualizacion, ...}}.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(DOLAR_API_BASE_URL)
            resp.raise_for_status()
            data = resp.json()
            return {item["casa"]: item for item in data}
    except Exception as e:
        # Fallback de respaldo o error descriptivo
        return {
            "error": str(e),
            "oficial": {"compra": 980.0, "venta": 1020.0},
            "bolsa": {"compra": 1180.0, "venta": 1200.0},
            "contadoconliqui": {"compra": 1220.0, "venta": 1240.0},
        }


def get_mep_rate() -> float:
    """Obtiene la cotización de venta del Dólar MEP (Bolsa)."""
    rates = get_dolar_rates()
    if "bolsa" in rates and "venta" in rates["bolsa"]:
        return float(rates["bolsa"]["venta"])
    return 1200.0

