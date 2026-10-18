"""Test validasi upload audio (integrasi #3, Fase C / D4).

Format yang diizinkan: WAV & MP3 saja. Batas: 10 MB (MAX_AUDIO_BYTES).
Validasi memakai magic bytes, bukan nama file.
"""
import pytest

from services.audio_validation import (
    ALLOWED_FORMATS,
    DEFAULT_MAX_AUDIO_BYTES,
    DEFAULT_TARGET_SAMPLE_RATE,
    AudioValidationError,
    max_audio_bytes,
    suffix_for_format,
    target_sample_rate,
    validate_audio_bytes,
    warn_if_oversampled,
    wav_sample_rate,
)
from tests.conftest import wav_bytes


def test_default_limit_is_10mb(monkeypatch):
    monkeypatch.delenv("MAX_AUDIO_BYTES", raising=False)
    assert max_audio_bytes() == DEFAULT_MAX_AUDIO_BYTES == 10 * 1024 * 1024


def test_env_override_limit(monkeypatch):
    monkeypatch.setenv("MAX_AUDIO_BYTES", "2048")
    assert max_audio_bytes() == 2048


def test_valid_wav_passes():
    payload = wav_bytes()
    assert validate_audio_bytes(payload[:12], len(payload)) == "wav"


def test_valid_mp3_id3_passes():
    payload = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 100
    assert validate_audio_bytes(payload[:12], len(payload)) == "mp3"


def test_valid_mp3_frame_sync_passes():
    payload = b"\xff\xfb\x90\x00" + b"\x00" * 100
    assert validate_audio_bytes(payload[:12], len(payload)) == "mp3"


def test_webm_rejected_415():
    payload = b"\x1a\x45\xdf\xa3" + b"\x00" * 100  # EBML/webm magic
    with pytest.raises(AudioValidationError) as e:
        validate_audio_bytes(payload[:12], len(payload))
    assert e.value.status_code == 415


def test_ogg_rejected_415():
    payload = b"OggS" + b"\x00" * 100
    with pytest.raises(AudioValidationError) as e:
        validate_audio_bytes(payload[:12], len(payload))
    assert e.value.status_code == 415


def test_oversize_rejected_413(monkeypatch):
    monkeypatch.setenv("MAX_AUDIO_BYTES", "1000")
    payload = wav_bytes()
    with pytest.raises(AudioValidationError) as e:
        validate_audio_bytes(payload[:12], 2000)
    assert e.value.status_code == 413


def test_empty_rejected_415():
    with pytest.raises(AudioValidationError) as e:
        validate_audio_bytes(b"", 0)
    assert e.value.status_code == 415


def test_suffix_from_format():
    assert suffix_for_format("wav") == ".wav"
    assert suffix_for_format("mp3") == ".mp3"


def test_allowed_formats_are_wav_mp3():
    assert ALLOWED_FORMATS == ("wav", "mp3")


# ── Integrasi #4 (D2): konvensi 16 kHz + peringatan oversampling ──

def test_default_target_sample_rate_is_16k(monkeypatch):
    monkeypatch.delenv("TARGET_SAMPLE_RATE", raising=False)
    assert target_sample_rate() == DEFAULT_TARGET_SAMPLE_RATE == 16000


def test_target_sample_rate_env_override(monkeypatch):
    monkeypatch.setenv("TARGET_SAMPLE_RATE", "22050")
    assert target_sample_rate() == 22050


def test_wav_sample_rate_read_from_header():
    payload = wav_bytes(sample_rate=16000)
    assert wav_sample_rate(payload[:28]) == 16000


def test_wav_sample_rate_none_for_mp3():
    assert wav_sample_rate(b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\x00" * 20) is None


def test_warn_if_oversampled_flags_high_rate(monkeypatch):
    monkeypatch.setenv("TARGET_SAMPLE_RATE", "16000")
    payload = wav_bytes(sample_rate=48000)  # 3x target — di bawah ambang 4x
    assert warn_if_oversampled("wav", payload[:28], "x.wav") is None
    payload2 = wav_bytes(sample_rate=96000)  # 6x target → peringatan
    assert warn_if_oversampled("wav", payload2[:28], "x.wav") is not None


def test_warn_if_oversampled_ignores_mp3():
    assert warn_if_oversampled("mp3", b"\x00" * 28, "x.mp3") is None
