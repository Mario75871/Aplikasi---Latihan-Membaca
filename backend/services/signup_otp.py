"""Inti keamanan pendaftaran akun: kode OTP + tiket verifikasi.

Alur tiga langkah (lihat `api/signup.py`):
  1. ``/start``    → :func:`generate_code` → hash disimpan di tabel ``signup_otp`` → email dikirim
  2. ``/verify``   → bandingkan hash (constant-time) → :func:`issue_ticket`
  3. ``/complete`` → :func:`verify_ticket` → buat user di Supabase Auth

**Kenapa tiket, bukan sesi.** Setelah OTP terverifikasi, pengguna belum boleh dianggap
login — password-nya belum ada. Tiket hanya membuktikan "email ini sudah diverifikasi",
berumur pendek, dan **tidak memberi akses apa pun** ke API (bukan JWT Supabase, tidak
dikenali `api/auth.py:verify_token`). Akun baru benar-benar lahir di langkah 3.

**Yang tidak pernah disimpan:** kode OTP mentah. Yang tersimpan hanya HMAC-nya, jadi isi
tabel tetap tidak berguna walau bocor.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

#: Label konteks HMAC — mencegah tanda tangan satu keperluan dipakai untuk keperluan lain.
_CODE_CONTEXT = b"bacalaras-signup-code:"
_TICKET_CONTEXT = b"bacalaras-signup-ticket:"


class SignupNotConfigured(RuntimeError):
    """Env pendaftaran belum lengkap — fitur daftar akun nonaktif."""


# ─────────────────────────────────────────────────────────────
# Konfigurasi
# ─────────────────────────────────────────────────────────────

def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        val = int(raw)
        return val if val > 0 else default
    except ValueError:
        return default


def otp_ttl_sec() -> int:
    """Masa berlaku kode OTP (detik). Default 10 menit."""
    return _int_env("SIGNUP_OTP_TTL_SEC", 600)


def max_attempts() -> int:
    """Batas percobaan verifikasi per kode, sebelum kode dianggap hangus."""
    return _int_env("SIGNUP_OTP_MAX_ATTEMPTS", 5)


def ticket_ttl_sec() -> int:
    """Masa berlaku tiket antara verifikasi OTP dan pembuatan password."""
    return _int_env("SIGNUP_TICKET_TTL_SEC", 900)


def _secret() -> bytes:
    """Kunci HMAC. **Tanpa nilai default** — kunci yang bisa ditebak lebih buruk
    daripada fitur yang mati."""
    raw = os.getenv("SIGNUP_OTP_SECRET")
    if not raw:
        raise SignupNotConfigured("SIGNUP_OTP_SECRET belum diisi.")
    return raw.encode()


def signup_configured() -> bool:
    """True bila seluruh env yang dibutuhkan pendaftaran tersedia."""
    from services.email import email_configured

    return (
        bool(os.getenv("SIGNUP_OTP_SECRET"))
        and email_configured()
        and bool(os.getenv("SUPABASE_URL"))
        and bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    )


def normalize_email(email: str) -> str:
    """Samakan bentuk email agar pencocokan kode tidak sensitif huruf besar/kecil."""
    return email.strip().lower()


def expires_at_iso(ttl_sec: int) -> str:
    """ISO-8601 UTC untuk `ttl_sec` detik dari sekarang."""
    return datetime.fromtimestamp(int(time.time()) + ttl_sec, tz=timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────
# Kode OTP
# ─────────────────────────────────────────────────────────────

def generate_code() -> str:
    """Kode 6 digit yang seragam (000000–999999) dari sumber acak kriptografis."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(email: str, code: str) -> str:
    """HMAC kode terhadap alamat emailnya.

    Email diikat ke dalam hash supaya kode yang diterbitkan untuk satu alamat tidak
    bisa dipakai untuk alamat lain.
    """
    msg = f"{normalize_email(email)}:{code}".encode()
    return hmac.new(_secret(), _CODE_CONTEXT + msg, hashlib.sha256).hexdigest()


def code_matches(email: str, code: str, stored_hash: str) -> bool:
    """Bandingkan kode dengan hash tersimpan secara constant-time."""
    return hmac.compare_digest(hash_code(email, code), stored_hash or "")


# ─────────────────────────────────────────────────────────────
# Tiket verifikasi (stateless, bertanda tangan)
# ─────────────────────────────────────────────────────────────

