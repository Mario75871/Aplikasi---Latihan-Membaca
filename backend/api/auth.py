"""Auth API — Supabase Auth + JWT (Fase 2).

POST /auth/login memvalidasi kredensial lewat Supabase Auth dan mengembalikan
**JWT Supabase** (bukan token sesi in-memory). Bila Supabase tidak tersedia
(dev/lokal), memakai akun demo dari env var dan menerbitkan token lokal.

Verifikasi: `verify_token` memvalidasi JWT Supabase (stateless) — tidak ada sesi
in-memory yang hilang saat restart. Fallback token lokal (mode demo) tetap
didukung untuk pengembangan.

Jangan hardcode secret. Semua konfigurasi lewat env var.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "12"))

#: Prefix token lokal (mode demo, non-Supabase). Bukan JWT.
_LOCAL_TOKEN_PREFIX = "local-"
#: Store token lokal (mode demo saja) — dibutuhkan untuk verifikasi tanpa Supabase.
_local_tokens: dict[str, dict] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    expires_at: str


def _supabase_credentials() -> Optional[tuple[str, str]]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return (url, key) if (url and key) else None


def _validate_demo_credentials(username: str, password: str) -> bool:
    """Validasi kredensial demo dari env var (bukan hardcoded)."""
    demo_username = os.getenv("DEMO_USERNAME", "guru@demo.com")
    demo_password = os.getenv("DEMO_PASSWORD", "demo123")
    return username == demo_username and password == demo_password


def _supabase_login(username: str, password: str, display_name: Optional[str] = None) -> Optional[dict]:
    """Login Supabase Auth. Mengembalikan dict {token, user_id, email, expires_at}.

    Args:
        display_name: nama tampilan untuk baris `public.users` yang baru dibuat.
            Hanya dipakai pendaftaran (`api/signup.py`) — pada login biasa dibiarkan
            None sehingga nama yang sudah ada tidak tertimpa.

    Returns:
        dict bila berhasil, None bila Supabase tidak tersedia.
    Raises:
        HTTPException 401 bila kredensial Supabase ditolak.
    """
    creds = _supabase_credentials()
    if not creds:
        return None
    url, key = creds
    try:
        from supabase import create_client
        client = create_client(url, key)
        resp = client.auth.sign_in_with_password({"email": username, "password": password})
    except Exception as e:
        print(f"[auth] Supabase auth failed: {e}")
        raise HTTPException(status_code=401, detail="Kredensial tidak valid")

    if resp is None or resp.user is None:
        raise HTTPException(status_code=401, detail="Kredensial tidak valid")

    session = getattr(resp, "session", None)
    token = getattr(session, "access_token", None)
    if not token:
        raise HTTPException(status_code=401, detail="Supabase tidak mengembalikan token sesi")

    expires_at = getattr(session, "expires_at", None)
    if expires_at:
        expires_iso = datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
    else:
        expires_iso = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).isoformat()

    ok = _sync_public_user(client, resp.user, display_name)
    if not ok:
        # D2: profil gagal disinkronkan → jangan lanjut dengan profil hilang.
        raise HTTPException(
            status_code=503,
            detail=(
                "Login berhasil, tetapi profil guru tidak dapat disiapkan "
                "(public.users). Hubungi administrator atau coba lagi."
            ),
        )
    return {
        "token": token,
        "user_id": str(resp.user.id),
        "email": getattr(resp.user, "email", username),
        "expires_at": expires_iso,
    }


def _sync_public_user(client, user, display_name: Optional[str] = None) -> bool:
    """Upsert baris `public.users` (id = auth.users.id) untuk join classes.teacher_id.

    Integrasi #3, D2: TIDAK senyap lagi. Mengembalikan True bila berhasil. Kegagalan
    dicatat (log level error) agar dapat ditangani pemanggil — bukan ditelan diam-diam.

    Args:
        display_name: bila diisi, dipakai sebagai `name`. Pendaftaran mengirim nama
            asli dari formulir; login biasa membiarkannya None agar `name` yang sudah
            ada dipertahankan (dan baris baru jatuh ke email seperti sebelumnya).
    """
    try:
        client.table("users").upsert(
            {
                "id": str(user.id),
                "name": display_name or getattr(user, "email", "") or "Guru",
                "email": getattr(user, "email", "") or str(user.id),
            },
            on_conflict="id",
        ).execute()
        return True
    except Exception as e:
        print(f"[auth] ERROR: gagal sinkronisasi public.users: {e}")
        return False


def _issue_demo_token(username: str) -> dict:
    """Terbitkan token lokal (mode demo, tanpa Supabase)."""
    token = _LOCAL_TOKEN_PREFIX + secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
    _local_tokens[token] = {"username": username, "expires_at": expires_at.isoformat()}
    return {
        "token": token,
        "username": username,
        "expires_at": expires_at.isoformat(),
    }


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """POST /auth/login — validasi kredensial, kembalikan JWT (Supabase) / token demo."""
    if not req.username or not req.password:
        raise HTTPException(status_code=422, detail="Username dan password wajib diisi")

    # Coba Supabase Auth dulu (bila env tersedia).
    supabase_result = _supabase_login(req.username, req.password)
    if supabase_result is not None:
        return LoginResponse(
            token=supabase_result["token"],
            username=supabase_result["email"],
            expires_at=supabase_result["expires_at"],
        )

    # Fallback: akun demo dari env (lokal/dev).
    if not _validate_demo_credentials(req.username, req.password):
        raise HTTPException(status_code=401, detail="Kredensial tidak valid")

    issued = _issue_demo_token(req.username)
    return LoginResponse(**issued)


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    """POST /auth/logout — akhiri sesi lokal (JWT Supabase stateless)."""
    token = _extract_token(authorization)
    if token and token in _local_tokens:
        del _local_tokens[token]
    return {"status": "ok", "message": "Sesi berakhir"}


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    """Ekstrak token dari header Authorization: Bearer <token>."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def _verify_supabase_jwt(token: str) -> Optional[dict]:
    """Verifikasi JWT Supabase. Mengembalikan user dict bila valid, else None."""
    creds = _supabase_credentials()
    if not creds:
        return None
    url, key = creds
    try:
        from supabase import create_client
        client = create_client(url, key)
        resp = client.auth.get_user(token)
        user = getattr(resp, "user", None)
        if user is None:
            return None
        return {"username": getattr(user, "email", "") or str(user.id), "user_id": str(user.id)}
    except Exception:
        return None


