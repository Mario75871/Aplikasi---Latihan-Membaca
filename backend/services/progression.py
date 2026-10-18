"""Progresi bacaan per siswa — gerbang naik level.

Aturan (keputusan produk, bukan ketentuan pedoman B1-B3):
    Tangga mulai Level 1 untuk SEMUA siswa, tanpa melihat tingkat kelasnya.
    Seorang siswa hanya boleh mengases bacaan pada level <= level terbukanya.
    Level terbuka naik satu tingkat setelah **seluruh** bacaan pada level
    berjalan tuntas.

"Tuntas" berarti ``session_state == "COMPLETED"`` pada asesmen siswa untuk bacaan
itu. Status tersebut baru diisi di akhir pipeline (``api/assessments.py``:
submit pemahaman), yaitu setelah audio diproses DAN jawaban pemahaman dikirim,
jadi memang berarti selesai — bukan sekadar sesi dibuka.

Modul ini adalah **satu-satunya penegak aturan**; frontend hanya mencerminkannya
untuk keperluan tampilan (``frontend/lib/progression.ts``). Bila aturan berubah,
ubah di sini lebih dulu, lalu cerminnya.
"""
from __future__ import annotations

from typing import Iterable, Optional

#: Tangga level yang dikenal (selaras dengan seed/validator.py LEVEL_LIMITS).
LEVELS = (1, 2, 3)

#: Nilai session_state yang berarti asesmen sudah tuntas.
COMPLETED_STATE = "COMPLETED"


def completed_reading_ids(repo, student_id: str) -> set[str]:
    """Kumpulan ``reading_id`` yang sudah TUNTAS untuk siswa ini."""
    return {
        a["reading_id"]
        for a in repo.list_student_assessments(student_id)
        if a.get("session_state") == COMPLETED_STATE and a.get("reading_id")
    }


def readings_at_level(readings: Iterable[dict], level: int) -> list[dict]:
    """Bacaan pada satu level (``complexity``)."""
    return [r for r in readings if r.get("complexity") == level]


def unlocked_level(readings: Iterable[dict], completed_ids: set[str]) -> int:
    """Level tertinggi yang boleh diakses, mengikuti tangga dari Level 1.

    Naik satu tingkat selama seluruh bacaan pada level berjalan sudah tuntas.
    Level tanpa bacaan dianggap tuntas (tidak ada yang perlu diselesaikan),
    sehingga katalog yang tidak lengkap tidak mengunci tangga selamanya.
    """
    readings = list(readings)
    level = LEVELS[0]
    for lvl in LEVELS[:-1]:
        at_level = readings_at_level(readings, lvl)
        if at_level and not all(r["id"] in completed_ids for r in at_level):
            break
        level = lvl + 1
    return level


def locked_reason(
    readings: Iterable[dict],
    completed_ids: set[str],
    reading: dict,
    student_name: Optional[str] = None,
) -> Optional[str]:
    """Alasan bacaan ini terkunci, atau ``None`` bila boleh diases.

    Pesannya menyebut hal yang bisa ditindaklanjuti: sisa bacaan pada level
    berjalan yang belum tuntas. Pesan inilah yang tampil di UI (``409`` dari
    backend maupun cermin frontend), jadi kalimatnya harus enak dibaca guru.
    """
    readings = list(readings)
    level = reading.get("complexity")
    unlocked = unlocked_level(readings, completed_ids)
    if level is None or level <= unlocked:
        return None

    who = f"{student_name} " if student_name else ""
    pending = [
        r for r in readings_at_level(readings, unlocked)
        if r["id"] not in completed_ids
    ]
    if pending:
        judul = ", ".join(f"«{r.get('title') or r['id']}»" for r in pending)
        return (
            f"{who}masih di Level {unlocked}. Selesaikan dulu {len(pending)} bacaan "
            f"Level {unlocked} yang belum tuntas: {judul}. "
            f"Level {level} terbuka setelah semuanya tuntas."
        )
    return (
        f"{who}masih di Level {unlocked}. Level {level} terbuka setelah seluruh "
        f"bacaan Level {unlocked} tuntas."
    )
