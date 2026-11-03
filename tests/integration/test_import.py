"""Import safety boundaries: no real Gemini calls or database writes."""
import base64
from io import BytesIO
import json
from unittest.mock import Mock
from uuid import uuid4
import httpx
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import User, require_user
from backend import importer
from backend.db import storage

client = TestClient(app)
USER = User("00000000-0000-0000-0000-000000000001", "test-jwt")


def image_request():
    out = BytesIO()
    Image.new("RGB", (20, 20)).save(out, format="PNG")
    return {"mime_type": "image/png", "image_base64": base64.b64encode(out.getvalue()).decode()}


@pytest.fixture
def setup(monkeypatch):
    app.dependency_overrides[require_user] = lambda: USER
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setattr(importer, "_usage", {})
    yield
    app.dependency_overrides.clear()


def provider(status=200, draft=None, finish="STOP"):
    return httpx.Response(status, json={"candidates": [{"finishReason": finish,
        "content": {"parts": [{"text": json.dumps(draft or {"positions": [], "warnings": []})}]}}]},
        request=httpx.Request("POST", "https://provider.invalid"))


def test_import_routes_require_login():
    assert client.post("/api/import/screenshot", json=image_request()).status_code == 401
    assert client.post("/api/import/positions", json={}).status_code == 401


def test_extract_preserves_unknown_fields_and_never_saves(setup, monkeypatch):
    call = Mock(return_value=provider(draft={"positions": [{"name": "Apple", "quantity": 5}], "warnings": []}))
    save = Mock()
    monkeypatch.setattr(importer.httpx, "post", call)
    monkeypatch.setattr("backend.main.save_import", save)
    result = client.post("/api/import/screenshot", json=image_request())
    assert result.status_code == 200
    row = result.json()["positions"][0]
    assert row["buy_price"] is None and row["buy_date"] is None and row["ticker"] is None
    assert row["quantity"] == 5
    assert call.call_args.kwargs["headers"]["x-goog-api-key"] == "test-secret"
    assert "responseSchema" in call.call_args.kwargs["json"]["generationConfig"]
    save.assert_not_called()


def test_invalid_or_mismatched_images_never_reach_provider(setup, monkeypatch):
    call = Mock()
    monkeypatch.setattr(importer.httpx, "post", call)
    assert client.post("/api/import/screenshot", json={"mime_type": "image/png", "image_base64": "broken"}).status_code == 422
    body = {**image_request(), "mime_type": "image/jpeg"}
    assert client.post("/api/import/screenshot", json=body).status_code == 422
    call.assert_not_called()


@pytest.mark.parametrize("status,finish,expected", [(429, "STOP", 429), (403, "STOP", 503), (404, "STOP", 503), (503, "STOP", 503), (200, "MAX_TOKENS", 502)])
def test_provider_errors_are_sanitized(setup, monkeypatch, status, finish, expected):
    monkeypatch.setattr(importer.httpx, "post", Mock(return_value=provider(status, finish=finish)))
    result = client.post("/api/import/screenshot", json=image_request())
    assert result.status_code == expected
    assert "test-secret" not in result.text


def test_missing_key_and_local_rate_limit(setup, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    assert client.post("/api/import/screenshot", json=image_request()).status_code == 503
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret")
    call = Mock(return_value=provider())
    monkeypatch.setattr(importer.httpx, "post", call)
    for _ in range(2):
        assert client.post("/api/import/screenshot", json=image_request()).status_code == 200
    assert client.post("/api/import/screenshot", json=image_request()).status_code == 429
    assert call.call_count == 2


def batch():
    return {"import_id": str(uuid4()), "positions": [
        {"ticker": "AAPL", "asset_type": "stock", "currency": "USD", "quantity": 2,
         "buy_price": 150, "buy_date": "2024-01-15"},
        {"ticker": "GGAL.BA", "asset_type": "stock", "currency": "ARS", "quantity": 3,
         "buy_price": 1000, "buy_date": "2024-01-15"}]}


def test_all_positions_validate_before_save_and_retries_have_stable_ids(setup, monkeypatch):
    save = Mock()
    monkeypatch.setattr("backend.main.save_import", save)
    monkeypatch.setattr("backend.main.get_currency", lambda t: "ARS" if t.endswith(".BA") else "USD")
    monkeypatch.setattr("backend.main.get_mep_on_date", lambda d: 100)
    body = batch()
    assert client.post("/api/import/positions", json=body).status_code == 200
    rows = save.call_args.args[1]
    assert rows[0]["buy_fx_rate"] == 1 and rows[1]["buy_fx_rate"] == 100
    assert all(row["user_id"] == USER.id for row in rows)
    assert client.post("/api/import/positions", json=body).status_code == 200
    assert save.call_args.args[1] == rows
    save.reset_mock()
    body["positions"][1]["currency"] = "USD"
    assert client.post("/api/import/positions", json=body).status_code == 422
    save.assert_not_called()
    body["positions"][0]["buy_date"] = "2099-01-01"
    assert client.post("/api/import/positions", json=body).status_code == 422
    save.assert_not_called()


def test_bulk_storage_uses_atomic_post_user_jwt_and_ignore_duplicates(setup, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public")
    call = Mock(return_value=httpx.Response(201, json=[], request=httpx.Request("POST", "https://test.invalid")))
    monkeypatch.setattr(storage.httpx, "request", call)
    rows = [{"id": str(uuid4()), "user_id": USER.id}]
    storage.save_import(USER, rows)
    assert call.call_count == 1
    assert call.call_args.args[0] == "POST"
    assert call.call_args.kwargs["json"] == rows
    assert call.call_args.kwargs["headers"]["Authorization"] == "Bearer test-jwt"
    assert "resolution=ignore-duplicates" in call.call_args.kwargs["headers"]["Prefer"]
