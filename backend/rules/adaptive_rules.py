"""Adaptive Rules — BR-01 s/d BR-05, BR-07, BR-08 (Fase 1C).

Catatan v2.5:
  - BR-06 (Dominant Error Pattern) PENSIUN — nomor tidak dipakai ulang.
  - BR-10 (Self-Correction) PENSIUN — nomor tidak dipakai ulang.
  - BR-03, BR-04, BR-05 sekarang memakai wcpm_floor(grade, season) dinamis (D2)
  - BR-07 dihitung dari riwayat asesmen COMPLETED (D3)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Design thresholds MVP (§15, §20)
ACCURACY_LOW = 90.0        # < 90 → INTERVENE
ACCURACY_HIGH = 95.0       # >= 95 → kandidat promosi
COMPREHENSION_MIN = 80.0   # < 80 → INTERVENE kompetensi


def wcpm_floor(grade: int, season: str) -> Optional[float]:
    """Batas WCPM berdasarkan kelas dan musim (D2, F-08).

    Batas = P50 Hasbrouck–Tindal 2017 dikurangi 10 WCPM.

    Integrasi #2, Fase C.4: nilai diturunkan dari **satu sumber** tabel norms di
    ``services/hasbrouck.py`` (bukan literal terpisah), agar tidak lepas sinkron.

    Args:
        grade: 1, 2, atau 3
        season: "fall" (Juli-Okt), "winter" (Nov-Feb), "spring" (Mar-Jun)

    Returns:
        Batas WCPM (float), atau None bila tidak tersedia (mis. kelas 1 awal tahun).
    """
    from services.hasbrouck import _HASBROUCK_TINDAL

    row = _HASBROUCK_TINDAL.get(grade)
    if row is None:
        return None
    norms = row.get(season)
    if norms is None:
        return None
    # P50 − 10 (D2)
    return float(norms["p50"] - 10)


def determine_season(assessment_date: datetime) -> str:
    """Tentukan musim dari tanggal asesmen (D2, Q14).
    
    Awal (fall): Juli-Oktober (7-10)
    Tengah (winter): November-Februari (11-2)
    Akhir (spring): Maret-Juni (3-6)
    """
    month = assessment_date.month
    if 7 <= month <= 10:
        return "fall"
    elif 11 <= month or month <= 2:
        return "winter"
    else:  # 3 <= month <= 6
        return "spring"


@dataclass
class AdaptiveInput:
    wcpm: float
    accuracy: float
    retrieve: float
    interpret: float
    reflect: float
    grade: int  # 1, 2, atau 3
    season: str  # "fall", "winter", "spring"
    previous_status: str | None = None   # status asesmen sebelumnya
    previous_wcpm: float | None = None
    previous_accuracy: float | None = None
    consecutive_drops: int = 0  # D3: dihitung dari riwayat
    current_level: int = 1


@dataclass
class AdaptiveDecision:
    status: str                 # INTERVENE | STAY | PROMOTION_CANDIDATE | PROMOTE
    focus: str | None           # Fluency/Accuracy | Retrieve | Interpret | Reflect
    recommendation: str
    next_reading_level: int
    rules_fired: list[dict]


def _rule(rule_id: str, text: str, fired: bool) -> dict:
    return {"rule": rule_id, "text": text, "fired": fired}


def decide(inp: AdaptiveInput) -> AdaptiveDecision:
    """Menjalankan business rules secara deterministik (§38.2).
    
    Urutan prioritas (D4):
    BR-01 → BR-02 → BR-03/BR-04 → BR-05 → BR-07 → default STAY
    """
    rules: list[dict] = []

    # BR-01 — Accuracy < 90% → INTERVENE Fluency/Accuracy (§20)
    if inp.accuracy < ACCURACY_LOW:
        rules.append(_rule("BR-01", f"Akurasi {inp.accuracy}% < {ACCURACY_LOW}%", True))
        return AdaptiveDecision(
            status="INTERVENE", focus="Fluency/Accuracy",
            recommendation="Latihan kelancaran & akurasi membaca.",
            next_reading_level=inp.current_level,
            rules_fired=rules,
        )
    rules.append(_rule("BR-01", f"Akurasi {inp.accuracy}% ≥ {ACCURACY_LOW}%", False))

    # BR-02 — Comprehension < 80% → INTERVENE kompetensi (§20)
    for comp_name, val in (("Retrieve", inp.retrieve),
                           ("Interpret", inp.interpret),
                           ("Reflect", inp.reflect)):
        if val < COMPREHENSION_MIN:
            rules.append(_rule("BR-02", f"{comp_name} {val}% < {COMPREHENSION_MIN}%", True))
            return AdaptiveDecision(
                status="INTERVENE", focus=comp_name,
                recommendation=f"Latihan pemahaman {comp_name.lower()}.",
                next_reading_level=inp.current_level,
                rules_fired=rules,
            )
    rules.append(_rule("BR-02", "Semua kompetensi ≥ 80%", False))

    # BR-03 — Promotion Candidate (§21, v2.5: + syarat WCPM)
    floor = wcpm_floor(inp.grade, inp.season)
    wcpm_ok = True
    if floor is not None:
        wcpm_ok = inp.wcpm >= floor
        wcpm_msg = f"WCPM {inp.wcpm} {'≥' if wcpm_ok else '<'} batas {floor}"
    else:
        wcpm_msg = f"WCPM {inp.wcpm} (batas tidak tersedia, diabaikan)"
    
    is_candidate = (
        inp.accuracy >= ACCURACY_HIGH
        and inp.retrieve >= COMPREHENSION_MIN
        and inp.interpret >= COMPREHENSION_MIN
        and inp.reflect >= COMPREHENSION_MIN
        and wcpm_ok
    )
    
    if is_candidate:
        rules.append(_rule("BR-03", f"Kriteria kandidat promosi terpenuhi: {wcpm_msg}", True))

        # BR-04 — Promotion Confirmation (§22, v2.5: teks berbeda + naik satu level)
        if inp.previous_status == "PROMOTION_CANDIDATE":
            rules.append(_rule("BR-04", "Asesmen sebelumnya juga kandidat → PROMOTE", True))
            return AdaptiveDecision(
                status="PROMOTE", focus=None,
                recommendation="Gunakan bacaan complexity level berikutnya.",
                next_reading_level=min(3, inp.current_level + 1),
                rules_fired=rules,
            )
        rules.append(_rule("BR-04", "Asesmen sebelumnya belum kandidat → minta reassess", False))
        return AdaptiveDecision(
            status="PROMOTION_CANDIDATE", focus=None,
            recommendation="Lakukan reassessment pada teks berbeda di level yang sama untuk konfirmasi promosi.",
            next_reading_level=inp.current_level,
            rules_fired=rules,
        )
    rules.append(_rule("BR-03", f"Kriteria kandidat promosi belum terpenuhi: {wcpm_msg}", False))

    # BR-05 — Low WCPM + Accuracy tinggi + Comprehension tinggi (§23, v2.5: batas dinamis)
    if floor is not None and inp.wcpm < floor \
            and inp.accuracy >= ACCURACY_LOW \
            and inp.retrieve >= COMPREHENSION_MIN \
            and inp.interpret >= COMPREHENSION_MIN \
            and inp.reflect >= COMPREHENSION_MIN:
        rules.append(_rule("BR-05", f"WCPM {inp.wcpm} < {floor} + Akurasi & Pemahaman tinggi → Fluency Practice", True))
        return AdaptiveDecision(
            status="STAY", focus="Fluency",
            recommendation="STAY + latihan kelancaran (fluency practice).",
            next_reading_level=inp.current_level,
            rules_fired=rules,
        )
    rules.append(_rule("BR-05", "Bukan kondisi low-WCPM", False))

    # BR-07 — Performance Drop (§25, D3: dari riwayat)
    if inp.consecutive_drops >= 2:
        rules.append(_rule("BR-07", "Penurunan konsisten pada beberapa asesmen → REVIEW/REMEDIAL", True))
        return AdaptiveDecision(
            status="STAY", focus="Monitor",
            recommendation="REVIEW / REMEDIAL. Pantau perkembangan.",
            next_reading_level=inp.current_level,
            rules_fired=rules,
        )
    if inp.consecutive_drops == 1:
        rules.append(_rule("BR-07", "Penurunan sekali → STAY + MONITOR", True))
        return AdaptiveDecision(
            status="STAY", focus="Monitor",
            recommendation="STAY + MONITOR.",
            next_reading_level=inp.current_level,
            rules_fired=rules,
        )
    rules.append(_rule("BR-07", "Tidak ada penurunan", False))

    # Default — STAY
    return AdaptiveDecision(
        status="STAY", focus=None,
        recommendation="Lanjutkan pada level yang sama.",
        next_reading_level=inp.current_level,
        rules_fired=rules,
    )


def calculate_consecutive_drops(
    current_wcpm: float,
    current_accuracy: float,
    assessment_history: list[dict],
) -> tuple[int, Optional[float], Optional[float]]:
    """Hitung consecutive drops dari riwayat (D3).
    
    Penurunan = WCPM atau Accuracy lebih rendah dari asesmen COMPLETED sebelumnya.
    
    Args:
        current_wcpm: WCPM asesmen saat ini
        current_accuracy: Accuracy asesmen saat ini
        assessment_history: list asesmen COMPLETED siswa yang sama, urut waktu (lama→baru)
    
    Returns:
        (consecutive_drops, previous_wcpm, previous_accuracy)
        consecutive_drops = 0 bila tidak ada penurunan atau ini asesmen pertama
    """
    if not assessment_history:
        return 0, None, None
    
    # Ambil asesmen terakhir yang COMPLETED
    prev = None
    for a in reversed(assessment_history):
        if a.get("status") in ["COMPLETED", "INTERVENE", "STAY", "PROMOTION_CANDIDATE", "PROMOTE"]:
            prev = a
            break
    
    if not prev:
        return 0, None, None
    
    prev_wcpm = prev.get("wcpm") or 0
    prev_accuracy = prev.get("accuracy") or 0
    
    # Cek apakah asesmen saat ini turun
    current_drop = (current_wcpm < prev_wcpm) or (current_accuracy < prev_accuracy)
    
    if not current_drop:
        return 0, prev_wcpm, prev_accuracy
    
    # Hitung berapa kali berturut-turut turun
    consecutive = 1  # asesmen saat ini sudah turun
    
    # Telusuri mundur dari prev
    for i in range(len(assessment_history) - 2, -1, -1):
        curr_hist = assessment_history[i + 1]
        prev_hist = assessment_history[i]
        
        if curr_hist.get("status") not in ["COMPLETED", "INTERVENE", "STAY", "PROMOTION_CANDIDATE", "PROMOTE"]:
            continue
        if prev_hist.get("status") not in ["COMPLETED", "INTERVENE", "STAY", "PROMOTION_CANDIDATE", "PROMOTE"]:
            continue
        
        curr_w = curr_hist.get("wcpm") or 0
        curr_a = curr_hist.get("accuracy") or 0
        prev_w = prev_hist.get("wcpm") or 0
        prev_a = prev_hist.get("accuracy") or 0
        
        if (curr_w < prev_w) or (curr_a < prev_a):
            consecutive += 1
        else:
            break
    
    return consecutive, prev_wcpm, prev_accuracy
