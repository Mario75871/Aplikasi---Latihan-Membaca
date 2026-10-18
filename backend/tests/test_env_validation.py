"""Test validasi env saat startup (integrasi #4, C.3; pendaftaran di integrasi #7)."""
from __future__ import annotations

import pytest

from api.env_validation import current_env, is_production, validate_environment

#: Nama env yang dibersihkan sebelum tiap test, agar hasilnya tidak bergantung
#: pada lingkungan mesin yang menjalankan test.
_MANAGED_ENV = (
    "ENV", "CORS_ORIGINS", "SUPABASE_KEY",
    "SUPABASE_SERVICE_ROLE_KEY", "AUTH_DISABLED",
    "SESSION_COOKIE_SECURE",
    # Integrasi #7 — pendaftaran akun.
    "RESEND_API_KEY", "MAIL_FROM", "SIGNUP_OTP_SECRET",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in _MANAGED_ENV:
        monkeypatch.delenv(k, raising=False)
    yield


def _set_valid_signup_env(monkeypatch):
    """Env pendaftaran yang lengkap & kuat."""
    monkeypatch.setenv("RESEND_API_KEY", "re_contoh")
    monkeypatch.setenv("MAIL_FROM", "BacaLaras <noreply@bacalaras.my.id>")
    monkeypatch.setenv("SIGNUP_OTP_SECRET", "x" * 48)


def test_default_env_is_development():
    assert current_env() == "development"
    assert not is_production()


def test_wildcard_cors_fails(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError):
        validate_environment()


def test_anon_equals_service_role_fails(monkeypatch):
    monkeypatch.setenv("SUPABASE_KEY", "same")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "same")
    with pytest.raises(RuntimeError):
        validate_environment()


def test_production_rejects_auth_disabled(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("AUTH_DISABLED", "true")
    with pytest.raises(RuntimeError):
        validate_environment()


def test_production_requires_secure_cookie(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    with pytest.raises(RuntimeError):
        validate_environment()


def test_production_valid_config_passes(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.id")
    _set_valid_signup_env(monkeypatch)
    assert validate_environment() == []


def test_development_warns_on_insecure_cookie(monkeypatch):
    warnings = validate_environment()
    assert any("SESSION_COOKIE_SECURE" in w for w in warnings)


# ---------- Pendaftaran akun (integrasi #7): peringatan, BUKAN fatal ----------

def test_env_pendaftaran_kosong_hanya_memperingatkan(monkeypatch):
    """Penyedia email yang bermasalah tidak boleh menjatuhkan login yang sudah jalan."""
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.id")

    warnings = validate_environment()  # tidak melempar
    assert any("RESEND_API_KEY" in w for w in warnings)
    assert any("SIGNUP_OTP_SECRET" in w for w in warnings)


def test_secret_pendaftaran_pendek_diperingatkan_di_produksi(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.id")
    monkeypatch.setenv("RESEND_API_KEY", "re_contoh")
    monkeypatch.setenv("MAIL_FROM", "noreply@bacalaras.my.id")
    monkeypatch.setenv("SIGNUP_OTP_SECRET", "pendek")

    warnings = validate_environment()
    assert any("minimal 32" in w for w in warnings)


def test_env_pendaftaran_lengkap_di_produksi_tanpa_peringatan(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.id")
    _set_valid_signup_env(monkeypatch)

    assert not any("SIGNUP" in w or "RESEND" in w for w in validate_environment())
