"""Adaptive Engine — wrapper (§19, §38.2).

Menggabungkan Fluency (WCPM), Accuracy, Comprehension, Previous Progress,
dan Text Complexity menjadi keputusan. Deterministik & rule-based.

Fase 1C: tambah grade + season untuk batas WCPM dinamis, dan consecutive_drops
dari riwayat.
"""
from __future__ import annotations

from rules.adaptive_rules import (
    AdaptiveDecision,
    AdaptiveInput,
    decide,
)


def make_decision(
    wcpm: float,
    accuracy: float,
    retrieve: float,
    interpret: float,
    reflect: float,
    grade: int,
    season: str,
    previous_status: str | None = None,
    previous_wcpm: float | None = None,
    previous_accuracy: float | None = None,
    current_level: int = 1,
    consecutive_drops: int = 0,
) -> AdaptiveDecision:
    """Wrapper deterministik untuk decide().

    Args:
        grade: 1, 2, atau 3 (kelas siswa)
        season: "fall" | "winter" | "spring" (dari tanggal asesmen)
    """
    return decide(
        AdaptiveInput(
            wcpm=wcpm,
            accuracy=accuracy,
            retrieve=retrieve,
            interpret=interpret,
            reflect=reflect,
            grade=grade,
            season=season,
            previous_status=previous_status,
            previous_wcpm=previous_wcpm,
            previous_accuracy=previous_accuracy,
            current_level=current_level,
            consecutive_drops=consecutive_drops,
        )
    )