def issue_ticket(email: str, name: str) -> tuple[str, str]:
    """Terbitkan tiket bertanda tangan. Kembalikan ``(tiket, kedaluwarsa_iso)``.

    Stateless: tidak ada yang disimpan di server, jadi tiket tetap sah setelah
    backend di-restart (berbeda dari sesi in-memory yang sengaja dihindari).
    """
    exp = int(time.time()) + ticket_ttl_sec()
    payload = {"email": normalize_email(email), "name": name, "exp": exp}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    b64 = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig = hmac.new(_secret(), _TICKET_CONTEXT + b64.encode(), hashlib.sha256).hexdigest()
    # Dihitung dari `exp` yang sama, bukan dari time.time() baru — supaya waktu
    # kedaluwarsa yang dilaporkan persis sama dengan yang ditandatangani.
    expires_iso = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
    return f"{b64}.{sig}", expires_iso


def verify_ticket(ticket: str) -> dict:
    """Verifikasi tanda tangan & masa berlaku tiket.

    Returns:
        dict ``{"email": ..., "name": ...}``.

    Raises:
        SignupNotConfigured: ``SIGNUP_OTP_SECRET`` kosong.
        ValueError: tiket rusak, tanda tangan tidak cocok, atau kedaluwarsa.
            (Pemanggil menerjemahkannya menjadi HTTP 401.)
    """
    if not ticket or ticket.count(".") != 1:
        raise ValueError("Tiket tidak valid.")
    b64, sig = ticket.split(".", 1)

    expected = hmac.new(_secret(), _TICKET_CONTEXT + b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("Tiket tidak valid.")

    try:
        padded = b64 + "=" * (-len(b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except Exception as e:
        raise ValueError("Tiket tidak valid.") from e

    if not isinstance(payload, dict) or "email" not in payload:
        raise ValueError("Tiket tidak valid.")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("Tiket sudah kedaluwarsa. Silakan ulangi pendaftaran.")

    return {"email": payload["email"], "name": payload.get("name") or ""}


# ─────────────────────────────────────────────────────────────
# Penyimpanan (service-role; tabel `signup_otp` tanpa policy RLS)
# ─────────────────────────────────────────────────────────────

def _admin_client():
    """Klien Supabase service-role — melewati RLS, server-only.

    Dipisah menjadi fungsi sendiri agar test dapat menggantinya (monkeypatch)
    tanpa menyentuh jaringan.
    """
    from repository import get_admin_repository

    return get_admin_repository().client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def email_registered(email: str) -> bool:
    """True bila email sudah dipakai akun lain (dicek di tabel cermin `public.users`).

    Ini lapis pertama demi pesan galat yang jelas. Lapis kedua yang **otoritatif**
    ada di Supabase Auth: ``admin.create_user`` menolak email yang sudah terdaftar,
    dan itu ditangani di langkah ``/complete``.
    """
    resp = (
        _admin_client()
        .table("users")
        .select("id")
        .eq("email", normalize_email(email))
        .limit(1)
        .execute()
    )
    return bool(resp.data)


def invalidate_open_challenges(email: str) -> None:
    """Hanguskan kode lama yang belum terpakai sebelum menerbitkan kode baru.

    Mencegah beberapa kode aktif sekaligus untuk satu alamat.
    """
    (
        _admin_client()
        .table("signup_otp")
        .update({"consumed_at": _now_iso()})
        .eq("email", normalize_email(email))
        .is_("consumed_at", "null")
        .execute()
    )


def store_challenge(
    email: str, code_hash: str, name: str, expires_at: str, request_ip: Optional[str]
) -> None:
    """Simpan satu tantangan OTP (hanya hash-nya)."""
    (
        _admin_client()
        .table("signup_otp")
        .insert(
            {
                "email": normalize_email(email),
                "code_hash": code_hash,
                "name": name or None,
                "expires_at": expires_at,
                "request_ip": request_ip,
            }
        )
        .execute()
    )


def latest_open_challenge(email: str) -> Optional[dict]:
    """Tantangan terbaru yang belum terpakai & belum kedaluwarsa untuk `email`."""
    resp = (
        _admin_client()
        .table("signup_otp")
        .select("*")
        .eq("email", normalize_email(email))
        .is_("consumed_at", "null")
        .gt("expires_at", _now_iso())
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def bump_attempts(challenge_id: str, attempts: int) -> None:
    """Catat satu percobaan verifikasi gagal."""
    _admin_client().table("signup_otp").update({"attempts": attempts}).eq(
        "id", challenge_id
    ).execute()


def consume_challenge(challenge_id: str) -> None:
    """Tandai tantangan terpakai — kode menjadi sekali pakai."""
    _admin_client().table("signup_otp").update({"consumed_at": _now_iso()}).eq(
        "id", challenge_id
    ).execute()
