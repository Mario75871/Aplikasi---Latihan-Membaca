"""Test Adaptive Rules v2.5 — wcpm_floor dan BR-07 dari riwayat (Fase 1C)."""
import pytest
from datetime import datetime

from rules.adaptive_rules import (
    ACCURACY_HIGH,
    ACCURACY_LOW,
    COMPREHENSION_MIN,
    AdaptiveInput,
    calculate_consecutive_drops,
    decide,
    determine_season,
    wcpm_floor,
)


# ========== Test wcpm_floor (D2) ==========

def test_wcpm_floor_grade1_fall_is_none():
    """Kelas 1 awal tahun tidak punya batas WCPM."""
    assert wcpm_floor(1, "fall") is None


def test_wcpm_floor_grade1_winter():
    assert wcpm_floor(1, "winter") == 19


def test_wcpm_floor_grade1_spring():
    assert wcpm_floor(1, "spring") == 50


def test_wcpm_floor_grade2_fall():
    assert wcpm_floor(2, "fall") == 40


def test_wcpm_floor_grade2_winter():
    assert wcpm_floor(2, "winter") == 74


def test_wcpm_floor_grade2_spring():
    assert wcpm_floor(2, "spring") == 90


def test_wcpm_floor_grade3_fall():
    assert wcpm_floor(3, "fall") == 73


def test_wcpm_floor_grade3_winter():
    assert wcpm_floor(3, "winter") == 87


def test_wcpm_floor_grade3_spring():
    assert wcpm_floor(3, "spring") == 102


def test_wcpm_floor_invalid_grade():
    """Grade di luar 1-3 return None."""
    assert wcpm_floor(4, "fall") is None
    assert wcpm_floor(0, "spring") is None


# ========== Test determine_season (D2, Q14) ==========

def test_season_fall():
    """Juli-Oktober = fall."""
    assert determine_season(datetime(2026, 7, 15)) == "fall"
    assert determine_season(datetime(2026, 10, 31)) == "fall"


def test_season_winter():
    """November-Februari = winter."""
    assert determine_season(datetime(2026, 11, 1)) == "winter"
    assert determine_season(datetime(2026, 12, 25)) == "winter"
    assert determine_season(datetime(2027, 1, 15)) == "winter"
    assert determine_season(datetime(2027, 2, 28)) == "winter"


def test_season_spring():
    """Maret-Juni = spring."""
    assert determine_season(datetime(2026, 3, 1)) == "spring"
    assert determine_season(datetime(2026, 6, 30)) == "spring"


# ========== Test BR-01 ==========

