"""Discovery must preserve exchange identity and never classify unsupported products."""
from unittest.mock import Mock
import pytest
from backend.market import assets
from backend.auth import User, require_user
from backend.main import app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def cache(monkeypatch):
    monkeypatch.setattr(assets, "_CACHE", {})


def test_search_filters_unsupported_and_keeps_cedear_distinct(monkeypatch):
    search = Mock(return_value=Mock(quotes=[
        {"symbol": "AAPL", "quoteType": "EQUITY", "exchange": "NMS", "longname": "Apple Inc."},
        {"symbol": "AAPL.BA", "quoteType": "EQUITY", "exchange": "BUE", "shortname": "Apple"},
        {"symbol": "GGAL.BA", "quoteType": "EQUITY", "exchange": "BUE"},
        {"symbol": "VTI", "quoteType": "ETF", "exchange": "PCX"},
        {"symbol": "BTC-USD", "quoteType": "CRYPTOCURRENCY", "exchange": "CCC"},
        {"symbol": "BTC-EUR", "quoteType": "CRYPTOCURRENCY", "exchange": "CCC"},
        {"symbol": "SHOP.TO", "quoteType": "EQUITY", "exchange": "TOR"},
        {"symbol": "ES=F", "quoteType": "FUTURE", "exchange": "CME"},
        {"symbol": "AAPL", "quoteType": "EQUITY", "exchange": "NMS"},
    ]))
    monkeypatch.setattr(assets.yf, "Search", search)
    result = assets.search_assets("Apple")
    assert [r["ticker"] for r in result] == ["AAPL", "AAPL.BA", "GGAL.BA", "VTI", "BTC-USD"]
    assert result[0]["currency"] == "USD" and result[1]["currency"] == "ARS"
    assert result[1]["asset_type"] == "cedear"
    assert result[2]["asset_type"] is None  # Ask instead of assuming every .BA is a CEDEAR.
    assert result[3]["instrument"] == "ETF"
    result[0]["ticker"] = "changed"
    assert assets.search_assets(" apple ")[0]["ticker"] == "AAPL"
    assert search.call_count == 1
    assert search.call_args.kwargs["timeout"] == 10


def test_search_cache_expires_and_provider_failure_is_not_empty_success(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(assets, "monotonic", lambda: clock[0])
    search = Mock(return_value=Mock(quotes=[]))
    monkeypatch.setattr(assets.yf, "Search", search)
    assert assets.search_assets("Unknown") == []
    clock[0] = assets.SEARCH_TTL + 1
    search.side_effect = RuntimeError("unavailable")
    with pytest.raises(ValueError, match="buscador"):
        assets.search_assets("Unknown")


def test_logo_urls_match_instrument_and_allow_absence():
    assert assets.asset_logo_url("AAPL.BA") == assets.asset_logo_url("AAPL")
    assert assets.asset_logo_url("BTC-USD").endswith("/BTCUSD.png")
    assert assets.asset_logo_url("YPFD.BA").endswith("/YPF.png")
    assert assets.asset_logo_url("AL30D.BA") is None
    assert assets.asset_logo_url("https://attacker.invalid") is None


def test_routes_auth_and_details_use_actual_provider_currency(monkeypatch):
    client = TestClient(app)
    assert client.get("/api/market/assets/search?q=Apple").status_code == 401
    assert client.get("/api/market/assets/AAPL").status_code == 401
    app.dependency_overrides[require_user] = lambda: User("user-a", "token-a")
    try:
        assert client.get("/api/market/assets/search?q= ").status_code == 422
        monkeypatch.setattr("backend.main.search_assets", lambda q: [])
        assert client.get("/api/market/assets/search?q=unknown").json() == []
        monkeypatch.setattr("backend.main.get_currency", lambda t: "USD")
        monkeypatch.setattr("backend.main.get_current_quote", lambda t: {"price": 123, "quote_at": "2026-11-03T12:00:00Z"})
        result = client.get("/api/market/assets/AAPL").json()
        assert result["currency"] == "USD" and result["price"] == 123
        assert result["logo_url"].endswith("/AAPL.png")
        def fail(*args):
            raise ValueError("Sin cotización")
        monkeypatch.setattr("backend.main.get_current_quote", fail)
        assert client.get("/api/market/assets/AAPL").json()["price"] is None
        monkeypatch.setattr("backend.main.get_currency", fail)
        assert client.get("/api/market/assets/AAPL").status_code == 422
    finally:
        app.dependency_overrides.clear()
