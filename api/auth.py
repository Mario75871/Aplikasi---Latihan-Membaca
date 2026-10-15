"""Auth API — sederhana (D7).

POST /auth/login memvalidasi kredensial (Supabase Auth bila env tersedia,
selain itu akun demo dari env var) dan mengembalikan token sesi.

Jangan hardcode secret. Semua konfigurasi lewat env var.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory session store (MVP). Di produksi: Supabase Auth atau JWT.
_sessions: dict[str, dict] = {}

SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "12"))


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    expires_at: str


def _validate_demo_credentials(username: str, password: str) -> bool:
    """Validasi kredensial demo dari env var (bukan hardcoded)."""
    demo_username = os.getenv("DEMO_USERNAME", "guru@demo.com")
    demo_password = os.getenv("DEMO_PASSWORD", "demo123")
    return username == demo_username and password == demo_password


def _validate_supabase(username: str, password: str) -> Optional[bool]:
    """Validasi lewat Supabase Auth bila env tersedia.
    
    Returns:
        True bila valid, False bila invalid, None bila Supabase tidak tersedia.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not (supabase_url and supabase_key):
        return None
    
    try:
        from supabase import create_client
        client = create_client(supabase_url, supabase_key)
        resp = client.auth.sign_in_with_password({"email": username, "password": password})
        return resp.user is not None
    except Exception as e:
        print(f"[auth] Supabase auth failed: {e}")
        return False


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """POST /auth/login — validasi kredensial, kembalikan token sesi."""
    if not req.username or not req.password:
        raise HTTPException(status_code=422, detail="Username dan password wajib diisi")
    
    # Coba Supabase dulu, fallback ke demo
    supabase_result = _validate_supabase(req.username, req.password)
    
    if supabase_result is True:
        valid = True
    elif supabase_result is False:
        valid = False
    else:
        # Supabase tidak tersedia → akun demo dari env
        valid = _validate_demo_credentials(req.username, req.password)
    
    if not valid:
        raise HTTPException(status_code=401, detail="Kredensial tidak valid")
    
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
    
    _sessions[token] = {
        "username": req.username,
        "expires_at": expires_at.isoformat(),
    }
    
    return LoginResponse(
        token=token,
        username=req.username,
        expires_at=expires_at.isoformat(),
    )


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    """POST /auth/logout — akhiri sesi."""
    token = _extract_token(authorization)
    if token and token in _sessions:
        del _sessions[token]
    return {"status": "ok", "message": "Sesi berakhir"}


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    """Ekstrak token dari header Authorization: Bearer <token>."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def verify_token(authorization: Optional[str]) -> dict:
    """Verifikasi token sesi. Raise HTTPException 401 bila invalid/expired."""
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan. Silakan login.")
    
    session = _sessions.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Sesi tidak valid. Silakan login.")
    
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        del _sessions[token]
        raise HTTPException(status_code=401, detail="Sesi kedaluwarsa. Silakan login.")
    
    return session


def reset_sessions():
    """Reset session store (untuk test)."""
    _sessions.clear()
