"""Tests de integración para los endpoints de la API REST."""

from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_check():
    """Verifica que el servicio responda status 200 y mensaje ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "Portfolio Manager"


def test_positions_crud():
    """Verifica el ciclo de vida de una posición: creación, listado y eliminación."""
    new_pos = {
        "ticker": "AAPL",
        "asset_type": "stock",
        "quantity": 10.0,
        "buy_price": 150.0,
        "buy_date": "2024-01-15",
    }
    # 1. Crear posición
    create_resp = client.post("/api/positions", json=new_pos)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    pos_id = created_data["id"]
    assert created_data["ticker"] == "AAPL"
    assert created_data["quantity"] == 10.0

    # 2. Listar posiciones
    list_resp = client.get("/api/positions")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(p["id"] == pos_id for p in items)

    # 3. Eliminar posición
    del_resp = client.delete(f"/api/positions/{pos_id}")
    assert del_resp.status_code == 200

    # 4. Verificar que no exista más
    list_resp_after = client.get("/api/positions")
    items_after = list_resp_after.json()
    assert not any(p["id"] == pos_id for p in items_after)


@patch("backend.main.fetch_multiple_tickers")
def test_optimize_endpoint_mocked(mock_fetch):
    """Verifica el endpoint de optimización utilizando datos simulados (sin conexión externa)."""
    # Crear series sintéticas deterministas
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    mock_df = pd.DataFrame({
        "AAPL": [150.0 + i * 1.5 for i in range(10)],
        "MSFT": [300.0 + i * 2.0 for i in range(10)],
    }, index=dates)
    mock_fetch.return_value = mock_df

    payload = {
        "tickers": ["AAPL", "MSFT"],
        "risk_free_rate": 0.03,
        "allow_short": False,
        "period": "1y",
    }
    response = client.post("/api/optimize", json=payload)
    assert response.status_code == 200
    res_data = response.json()

    # Validar estructura y propiedades de Markowitz
    assert "gmvp" in res_data
    assert "tangency" in res_data
    assert "frontier" in res_data

    # Validar que los pesos sumen 1
    gmvp_weights = res_data["gmvp"]["weights"]
    assert np.isclose(sum(gmvp_weights.values()), 1.0, atol=1e-3)

    tangency_weights = res_data["tangency"]["weights"]
    assert np.isclose(sum(tangency_weights.values()), 1.0, atol=1e-3)

    # Validar que la frontera contenga puntos válidos
    assert len(res_data["frontier"]) > 0

