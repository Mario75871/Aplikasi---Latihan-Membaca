"""Test audio input helper — Fase 3.3 (.webm + durasi).

Memverifikasi bahwa durasi audio dapat dilengkapi lewat PyAV bila framework
mengembalikan None (mis. webm tanpa ffprobe), dan bahwa kegagalan tidak
mengarang angka (null ≠ 0).
"""
import wave

from services.audio_input import probe_duration_seconds, resolve_duration_seconds


def _write_wav(path, seconds: float, rate: int = 8000) -> None:
    """Tulis WAV senyap berdurasi tertentu (untuk test durasi)."""
    n_frames = int(rate * seconds)
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(b"\x00\x00" * n_frames)


def test_framework_duration_preferred(tmp_path):
    """Bila durasi framework ada & > 0, dipakai apa adanya."""
    wav = tmp_path / "a.wav"
    _write_wav(wav, 2.0)
    assert resolve_duration_seconds(wav, 2.5) == 2.5


def test_fallback_to_pyav_when_framework_none(tmp_path):
    """Framework None → fallback PyAV membaca durasi WAV nyata."""
    wav = tmp_path / "a.wav"
    _write_wav(wav, 1.5)
    dur = resolve_duration_seconds(wav, None)
    assert dur is not None
    assert abs(dur - 1.5) < 0.1  # toleransi codec/header


def test_fallback_when_framework_zero(tmp_path):
    """Framework 0 dianggap tidak tersedia → fallback PyAV."""
    wav = tmp_path / "a.wav"
    _write_wav(wav, 1.0)
    dur = resolve_duration_seconds(wav, 0.0)
    assert dur is not None and dur > 0


def test_missing_file_returns_none(tmp_path):
    """File tidak ada → None (bukan 0)."""
    assert resolve_duration_seconds(tmp_path / "nope.webm", None) is None


def test_probe_unreadable_returns_none(tmp_path):
    """File bukan audio valid → None, tidak melempar."""
    bad = tmp_path / "bad.webm"
    bad.write_bytes(b"not-a-real-audio-file")
    assert probe_duration_seconds(bad) is None
