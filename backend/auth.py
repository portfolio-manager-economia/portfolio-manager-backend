"""Verify each bearer token with Supabase Auth; never trust decoded claims alone."""
from dataclasses import dataclass
from uuid import UUID
import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import supabase_config

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class User:
    id: str
    token: str


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    if credentials is None:
        raise HTTPException(401, "Iniciá sesión para acceder a tu cartera.", headers={"WWW-Authenticate": "Bearer"})
    try:
        url, key = supabase_config()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    try:
        response = httpx.get(f"{url}/auth/v1/user", headers={
            "apikey": key, "Authorization": f"Bearer {credentials.credentials}",
        }, timeout=10)
        if response.status_code in (401, 403):
            raise HTTPException(401, "Tu sesión venció. Volvé a iniciar sesión.")
        response.raise_for_status()
        user_id = str(UUID(response.json()["id"]))
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(503, "No se pudo verificar la sesión con Supabase.") from exc
    return User(user_id, credentials.credentials)
