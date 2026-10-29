"""Supabase PostgREST access using the user's JWT, so RLS stays active."""
from typing import Any
from fastapi import HTTPException
import httpx
from ..auth import User
from ..config import supabase_config


def _request(user: User, method: str, **kwargs: Any) -> list[dict]:
    try:
        url, key = supabase_config()
        response = httpx.request(method, f"{url}/rest/v1/positions", headers={
            "apikey": key, "Authorization": f"Bearer {user.token}",
            "Prefer": "return=representation", "Content-Type": "application/json",
        }, timeout=15, **kwargs)
        if response.status_code in (401, 403):
            raise HTTPException(403, "No tenés acceso a estas posiciones.")
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        raise HTTPException(503, "No se pudo acceder a la base de datos de Supabase.") from exc


def list_positions(user: User) -> list[dict]:
    rows: list[dict] = []
    while True:
        page = _request(user, "GET", params={
            "user_id": f"eq.{user.id}", "select": "*", "order": "created_at.asc,id.asc",
            "limit": "500", "offset": str(len(rows)),
        })
        rows.extend(page)
        if len(page) < 500:
            return rows


def save_position(user: User, values: dict) -> dict:
    return _request(user, "POST", json={**values, "user_id": user.id})[0]


def delete_position(user: User, position_id: str) -> bool:
    return bool(_request(user, "DELETE", params={"id": f"eq.{position_id}", "user_id": f"eq.{user.id}"}))
