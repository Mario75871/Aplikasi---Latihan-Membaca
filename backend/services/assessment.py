"""Assessment Engine — WCPM dan Accuracy (Fase 1B).

Menghitung WCPM dan Accuracy dari hasil scoring.py:
- WCPM = Correct Words / durasi_audio × 60
- Accuracy = Correct Words / Total Words Read × 100

Aturan `null` ≠ `0` (JSON_SCHEMA §2): bila nilai TIDAK DAPAT dihitung
(mis. durasi tak tersedia/null, penyebut 0), kembalikan ``None`` — bukan 0.
Nilai 0 hanya untuk nol yang benar (mis. 0 kata benar dengan durasi valid).
"""
from __future__ import annotations

from typing import Optional


def calculate_wcpm(correct_words: int, duration_seconds: Optional[float]) -> Optional[float]:
    """Hitung WCPM (Words Correct Per Minute).

    WCPM = Correct Words / Reading Time × 60

    Args:
        correct_words: jumlah kata yang benar
        duration_seconds: durasi audio aktual (dari framework); None bila tak tersedia

    Returns:
        WCPM (float), atau None bila durasi tidak tersedia/≤ 0 (tidak dapat dihitung).
    """
    if duration_seconds is None or duration_seconds <= 0:
        return None
    return round((correct_words / duration_seconds) * 60, 2)


def calculate_accuracy(correct_words: int, total_words_read: int) -> Optional[float]:
    """Hitung Accuracy (%).

    Accuracy = Correct Words / Total Words Read × 100

    Args:
        correct_words: jumlah kata yang benar
        total_words_read: jumlah kata reference yang dicoba dibaca (D1)

    Returns:
        Accuracy 0..100 (float), atau None bila total 0 (tidak dapat dihitung).
    """
    if total_words_read <= 0:
        return None
    return round((correct_words / total_words_read) * 100, 2)


def classify_accuracy(accuracy: float) -> str:
    """Klasifikasi accuracy (design rule MVP, kriteria Betts).
    
    < 90%: Perlu Intervensi (frustasi)
    90-94%: Berkembang (instruksional)
    >= 95%: Baik (independen)
    """
    if accuracy < 90.0:
        return "Perlu Intervensi"
    elif accuracy < 95.0:
        return "Berkembang"
    else:
        return "Baik"
