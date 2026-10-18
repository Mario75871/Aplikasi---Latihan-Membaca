"""Test anti-drift konstanta audio lintas-sisi + batas durasi (integrasi #5, A.2/A.3).

Menutup aturan #13/#14 (TARGET_SAMPLE_RATE, MAX_AUDIO_BYTES) dan #15 (durasi)
matriks §3 integration_5.md. Nilai backend = satu sumber (`services/audio_validation`),
dibandingkan dengan konstanta frontend `lib/audio-wav.ts`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from services.audio_validation import (
    AudioValidationError,
    DEFAULT_MAX_AUDIO_BYTES,
    DEFAULT_MAX_AUDIO_DURATION_SEC,
    DEFAULT_TARGET_SAMPLE_RATE,
    max_audio_bytes,
    max_audio_duration_sec,
    target_sample_rate,
    validate_audio_duration,
)

_AUDIO_WAV_TS = (
    Path(__file__).resolve().parents[2] / "frontend" / "lib" / "audio-wav.ts"
)
_API_TS = Path(__file__).resolve().parents[2] / "frontend" / "lib" / "api.ts"
_RECORD_TSX = (
    Path(__file__).resolve().parents[2]
    / "frontend" / "app" / "assess" / "record" / "RecordScreen.tsx"
)


# ── Anti-drift: konstanta frontend harus mencerminkan backend ──

def test_frontend_target_sample_rate_matches_backend():
    """aturan #13: TARGET_SAMPLE_RATE frontend == backend."""
    if not _AUDIO_WAV_TS.exists():
        pytest.skip("frontend/lib/audio-wav.ts tidak tersedia")
    text = _AUDIO_WAV_TS.read_text()
    m = re.search(r"TARGET_SAMPLE_RATE\s*=\s*(\d+)", text)
    assert m, "TARGET_SAMPLE_RATE tidak ditemukan di audio-wav.ts"
    assert int(m.group(1)) == target_sample_rate() == DEFAULT_TARGET_SAMPLE_RATE == 16000


def test_frontend_max_audio_bytes_matches_backend():
    """aturan #14: MAX_AUDIO_BYTES frontend == backend (10 MB)."""
    if not _AUDIO_WAV_TS.exists():
        pytest.skip("frontend/lib/audio-wav.ts tidak tersedia")
    text = _AUDIO_WAV_TS.read_text()
    m = re.search(r"MAX_AUDIO_BYTES\s*=\s*([\d\s*]+)", text)
    assert m, "MAX_AUDIO_BYTES tidak ditemukan di audio-wav.ts"
    # Ekspresi seperti "10 * 1024 * 1024".
    expr = m.group(1).strip()
    value = 1
    for factor in expr.split("*"):
        value *= int(factor.strip())
    assert value == max_audio_bytes() == DEFAULT_MAX_AUDIO_BYTES


def test_audio_defaults():
    """Default tidak berubah diam-diam (kontrak)."""
    assert DEFAULT_TARGET_SAMPLE_RATE == 16000
    assert DEFAULT_MAX_AUDIO_BYTES == 10 * 1024 * 1024
    assert DEFAULT_MAX_AUDIO_DURATION_SEC == 300


# ── Batas durasi (integrasi #5, A.2) ──

def test_validate_audio_duration_ok():
    """Durasi di bawah/​sama dengan batas → lolos (tidak raise)."""
    validate_audio_duration(1.0)
    validate_audio_duration(float(DEFAULT_MAX_AUDIO_DURATION_SEC))
    validate_audio_duration(None)  # tak tersedia → JANGAN tolak (null != 0)


def test_validate_audio_duration_exceeds_422(monkeypatch):
    """Durasi > batas → AudioValidationError 422."""
    monkeypatch.setenv("MAX_AUDIO_DURATION_SEC", "300")
    with pytest.raises(AudioValidationError) as e:
        validate_audio_duration(300.5)
    assert e.value.status_code == 422
    assert "melebihi batas" in e.value.detail


def test_validate_audio_duration_none_not_rejected(monkeypatch):
    """Durasi None (ffprobe gagal) TIDAK ditolak — konsisten null != 0."""
    monkeypatch.setenv("MAX_AUDIO_DURATION_SEC", "1")
    validate_audio_duration(None)  # tidak raise meski batas sangat kecil


def test_max_audio_duration_env_override(monkeypatch):
    monkeypatch.setenv("MAX_AUDIO_DURATION_SEC", "60")
    assert max_audio_duration_sec() == 60
    # Nilai tidak valid → fallback default.
    monkeypatch.setenv("MAX_AUDIO_DURATION_SEC", "abc")
    assert max_audio_duration_sec() == DEFAULT_MAX_AUDIO_DURATION_SEC
    monkeypatch.setenv("MAX_AUDIO_DURATION_SEC", "-5")
    assert max_audio_duration_sec() == DEFAULT_MAX_AUDIO_DURATION_SEC


# ── Konsumsi runtime (integrasi #6, B.2): cegah regresi "endpoint tanpa konsumen" ──

def test_frontend_max_audio_duration_matches_backend():
    """aturan #15 (runtime): MAX_AUDIO_DURATION_SEC frontend == backend."""
    if not _AUDIO_WAV_TS.exists():
        pytest.skip("frontend/lib/audio-wav.ts tidak tersedia")
    text = _AUDIO_WAV_TS.read_text()
    m = re.search(r"MAX_AUDIO_DURATION_SEC\s*=\s*(\d+)", text)
    assert m, "MAX_AUDIO_DURATION_SEC tidak ditemukan di audio-wav.ts"
    assert int(m.group(1)) == max_audio_duration_sec() == DEFAULT_MAX_AUDIO_DURATION_SEC


def test_frontend_consumes_audio_config_endpoint():
    """Integrasi #6 (B.2): FE HARUS mengonsumsi `GET /config/audio` (bukan hanya test)."""
    if not _API_TS.exists():
        pytest.skip("frontend/lib/api.ts tidak tersedia")
    assert "/config/audio" in _API_TS.read_text(), "FE tidak mengonsumsi /config/audio"
    assert "getAudioConfig" in _API_TS.read_text(), "fungsi getAudioConfig tidak ada"


def test_record_screen_enforces_duration():
    """Integrasi #6 (D1): layar rekam menegakkan batas durasi di klien (cegah 422)."""
    if not _RECORD_TSX.exists():
        pytest.skip("frontend/app/assess/record/RecordScreen.tsx tidak tersedia")
    text = _RECORD_TSX.read_text()
    assert "MAX_AUDIO_DURATION_SEC" in text, "RecordScreen tak pakai konstanta durasi"
    assert "durationError" in text, "RecordScreen tak menangani pelanggaran durasi"