def test_br01_low_accuracy_intervene():
    """BR-01: Accuracy < 90% → INTERVENE."""
    inp = AdaptiveInput(
        wcpm=60, accuracy=85.0,
        retrieve=90, interpret=90, reflect=90,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "INTERVENE"
    assert decision.focus == "Fluency/Accuracy"
    assert any(r["rule"] == "BR-01" and r["fired"] for r in decision.rules_fired)


# ========== Test BR-02 ==========

def test_br02_low_retrieve_intervene():
    """BR-02: Retrieve < 80% → INTERVENE."""
    inp = AdaptiveInput(
        wcpm=70, accuracy=95.0,
        retrieve=70, interpret=85, reflect=85,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "INTERVENE"
    assert decision.focus == "Retrieve"
    assert any(r["rule"] == "BR-02" and r["fired"] for r in decision.rules_fired)


def test_br02_low_interpret_intervene():
    """BR-02: Interpret < 80% → INTERVENE."""
    inp = AdaptiveInput(
        wcpm=70, accuracy=95.0,
        retrieve=85, interpret=75, reflect=85,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "INTERVENE"
    assert decision.focus == "Interpret"


def test_br02_low_reflect_intervene():
    """BR-02: Reflect < 80% → INTERVENE."""
    inp = AdaptiveInput(
        wcpm=70, accuracy=95.0,
        retrieve=85, interpret=85, reflect=70,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "INTERVENE"
    assert decision.focus == "Reflect"


# ========== Test BR-03 dengan batas WCPM dinamis (v2.5) ==========

def test_br03_promotion_candidate_with_wcpm_floor():
    """BR-03 v2.5: Accuracy ≥95%, Comprehension ≥80%, WCPM ≥ batas → CANDIDATE."""
    inp = AdaptiveInput(
        wcpm=68,  # >= 40 (kelas 2 fall)
        accuracy=95.0,
        retrieve=90, interpret=86, reflect=82,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "PROMOTION_CANDIDATE"
    assert any(r["rule"] == "BR-03" and r["fired"] for r in decision.rules_fired)


def test_br03_fails_if_wcpm_below_floor():
    """BR-03: WCPM < batas → tidak kandidat."""
    inp = AdaptiveInput(
        wcpm=35,  # < 40 (kelas 2 fall)
        accuracy=96.0,
        retrieve=90, interpret=90, reflect=90,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status != "PROMOTION_CANDIDATE"


def test_br03_grade1_fall_no_wcpm_requirement():
    """BR-03: Kelas 1 awal tahun tidak punya syarat WCPM."""
    inp = AdaptiveInput(
        wcpm=10,  # rendah, tapi batas None
        accuracy=96.0,
        retrieve=85, interpret=85, reflect=85,
        grade=1, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    # Harus kandidat karena batas WCPM diabaikan
    assert decision.status == "PROMOTION_CANDIDATE"


# ========== Test BR-04 (v2.5: teks berbeda + naik satu level) ==========

def test_br04_promote_when_previous_candidate():
    """BR-04: Asesmen sebelumnya kandidat → PROMOTE."""
    inp = AdaptiveInput(
        wcpm=75, accuracy=96.0,
        retrieve=92, interpret=88, reflect=84,
        grade=2, season="fall",
        previous_status="PROMOTION_CANDIDATE",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "PROMOTE"
    assert decision.next_reading_level == 2  # naik satu level
    assert any(r["rule"] == "BR-04" and r["fired"] for r in decision.rules_fired)


def test_br04_max_level_3():
    """BR-04: Maksimum Level 3."""
    inp = AdaptiveInput(
        wcpm=110,  # >= 102 (kelas 3 spring)
        accuracy=96.0,
        retrieve=92, interpret=88, reflect=84,
        grade=3, season="spring",
        previous_status="PROMOTION_CANDIDATE",
        current_level=3,
    )
    decision = decide(inp)
    assert decision.status == "PROMOTE"
    assert decision.next_reading_level == 3  # tidak naik lagi


def test_br04_stay_when_criteria_not_met_next():
    """BR-04: Kriteria terpenuhi tapi prev bukan kandidat → CANDIDATE (bukan STAY)."""
    inp = AdaptiveInput(
        wcpm=68, accuracy=95.0,
        retrieve=90, interpret=86, reflect=82,
        grade=2, season="fall",
        previous_status="STAY",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "PROMOTION_CANDIDATE"


# ========== Test BR-05 dengan batas WCPM dinamis (v2.5) ==========

def test_br05_low_wcpm_stay_fluency():
    """BR-05 v2.5: WCPM < batas + Akurasi & Pemahaman tinggi → STAY Fluency."""
    inp = AdaptiveInput(
        wcpm=35,  # < 40 (kelas 2 fall)
        accuracy=94.0,  # >= 90
        retrieve=85, interpret=85, reflect=85,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "STAY"
    assert decision.focus == "Fluency"
    assert any(r["rule"] == "BR-05" and r["fired"] for r in decision.rules_fired)


def test_br05_does_not_downgrade_level():
    """BR-05: Tidak menurunkan level otomatis."""
    inp = AdaptiveInput(
        wcpm=30, accuracy=92.0,
        retrieve=85, interpret=85, reflect=85,
        grade=2, season="fall",
        current_level=2,
    )
    decision = decide(inp)
    assert decision.next_reading_level == 2  # tetap level 2


def test_br05_not_triggered_if_no_floor():
    """BR-05: Tidak terpicu bila batas WCPM tidak tersedia."""
    inp = AdaptiveInput(
        wcpm=10,  # rendah tapi batas None
        accuracy=92.0,
        retrieve=85, interpret=85, reflect=85,
        grade=1, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    # BR-05 tidak terpicu, jadi STAY default
    assert decision.status == "STAY"
    assert decision.focus is None or decision.focus != "Fluency"


# ========== Test BR-07 dengan consecutive_drops dari riwayat (D3) ==========

def test_br07_single_drop_stay_monitor():
    """BR-07: 1 penurunan → STAY + MONITOR."""
    inp = AdaptiveInput(
        wcpm=60, accuracy=92.0,
        retrieve=85, interpret=85, reflect=85,
        grade=2, season="fall",
        consecutive_drops=1,
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "STAY"
    assert decision.focus == "Monitor"
    assert any(r["rule"] == "BR-07" and r["fired"] for r in decision.rules_fired)


def test_br07_consistent_drop_review():
    """BR-07: ≥2 penurunan berturut-turut → REVIEW/REMEDIAL."""
    inp = AdaptiveInput(
        wcpm=50, accuracy=91.0,
        retrieve=82, interpret=82, reflect=82,
        grade=2, season="fall",
        consecutive_drops=2,
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "STAY"
    assert "REVIEW" in decision.recommendation or "REMEDIAL" in decision.recommendation


# ========== Test calculate_consecutive_drops (D3) ==========

def test_consecutive_drops_no_history():
    """Asesmen pertama → drops=0."""
    drops, prev_w, prev_a = calculate_consecutive_drops(60, 95, [])
    assert drops == 0
    assert prev_w is None
    assert prev_a is None


def test_consecutive_drops_single():
    """1 penurunan."""
    history = [
        {"status": "STAY", "wcpm": 70, "accuracy": 95},
    ]
    drops, prev_w, prev_a = calculate_consecutive_drops(65, 94, history)
    assert drops == 1  # WCPM turun 70→65 atau Accuracy turun 95→94
    assert prev_w == 70
    assert prev_a == 95


def test_consecutive_drops_multiple():
    """2 penurunan berturut-turut."""
    history = [
        {"status": "STAY", "wcpm": 80, "accuracy": 96},
        {"status": "STAY", "wcpm": 75, "accuracy": 94},  # turun dari 80
    ]
    drops, prev_w, prev_a = calculate_consecutive_drops(70, 93, history)
    assert drops == 2  # current turun dari 75, 75 turun dari 80


def test_consecutive_drops_no_drop():
    """Tidak ada penurunan → drops=0."""
    history = [
        {"status": "STAY", "wcpm": 60, "accuracy": 90},
    ]
    drops, prev_w, prev_a = calculate_consecutive_drops(65, 92, history)
    assert drops == 0


# ========== Test default STAY ==========

def test_default_stay():
    """Tidak ada aturan terpicu → STAY."""
    inp = AdaptiveInput(
        wcpm=60, accuracy=92.0,
        retrieve=85, interpret=85, reflect=85,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "STAY"


# ========== Test rules_fired recorded ==========

def test_rules_fired_recorded():
    """Setiap BR mencatat fired/not fired."""
    inp = AdaptiveInput(
        wcpm=50, accuracy=85.0,  # BR-01 terpicu
        retrieve=90, interpret=90, reflect=90,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert len(decision.rules_fired) > 0
    assert any(r["rule"] == "BR-01" for r in decision.rules_fired)


# ========== Test skenario demo F-08 (Kelas 2, awal tahun, batas WCPM=40) ==========

def test_demo_scenario_assessment_1():
    """A1: WCPM 58, Acc 92%, R85/I70/Rf60 → fokus Interpret & Reflect.
    
    Status mengikuti Q13 (sementara): BR-02 (Interpret 70% < 80%) → INTERVENE.
    """
    inp = AdaptiveInput(
        wcpm=58, accuracy=92.0,
        retrieve=85, interpret=70, reflect=60,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    # BR-02: Interpret < 80 atau Reflect < 80
    assert decision.status == "INTERVENE"
    assert decision.focus in ["Interpret", "Reflect"]


def test_demo_scenario_assessment_2():
    """A2: WCPM 68, Acc 95%, R90/I86/Rf82 → PROMOTION_CANDIDATE."""
    inp = AdaptiveInput(
        wcpm=68, accuracy=95.0,
        retrieve=90, interpret=86, reflect=82,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "PROMOTION_CANDIDATE"
    assert "reassess" in decision.recommendation.lower()


def test_demo_scenario_assessment_3():
    """A3: WCPM 75, Acc 96%, R92/I88/Rf84 → PROMOTE (prev=CANDIDATE)."""
    inp = AdaptiveInput(
        wcpm=75, accuracy=96.0,
        retrieve=92, interpret=88, reflect=84,
        grade=2, season="fall",
        previous_status="PROMOTION_CANDIDATE",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "PROMOTE"
    assert decision.next_reading_level == 2


# ========== Test urutan prioritas aturan (D4) ==========

def test_rule_priority_br01_first():
    """BR-01 terpicu lebih dulu meski BR-02 juga memenuhi."""
    inp = AdaptiveInput(
        wcpm=50, accuracy=85.0,  # BR-01
        retrieve=70, interpret=70, reflect=70,  # BR-02
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "INTERVENE"
    assert decision.focus == "Fluency/Accuracy"  # BR-01 prioritas


def test_rule_priority_br02_before_br05():
    """BR-02 terpicu lebih dulu dari BR-05."""
    inp = AdaptiveInput(
        wcpm=30,  # rendah (BR-05)
        accuracy=92.0,
        retrieve=70,  # < 80 (BR-02)
        interpret=85, reflect=85,
        grade=2, season="fall",
        current_level=1,
    )
    decision = decide(inp)
    assert decision.status == "INTERVENE"
    assert decision.focus == "Retrieve"  # BR-02 prioritas
