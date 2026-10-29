"""Provider failure, cache expiry, verified identities and JWT propagation."""
from unittest.mock import Mock
from uuid import UUID
import httpx
import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from backend import auth
from backend.auth import User
from backend.db import storage
from backend.market import prices, dolar


def response(status, data):
    return httpx.Response(status, json=data, request=httpx.Request("GET", "https://test.invalid"))


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-key")


def test_identity_verified_by_auth_server(settings, monkeypatch):
    user_id = str(UUID(int=1))
    get = Mock(return_value=response(200, {"id": user_id}))
    monkeypatch.setattr(auth.httpx, "get", get)
    user = auth.require_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="signed-token"))
    assert user.id == user_id
    assert get.call_args.kwargs["headers"]["Authorization"] == "Bearer signed-token"
    get.return_value = response(401, {})
    with pytest.raises(HTTPException) as exc:
        auth.require_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="forged-token"))
    assert exc.value.status_code == 401


def test_storage_scopes_reads_and_deletes_and_passes_user_token(settings, monkeypatch):
    request = Mock(return_value=response(200, []))
    monkeypatch.setattr(storage.httpx, "request", request)
    user = User(str(UUID(int=1)), "token-a")
    assert storage.list_positions(user) == []
    assert request.call_args.kwargs["params"]["user_id"] == f"eq.{user.id}"
    assert request.call_args.kwargs["headers"]["Authorization"] == "Bearer token-a"
    assert storage.delete_position(user, str(UUID(int=5))) is False
    assert request.call_args.kwargs["params"]["user_id"] == f"eq.{user.id}"
    request.return_value = response(201, [{"id": str(UUID(int=2))}])
    storage.save_position(user, {"ticker": "AAPL", "user_id": "attacker"})
    assert request.call_args.kwargs["json"]["user_id"] == user.id


def test_quotes_cache_expires_and_manual_refresh_bypasses_it(monkeypatch):
    monkeypatch.setattr(prices, "_PRICE_CACHE", {})
    monkeypatch.setattr(prices, "_CURRENCY_CACHE", {})
    clock = [0.0]
    monkeypatch.setattr(prices, "monotonic", lambda: clock[0])
    instrument = Mock()
    instrument.history.return_value = pd.DataFrame({"Close": [100., 101.]}, index=pd.date_range("2024-01-01", periods=2, tz="UTC"))
    instrument.get_history_metadata.return_value = {"currency": "USD"}
    monkeypatch.setattr(prices.yf, "Ticker", lambda _: instrument)
    assert prices.get_current_quote("AAPL")["price"] == 101
    prices.get_current_quote("AAPL")
    assert instrument.history.call_count == 1
    prices.get_current_quote("AAPL", refresh=True)
    assert instrument.history.call_count == 2
    clock[0] = 61
    prices.get_current_quote("AAPL")
    assert instrument.history.call_count == 3
    assert instrument.history.call_args.kwargs["auto_adjust"] is False
    assert "quote_at" in prices.get_current_quote("AAPL")


def test_dolar_outage_never_creates_fake_rates(monkeypatch):
    monkeypatch.setattr(dolar, "_CACHE", None)
    monkeypatch.setattr(dolar.httpx, "get", Mock(side_effect=httpx.ConnectError("offline")))
    with pytest.raises(ValueError):
        dolar.get_dolar_rates()
    with pytest.raises(ValueError):
        dolar.get_mep_rate()


def test_historical_mep_sorted_cached_and_no_future_purchase_rate(monkeypatch):
    monkeypatch.setattr(prices, "_FX_CACHE", None)
    get = Mock(return_value=response(200, [
        {"fecha": "2024-01-03", "venta": 200},
        {"fecha": "2024-01-01", "venta": 100},
        {"fecha": "2024-01-02", "venta": 0},
    ]))
    monkeypatch.setattr(prices.httpx, "get", get)
    from datetime import date
    assert prices.get_mep_on_date(date(2024, 1, 2)) == 100
    assert prices.get_mep_history().iloc[-1] == 200
    assert get.call_count == 1
    with pytest.raises(ValueError):
        prices.get_mep_on_date(date(2023, 12, 31))
