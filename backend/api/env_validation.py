"""Validasi konfigurasi env saat startup (integrasi #4, Fase C.3 / P1).

Fail-fast: menolak konfigurasi berbahaya agar tidak "diam-diam" berjalan di produksi.
Dipanggil dari `main.lifespan`. Melempar ``RuntimeError`` bila tidak aman.

Yang dicek:
- ``CORS_ORIGINS`` mengandung ``*`` (tidak boleh untuk produksi / kredensial).
- ``SUPABASE_KEY`` == ``SUPABASE_SERVICE_ROLE_KEY`` (anon == service-role → bahaya).
- ``AUTH_DISABLED=true`` saat ``ENV=production`` (auth wajib di produksi).
- ``ENV=production`` tanpa TLS saat cookie ``Secure`` dinonaktifkan.

Peringatan non-fatal (integrasi #7):
- ``RESEND_API_KEY`` / ``MAIL_FROM`` / ``SIGNUP_OTP_SECRET`` kosong → fitur daftar
  akun nonaktif, tetapi aplikasi tetap jalan. Disengaja: kegagalan penyedia email
  tidak boleh menjatuhkan login guru yang sudah berjalan.
"""
from __future__ import annotations

import os

#: Nilai ENV yang dikenali.
ENVS = ("development", "staging", "production")


def current_env() -> str:
    """ENV aktif (default 'development')."""
    env = os.getenv("ENV", "development").strip().lower()
    return env if env in ENVS else "development"


def is_production() -> bool:
    return current_env() == "production"


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() == "true"


def validate_environment() -> list[str]:
    """Validasi konfigurasi. Kembalikan daftar PERINGATAN (non-fatal).

    Raises:
        RuntimeError: konfigurasi berbahaya (fatal) — startup harus gagal.
    """
    problems: list[str] = []
    warnings: list[str] = []

    cors_raw = os.getenv("CORS_ORIGINS", "")
    cors = [o.strip() for o in cors_raw.split(",") if o.strip()]
    if any(o == "*" for o in cors):
        problems.append(
            "CORS_ORIGINS tidak boleh berisi '*' (khususnya dengan kredensial). "
            "Sebutkan origin eksplisit, mis. https://app.example.id."
        )

    anon = os.getenv("SUPABASE_KEY")
    service = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if anon and service and anon == service:
        problems.append(
            "SUPABASE_KEY (anon) tidak boleh sama dengan SUPABASE_SERVICE_ROLE_KEY. "
            "Ini akan melewati RLS untuk semua permintaan guru."
        )

    if is_production():
        if _bool_env("AUTH_DISABLED"):
            problems.append("AUTH_DISABLED=true tidak diizinkan saat ENV=production.")
        # Produksi butuh TLS; cookie Secure hanya bisa benar bila HTTPS ada.
        if not _bool_env("SESSION_COOKIE_SECURE"):
            problems.append(
                "ENV=production tetapi SESSION_COOKIE_SECURE tidak diaktifkan. "
                "Pasang TLS (reverse proxy) lalu set SESSION_COOKIE_SECURE=true."
            )
    else:
        if not _bool_env("SESSION_COOKIE_SECURE"):
            warnings.append(
                "SESSION_COOKIE_SECURE=false (HTTP). Hanya untuk lokal/staging internal — "
                "jangan pakai data siswa nyata tanpa TLS."
            )

    if problems:
        raise RuntimeError(
            "Konfigurasi env tidak valid:\n- " + "\n- ".join(problems)
        )

    # ---------- Pendaftaran akun (integrasi #7) ----------
    # Hanya PERINGATAN, sengaja bukan fatal: penyedia email yang sedang bermasalah
    # tidak boleh ikut menjatuhkan login guru yang sudah berjalan. Bila env ini
    # kosong, endpoint /auth/signup/* membalas 503 dengan pesan yang jelas.
    if not os.getenv("RESEND_API_KEY") or not os.getenv("MAIL_FROM"):
        warnings.append(
            "RESEND_API_KEY / MAIL_FROM belum diisi — fitur daftar akun nonaktif "
            "(/auth/signup/* membalas 503). Login yang sudah ada tidak terpengaruh."
        )
    if not os.getenv("SIGNUP_OTP_SECRET"):
        warnings.append(
            "SIGNUP_OTP_SECRET belum diisi — verifikasi OTP pendaftaran nonaktif. "
            "Isi dengan nilai acak 32+ byte; JANGAN pakai nilai yang bisa ditebak."
        )
    elif is_production() and len(os.getenv("SIGNUP_OTP_SECRET", "")) < 32:
        warnings.append(
            "SIGNUP_OTP_SECRET di produksi sebaiknya minimal 32 karakter."
        )

    return warnings
