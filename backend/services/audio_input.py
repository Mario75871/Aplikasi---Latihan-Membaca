"""Audio input helper — Fase 3.3 (.webm + durasi).

Frontend merekam ``audio/webm`` via MediaRecorder. Framework ``probe_audio``
hanya mengenali WAV lewat modul ``wave``; untuk format lain (termasuk webm)
durasi bergantung pada ``ffprobe`` yang mungkin tidak ada di server.

Modul ini menyediakan durasi audio **tanpa bergantung ffprobe** memakai PyAV
(sudah menjadi dependensi faster-whisper). Hasilnya dipakai untuk melengkapi
``duration_seconds`` framework bila framework mengembalikan ``None`` — sehingga
WCPM tidak jatuh ke ``None`` hanya karena ffprobe tidak tersedia.

Tidak mengubah framework: hanya menyediakan nilai pelengkap di lapisan backend.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def probe_duration_seconds(path: str | Path) -> Optional[float]:
    """Durasi audio (detik) via PyAV. Mengembalikan None bila tidak terbaca.

    Tidak melempar exception — kegagalan decode dilaporkan sebagai None agar
    pemanggil dapat memutuskan (null ≠ 0).
    """
    try:
        import av

        with av.open(str(path)) as container:
            if container.duration is not None:
                # container.duration dalam mikrodetik (AV_TIME_BASE = 1_000_000)
                return float(container.duration) / 1_000_000.0
            # Fallback: ambil dari stream audio terpanjang.
            best = None
            for stream in container.streams:
                if stream.type != "audio":
                    continue
                if stream.duration is not None and stream.time_base is not None:
                    secs = float(stream.duration * stream.time_base)
                    if best is None or secs > best:
                        best = secs
            return best
    except Exception:
        return None


def resolve_duration_seconds(
    audio_path: str | Path,
    framework_duration: Optional[float],
) -> Optional[float]:
    """Gabungkan durasi framework dengan fallback PyAV.

    Urutan: pakai durasi framework bila ada & > 0; jika tidak, coba PyAV.
    Mengembalikan None bila keduanya tidak tersedia (bukan 0).
    """
    if framework_duration is not None and framework_duration > 0:
        return framework_duration
    return probe_duration_seconds(audio_path)
