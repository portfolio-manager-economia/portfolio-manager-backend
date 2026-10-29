"""Deterministic API tests without market calls or a production database."""
from copy import deepcopy
from uuid import uuid4
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import User, require_user

client = TestClient(app)
USER_A = User("00000000-0000-0000-0000-000000000001", "token-a")
USER_B = User("00000000-0000-0000-0000-000000000002", "token-b")


@pytest.fixture
def environment(monkeypatch):
    rows = []
    app.dependency_overrides[require_user] = lambda: USER_A
    def save(user, values):
        row = {**values, "id": str(uuid4()), "user_id": user.id}
        rows.append(row)
        return deepcopy(row)
    def delete(user, position_id):
        match = next((r for r in rows if r["id"] == position_id and r["user_id"] == user.id), None)
        if match is None:
            return False
        rows.remove(match)
        return True
    monkeypatch.setattr("backend.main.save_position", save)
    monkeypatch.setattr("backend.main.list_positions", lambda user: deepcopy([r for r in rows if r["user_id"] == user.id]))
    monkeypatch.setattr("backend.main.delete_position", delete)
    monkeypatch.setattr("backend.main.get_currency", lambda t: "ARS" if t.endswith(".BA") else "USD")
    monkeypatch.setattr("backend.main.get_current_quote", lambda t, refresh=False: {"price": 200 if t == "AAPL" else 100, "quote_at": "2026-10-28T12:00:00Z"})
    monkeypatch.setattr("backend.main.get_mep_rate", lambda refresh=False: 200)
    yield rows
    app.dependency_overrides.clear()


def position(ticker="AAPL", **kwargs):
    return {"ticker": ticker, "asset_type": "stock", "currency": "USD", "quantity": 10,
            "buy_price": 150, "buy_date": "2024-01-15", **kwargs}


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


@pytest.mark.parametrize("method,path,body", [
    ("GET", "/api/positions", None), ("POST", "/api/positions", position()),
    ("DELETE", f"/api/positions/{uuid4()}", None),
    ("POST", "/api/optimize", {"tickers": ["AAPL", "MSFT"]}),
])
def test_private_routes_require_auth(method, path, body):
    assert client.request(method, path, json=body).status_code == 401


def test_crud_and_user_isolation(environment):
    response = client.post("/api/positions", json=position())
    assert response.status_code == 201
    row = response.json()
    assert row["cost_basis_usd"] == 1500 and row["market_value"] == 2000
    assert row["unrealized_pnl"] == 500
    assert row["unrealized_pnl_pct"] == pytest.approx(1 / 3)
    assert len(client.get("/api/positions").json()) == 1
    app.dependency_overrides[require_user] = lambda: USER_B
    assert client.get("/api/positions").json() == []
    assert client.delete(f"/api/positions/{row['id']}").status_code == 404
    app.dependency_overrides[require_user] = lambda: USER_A
    assert client.delete(f"/api/positions/{row['id']}").status_code == 200
    assert client.get("/api/positions").json() == []


def test_missing_quote_is_not_purchase_price(environment, monkeypatch):
    def unavailable(*args, **kwargs):
        raise ValueError("Proveedor no disponible")
    monkeypatch.setattr("backend.main.get_current_quote", unavailable)
    row = client.post("/api/positions", json=position()).json()
    assert row["current_price"] is None and row["market_value"] is None
    assert row["unrealized_pnl"] is None and row["quote_error"]


def test_currency_validation_and_historical_cost(environment, monkeypatch):
    assert client.post("/api/positions", json=position(currency="ARS")).status_code == 422
    monkeypatch.setattr("backend.main.get_mep_on_date", lambda d: 100)
    row = client.post("/api/positions", json=position("GGAL.BA", currency="ARS", buy_price=1000)).json()
    assert row["buy_fx_rate"] == 100 and row["cost_basis_usd"] == 100
    assert row["market_value"] == 5


def mock_prices(monkeypatch, tickers):
    rng = np.random.default_rng(7)
    data = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.01, (90, len(tickers))), axis=0))
    df = pd.DataFrame(data, index=pd.bdate_range("2024-01-01", periods=90), columns=tickers)
    monkeypatch.setattr("backend.main.fetch_multiple_tickers", lambda *a, **k: df)
    return df


def test_comparison_uses_market_weights_and_aggregates_lots(environment, monkeypatch):
    prices = mock_prices(monkeypatch, ["AAPL", "MSFT"])
    client.post("/api/positions", json=position(quantity=1))
    client.post("/api/positions", json=position(quantity=2))
    client.post("/api/positions", json=position("MSFT", quantity=4))
    response = client.post("/api/optimize", json={"tickers": ["MSFT", "AAPL"], "compare_current": True})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["current_portfolio"]["weights"] == pytest.approx({"AAPL": .6, "MSFT": .4})
    from backend.finance.metrics import calculate_portfolio_performance
    returns = np.log(prices / prices.shift()).dropna()
    expected, vol = calculate_portfolio_performance([.6, .4], returns.mean() * 252, returns.cov() * 252)
    assert data["current_portfolio"]["expected_return"] == pytest.approx(expected)
    assert data["current_portfolio"]["volatility"] == pytest.approx(vol)
    for key in ("gmvp", "tangency"):
        assert sum(data[key]["weights"].values()) == pytest.approx(1)
        assert min(data[key]["weights"].values()) >= -1e-8
    assert data["currency"] == "USD" and data["annualization_factor"] == 252


def test_compare_rejects_missing_holdings(environment):
    client.post("/api/positions", json=position())
    assert client.post("/api/optimize", json={"tickers": ["MSFT", "GOOGL"], "compare_current": True}).status_code == 422


@pytest.mark.parametrize("tickers,factor", [(["BTC-USD", "ETH-USD"], 365), (["BTC-USD", "AAPL"], 252)])
def test_optimizer_calendar(environment, monkeypatch, tickers, factor):
    mock_prices(monkeypatch, tickers)
    response = client.post("/api/optimize", json={"tickers": tickers})
    assert response.status_code == 200, response.text
    assert response.json()["annualization_factor"] == factor


def test_duplicate_tickers_rejected(environment):
    assert client.post("/api/optimize", json={"tickers": [" aapl", "AAPL"]}).status_code == 422
