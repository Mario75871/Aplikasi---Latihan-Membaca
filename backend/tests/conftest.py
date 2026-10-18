"""Konfigurasi & helper test BacaLaras.

Integrasi #3 (D4): upload audio hanya menerima WAV & MP3 (validasi magic bytes).
Helper `wav_bytes()` menyediakan payload WAV minimal yang valid agar test upload
tidak bergantung pada file audio nyata.

Helper `unlock_level()` menyiapkan prasyarat gerbang naik level (lihat
``services/progression.py``) untuk test yang subjeknya bukan tangga level itu
sendiri. Tangga & gerbangnya diuji tersendiri di ``tests/test_progression.py``.
"""
from __future__ import annotations

import struct


def wav_bytes(n_samples: int = 16, sample_rate: int = 8000) -> bytes:
    """WAV PCM 16-bit mono minimal yang valid (magic bytes RIFF/WAVE).

    Cukup untuk lolos validasi format; tidak harus berisi audio bermakna
    (test mem-mock transcribe).
    """
    data = b"\x00\x00" * n_samples
    byte_rate = sample_rate * 2  # mono, 16-bit
    block_align = 2
    return (
        b"RIFF"
        + struct.pack("<I", 36 + len(data))
        + b"WAVE"
        + b"fmt "
        + struct.pack("<I", 16)
        + struct.pack("<HHIIHH", 1, 1, sample_rate, byte_rate, block_align, 16)
        + b"data"
        + struct.pack("<I", len(data))
        + data
    )


def unlock_level(repo, student_id: str, level: int) -> None:
    """Buka `level` untuk siswa dengan menandai bacaan di bawahnya sudah TUNTAS.

    Gerbang naik level menuntut SELURUH bacaan pada level berjalan tuntas sebelum
    level berikutnya terbuka. Test yang menguji perilaku lain di level 2/3 (mis.
    pipeline audio atau pemahaman) perlu memenuhi prasyarat itu lebih dulu —
    bukan mematikan gerbangnya.

    Asesmen tiruan ini hanya diberi ``session_state="COMPLETED"`` tanpa ``status``,
    sehingga **tidak** terhitung sebagai riwayat oleh Adaptive Engine:
    ``calculate_consecutive_drops`` dan ``previous_status`` menyaring berdasarkan
    ``status``. Tanpa itu, asesmen tiruan akan mengubah keputusan BR-04/BR-07.
    """
    for r in repo.list_readings():
        if (r.get("complexity") or 0) >= level:
            continue
        asmt = repo.create_assessment(student_id, r["id"], r.get("complexity"))
        repo.update_assessment(asmt["id"], {"session_state": "COMPLETED"})
