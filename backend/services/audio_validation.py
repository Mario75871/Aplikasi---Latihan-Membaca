"""Validasi upload audio — batas ukuran & format (integrasi #3, Fase C / D4).

Keputusan pengguna (D4): maksimum **10 MB per file**, format **WAV dan MP3 saja**
sampai kebutuhan lain teruji. Validasi memakai **magic bytes**, bukan sekadar nama
file/MIME (yang mudah dipalsukan klien).

Integrasi #4 (D2, aturan #16/#19): konvensi audio = **16 kHz mono** (standar input
ASR). Klien menormalkan rekaman ke format ini (`frontend/lib/audio-wav.ts`). Backend
TIDAK menolak sample rate lain (toleran), tetapi mencatat peringatan bila WAV jauh
di atas target — agar boros bandwidth terdeteksi, bukan untuk memblokir.
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from typing import Optional

#: Ukuran maksimum default (byte). Dapat ditimpa env MAX_AUDIO_BYTES.
DEFAULT_MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB

#: Format yang diizinkan (D4).
ALLOWED_FORMATS = ("wav", "mp3")

#: Sample rate standar input ASR (integrasi #4, D2). Satu sumber untuk backend.
DEFAULT_TARGET_SAMPLE_RATE = 16000

#: Durasi maksimum default (detik) — integrasi #5, D4. 5 menit.
DEFAULT_MAX_AUDIO_DURATION_SEC = 300


def target_sample_rate() -> int:
    """Target sample rate dari env TARGET_SAMPLE_RATE (fallback 16000)."""
    raw = os.getenv("TARGET_SAMPLE_RATE")
    if not raw:
        return DEFAULT_TARGET_SAMPLE_RATE
    try:
        val = int(raw)
        return val if val > 0 else DEFAULT_TARGET_SAMPLE_RATE
    except ValueError:
        return DEFAULT_TARGET_SAMPLE_RATE


def max_audio_duration_sec() -> int:
    """Durasi maksimum dari env MAX_AUDIO_DURATION_SEC (fallback 300 = 5 menit).

    Integrasi #5 (D4): batas durasi melengkapi batas ukuran (10 MB). Bila durasi
    tak tersedia (None), JANGAN tolak — konsisten `null` != 0.
    """
    raw = os.getenv("MAX_AUDIO_DURATION_SEC")
    if not raw:
        return DEFAULT_MAX_AUDIO_DURATION_SEC
    try:
        val = int(float(raw))
        return val if val > 0 else DEFAULT_MAX_AUDIO_DURATION_SEC
    except ValueError:
        return DEFAULT_MAX_AUDIO_DURATION_SEC


def validate_audio_duration(duration_sec: Optional[float]) -> None:
    """Tolak audio yang durasinya melebihi batas (integrasi #5, D4).

    Args:
        duration_sec: durasi aktual (dari probe/framework). ``None`` = tak tersedia →
            TIDAK ditolak (``null`` != 0).

    Raises:
        AudioValidationError: 422 bila durasi > batas.
    """
    if duration_sec is None:
        return
    limit = max_audio_duration_sec()
    if duration_sec > limit:
        raise AudioValidationError(
            detail=(
                f"Durasi audio melebihi batas ({duration_sec:.0f} detik > {limit} detik). "
                "Silakan unggah rekaman yang lebih pendek."
            ),
            status_code=422,
        )


def max_audio_bytes() -> int:
    """Batas ukuran dari env MAX_AUDIO_BYTES (fallback 10 MB)."""
    raw = os.getenv("MAX_AUDIO_BYTES")
    if not raw:
        return DEFAULT_MAX_AUDIO_BYTES
    try:
        val = int(raw)
        return val if val > 0 else DEFAULT_MAX_AUDIO_BYTES
    except ValueError:
        return DEFAULT_MAX_AUDIO_BYTES


@dataclass
class AudioValidationError(Exception):
    """Kesalahan validasi audio (pesan ramah + kode status HTTP)."""
    detail: str
    status_code: int

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.detail


def _sniff_format(head: bytes) -> Optional[str]:
    """Deteksi format dari magic bytes. Kembalikan 'wav'/'mp3'/None.

    - WAV: byte 0-3 = 'RIFF', byte 8-11 = 'WAVE'.
    - MP3: diawali 'ID3', ATAU frame sync 0xFF + (bit tinggi 0xE0) pada byte 1.
    """
    if len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if len(head) >= 3 and head[0:3] == b"ID3":
        return "mp3"
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return "mp3"
    return None


def validate_audio_bytes(head: bytes, size: int) -> str:
    """Validasi ukuran + magic bytes. Kembalikan format terdeteksi ('wav'/'mp3').

    Raises:
        AudioValidationError: 413 bila melebihi batas; 415 bila format tidak didukung.
    """
    limit = max_audio_bytes()
    if size > limit:
        raise AudioValidationError(
            detail=(
                f"Ukuran audio melebihi batas ({size} byte > {limit} byte). "
                "Silakan unggah file yang lebih kecil."
            ),
            status_code=413,
        )
    if size == 0:
        raise AudioValidationError(
            detail="File audio kosong.", status_code=415
        )
    fmt = _sniff_format(head)
    if fmt not in ALLOWED_FORMATS:
        raise AudioValidationError(
            detail=(
                "Format audio tidak didukung. Hanya WAV dan MP3 yang diterima. "
                "(Tips: MediaRecorder browser menghasilkan webm — konversi ke WAV/MP3 "
                "terlebih dahulu.)"
            ),
            status_code=415,
        )
    return fmt


def suffix_for_format(fmt: str) -> str:
    """Suffix aman untuk file temp (dari whitelist, bukan input klien)."""
    return ".wav" if fmt == "wav" else ".mp3"


def wav_sample_rate(head: bytes) -> Optional[int]:
    """Baca sample rate dari header WAV (byte 24-27, LE). None bila bukan WAV.

    Berguna untuk deteksi boros (mis. klien nakal mengirim 48 kHz) tanpa menolak.
    """
    if len(head) < 28 or head[0:4] != b"RIFF" or head[8:12] != b"WAVE":
        return None
    try:
        return struct.unpack_from("<I", head, 24)[0]
    except struct.error:
        return None


def warn_if_oversampled(fmt: str, head: bytes, path: str) -> Optional[str]:
    """Kembalikan pesan peringatan bila WAV jauh di atas target (bukan error).

    Integrasi #4 (D2): konvensi 16 kHz. Sample rate > 4x target dicatat agar boros
    terdeteksi. Tidak mengubah hasil penilaian.
    """
    if fmt != "wav":
        return None
    rate = wav_sample_rate(head)
    target = target_sample_rate()
    if rate and rate > target * 4:
        return (
            f"[audio] peringatan: {path} sample rate {rate} Hz jauh di atas target "
            f"{target} Hz (klien sebaiknya menormalkan ke {target} Hz mono)."
        )
    return None