def verify_token(authorization: Optional[str]) -> dict:
    """Verifikasi token (JWT Supabase atau token demo). Raise 401 bila invalid."""
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan. Silakan login.")

    # Token demo lokal (mode tanpa Supabase).
    if token.startswith(_LOCAL_TOKEN_PREFIX):
        session = _local_tokens.get(token)
        if not session:
            raise HTTPException(status_code=401, detail="Sesi tidak valid. Silakan login.")
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            del _local_tokens[token]
            raise HTTPException(status_code=401, detail="Sesi kedaluwarsa. Silakan login.")
        return session

    # JWT Supabase (stateless).
    user = _verify_supabase_jwt(token)
    if user is not None:
        return user

    # Supabase tidak tersedia → tolak (tidak ada sesi in-memory lagi).
    raise HTTPException(status_code=401, detail="Token tidak valid. Silakan login.")


def reset_sessions():
    """Reset token demo store (untuk test)."""
    _local_tokens.clear()


# ============================================================
# Integrasi #3 (A.1/A.3, D2) — dependencies identitas guru
# ============================================================

def _demo_teacher_id() -> str:
    """ID guru demo (mode lokal) — dari seed agar data seed punya pemilik."""
    try:
        from seed.reading_texts import SEED_IDS
        return SEED_IDS["teacher_demo"]
    except Exception:
        return "00000000-0000-0000-0000-000000000301"


def get_current_user(request: Request) -> dict:
    """Ambil identitas dari request.state (diisi middleware). Raise 401 bila tak ada.

    Bila `AUTH_DISABLED=true` (test/dev), middleware dilewati → pakai identitas demo
    agar endpoint tetap dapat dipanggil tanpa login (perilaku lama dipertahankan).
    """
    user = getattr(request.state, "user", None)
    if user:
        return user
    if os.getenv("AUTH_DISABLED", "false").lower() == "true":
        return {"username": "demo", "user_id": None}
    raise HTTPException(status_code=401, detail="Autentikasi diperlukan.")


def require_teacher(request: Request) -> str:
    """Kembalikan `teacher_id` (public.users.id) untuk scoping per-guru (D2).

    - Mode demo (token lokal): pakai teacher_demo dari seed.
    - Supabase: pakai user_id dari JWT. Bila profil `public.users` belum ada,
      coba buat ulang dari klaim token; bila tetap gagal → 503 dengan pesan jelas.
    """
    user = get_current_user(request)
    user_id = user.get("user_id")

    # Mode demo tanpa Supabase → guru demo.
    if not user_id:
        return _demo_teacher_id()

    # Mode Supabase: pastikan profil ada (pemulihan D2).
    creds = _supabase_credentials()
    if not creds:
        return user_id  # dev tanpa Supabase: percaya JWT

    try:
        from supabase import create_client
    except Exception:
        return user_id

    try:
        url, key = creds
        client = create_client(url, key)
        # Integrasi #6 (fix 503): tempelkan JWT guru agar RLS `auth.uid()` terisi.
        # Tanpa ini, select profil SELALU kosong (RLS users: id = auth.uid()) → upsert
        # gagal → 503 untuk SEMUA endpoint guru mode Supabase.
        token = _extract_token(request.headers.get("Authorization"))
        if token:
            try:
                client.postgrest.auth(token)
            except Exception:
                pass
        resp = client.table("users").select("id").eq("id", user_id).execute()
        if resp.data:
            return user_id
        # Profil belum ada → coba buat ulang dari klaim token (D2).
        try:
            client.table("users").upsert(
                {
                    "id": user_id,
                    "name": user.get("username") or "Guru",
                    "email": user.get("username") or user_id,
                },
                on_conflict="id",
            ).execute()
            return user_id
        except Exception as e:
            print(f"[auth] ERROR: gagal memulihkan profil public.users: {e}")
            raise HTTPException(
                status_code=503,
                detail="Profil guru belum siap dan tidak dapat dibuat ulang.",
            )
    except HTTPException:
        raise
    except Exception as e:
        # Bila pemeriksaan gagal karena jaringan dsb., tetap izinkan (RLS di DB tetap
        # menjadi lapis kedua). Catat untuk observability.
        print(f"[auth] peringatan: cek profil gagal ({e}); melanjutkan dengan user_id.")
        return user_id
