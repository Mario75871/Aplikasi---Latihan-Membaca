"""Audio input validation and metadata.

Tanggung jawab:
- memvalidasi keberadaan, ukuran, dan format file audio;
- mengambil durasi/sample rate/kanal/format/ukuran bila tersedia;
- menangani audio kosong/rusak dengan error yang mudah dipahami;
- sanitasi nama file untuk output yang aman.

Tidak pernah menjalankan file audio sebagai perintah. Metadata yang tidak
tersedia dikembalikan sebagai ``None``, bukan angka buatan.
"""

from __future__ import annotations

import re
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

#: Ekstensi yang dianggap audio (validasi dasar; decode sebenarnya oleh ffmpeg/av).
KNOWN_AUDIO_EXTENSIONS: tuple[str, ...] = (
    ".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac", ".wma", ".aiff", ".aif",
)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class AudioValidationError(ValueError):
    """Error yang dapat dipahami pengguna untuk input audio tidak valid."""


@dataclass
class AudioInfo:
    """Metadata audio yang benar-benar tersedia (else ``None``)."""

    path: str
    exists: bool
    size_bytes: int | None = None
    format: str | None = None
    duration_seconds: float | None = None
    sample_rate_hz: int | None = None
    channels: int | None = None
    error: str = ""


def sanitize_filename(name: str, fallback: str = "audio") -> str:
    """Bersihkan nama file dari klien: buang direktori, path traversal, dsb.

    ``../evil.wav`` -> ``evil.wav``; nama kosong -> *fallback*.
    """
    # buang apa pun sebelum nama dasar terakhir (cegah traversal / absolute)
    base = Path(str(name)).name
    base = base.replace("\\", "_")
    base = _SAFE_NAME_RE.sub("_", base).strip("._-")
    if not base:
        base = fallback
    # batasi panjang berlebihan
    return base[:128]


def _wav_metadata(path: Path) -> tuple[float | None, int | None, int | None]:
    try:
        with wave.open(str(path), "rb") as fh:
            frames = fh.getnframes()
            rate = fh.getframerate() or 0
            channels = fh.getnchannels()
            duration = frames / float(rate) if rate else None
            return duration, (rate or None), channels
    except Exception:
        return None, None, None


def _ffprobe_metadata(path: Path) -> tuple[float | None, int | None, int | None]:
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=sample_rate,channels",
             "-of", "default=noprint_wrappers=1",
             str(path)],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return None, None, None
    duration = sample_rate = channels = None
    for line in proc.stdout.splitlines():
        key, _, value = line.partition("=")
        value = value.strip()
        if not value or value.upper() == "N/A":
            continue
        try:
            if key == "duration":
                duration = float(value)
            elif key == "sample_rate":
                sample_rate = int(value)
            elif key == "channels":
                channels = int(value)
        except ValueError:
            continue
    return duration, sample_rate, channels


def probe_audio(path: str | Path, *, min_bytes: int = 1) -> AudioInfo:
    """Kumpulkan metadata audio. Tidak pernah raise; error ada di ``.error``."""
    p = Path(path)
    info = AudioInfo(path=str(p), exists=p.is_file())
    if not p.is_file():
        info.error = f"audio file not found: {p}"
        return info

    try:
        info.size_bytes = p.stat().st_size
    except OSError as exc:
        info.error = f"cannot stat audio file: {exc}"
        return info

    info.format = p.suffix.lower().lstrip(".") or None

    if info.size_bytes is not None and info.size_bytes < min_bytes:
        info.error = f"audio file is empty or too small ({info.size_bytes} bytes)"
        return info

    duration, sample_rate, channels = _wav_metadata(p)
    if duration is None and sample_rate is None:
        duration, sample_rate, channels = _ffprobe_metadata(p)

    info.duration_seconds = duration
    info.sample_rate_hz = sample_rate
    info.channels = channels
    return info


def validate_audio(path: str | Path, *, max_bytes: int | None = None,
                   allowed_extensions: tuple[str, ...] | None = None) -> AudioInfo:
    """Validasi audio; raise ``AudioValidationError`` bila tidak layak diproses.

    Bila ffprobe tidak tersedia, durasi boleh ``None`` — audio tetap dicoba
    ditranskripsi (kegagalan decode akan muncul sebagai error ASR, bukan di sini).
    """
    info = probe_audio(path)
    if not info.exists:
        raise AudioValidationError(info.error or f"audio not found: {path}")
    if info.error:
        raise AudioValidationError(info.error)
    if max_bytes is not None and info.size_bytes is not None and info.size_bytes > max_bytes:
        raise AudioValidationError(
            f"audio too large: {info.size_bytes} bytes > {max_bytes} limit"
        )
    if allowed_extensions is not None:
        ext = Path(path).suffix.lower()
        if ext not in allowed_extensions:
            raise AudioValidationError(
                f"unsupported audio extension {ext!r}; allowed: {list(allowed_extensions)}"
            )
    return info
