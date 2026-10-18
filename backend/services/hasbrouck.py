"""Hasbrouck–Tindal Reference (F-11, D9).

Posisi WCPM terhadap persentil sesuai kelas dan musim siswa.

TODO: verifikasi ke laporan asli Hasbrouck & Tindal (2017).
Tabel berasal dari salinan sekunder (PRD v2.5, F-11).
Jangan menambah angka persentil lain (P10/P75/P90) tanpa sumber.
"""
from __future__ import annotations

from typing import Optional

# Tabel P25/P50 Hasbrouck–Tindal 2017 (D9)
# TODO: verifikasi ke laporan asli H&T 2017 sebelum rilis
_HASBROUCK_TINDAL = {
    1: {
        "fall": None,  # tidak ada norma kelas 1 awal tahun
        "winter": {"p25": 16, "p50": 29},
        "spring": {"p25": 34, "p50": 60},
    },
    2: {
        "fall": {"p25": 36, "p50": 50},
        "winter": {"p25": 59, "p50": 84},
        "spring": {"p25": 72, "p50": 100},
    },
    3: {
        "fall": {"p25": 59, "p50": 83},
        "winter": {"p25": 79, "p50": 97},
        "spring": {"p25": 91, "p50": 112},
    },
}

DISCLAIMER = (
    "Reference based on Hasbrouck & Tindal ORF norms. "
    "This is not an Indonesian national normative benchmark."
)


def get_percentile_position(grade: int, season: str, wcpm: float) -> dict:
    """Tentukan posisi WCPM terhadap persentil P25/P50 (F-11).

    Args:
        grade: 1, 2, atau 3
        season: "fall" | "winter" | "spring"
        wcpm: nilai WCPM siswa

    Returns:
        dict dengan posisi, persentil, dan disclaimer
    """
    row = _HASBROUCK_TINDAL.get(grade)
    if row is None:
        return {
            "available": False,
            "reason": f"Tidak ada data referensi untuk kelas {grade}",
            "wcpm": wcpm,
            "grade": grade,
            "season": season,
            "disclaimer": DISCLAIMER,
            "todo_verify": True,
        }
    
    norms = row.get(season)
    if norms is None:
        return {
            "available": False,
            "reason": f"Tidak ada norma untuk kelas {grade} musim {season}",
            "wcpm": wcpm,
            "grade": grade,
            "season": season,
            "disclaimer": DISCLAIMER,
            "todo_verify": True,
        }
    
    p25 = norms["p25"]
    p50 = norms["p50"]
    
    if wcpm < p25:
        position = "Di bawah P25"
        label = f"< P25 ({p25})"
    elif wcpm < p50:
        position = "Antara P25 dan P50"
        label = f"P25–P50 ({p25}–{p50})"
    else:
        position = "Di atas P50"
        label = f"≥ P50 ({p50})"
    
    return {
        "available": True,
        "position": position,
        "label": label,
        "wcpm": wcpm,
        "grade": grade,
        "season": season,
        "p25": p25,
        "p50": p50,
        "disclaimer": DISCLAIMER,
        "todo_verify": True,
    }
