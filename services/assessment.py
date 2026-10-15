"""Assessment Engine — WCPM dan Accuracy (Fase 1B).

Menghitung WCPM dan Accuracy dari hasil scoring.py:
- WCPM = Correct Words / durasi_audio × 60
- Accuracy = Correct Words / Total Words Read × 100

Tangani edge case: durasi 0, total 0.
"""
from __future__ import annotations


def calculate_wcpm(correct_words: int, duration_seconds: float) -> float:
    """Hitung WCPM (Words Correct Per Minute).
    
    WCPM = Correct Words / Reading Time × 60
    
    Args:
        correct_words: jumlah kata yang benar
        duration_seconds: durasi audio aktual (dari framework)
    
    Returns:
        WCPM (0 bila durasi ≤ 0)
    """
    if duration_seconds <= 0:
        return 0.0
    return round((correct_words / duration_seconds) * 60, 2)


def calculate_accuracy(correct_words: int, total_words_read: int) -> float:
    """Hitung Accuracy (%).
    
    Accuracy = Correct Words / Total Words Read × 100
    
    Args:
        correct_words: jumlah kata yang benar
        total_words_read: jumlah kata reference yang dicoba dibaca (D1)
    
    Returns:
        Accuracy 0..100 (0 bila total 0)
    """
    if total_words_read <= 0:
        return 0.0
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
