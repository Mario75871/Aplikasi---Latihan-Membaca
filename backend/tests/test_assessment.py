"""Test Assessment Engine — WCPM dan Accuracy (Fase 1B)."""
import pytest

from services.assessment import calculate_accuracy, calculate_wcpm, classify_accuracy


def test_wcpm_formula():
    """WCPM = Correct Words / Reading Time × 60."""
    wcpm = calculate_wcpm(correct_words=30, duration_seconds=120)
    assert wcpm == 15.0  # 30 / 120 * 60 = 15


def test_wcpm_zero_time_is_safe():
    """Durasi 0 → None (tidak dapat dihitung), tidak crash. null ≠ 0."""
    wcpm = calculate_wcpm(correct_words=10, duration_seconds=0)
    assert wcpm is None


def test_wcpm_negative_time_is_safe():
    """Durasi negatif → None."""
    wcpm = calculate_wcpm(correct_words=10, duration_seconds=-5)
    assert wcpm is None


def test_wcpm_none_duration_is_safe():
    """Durasi None (tak tersedia) → None, bukan 0."""
    wcpm = calculate_wcpm(correct_words=10, duration_seconds=None)
    assert wcpm is None


def test_accuracy_formula():
    """Accuracy = Correct Words / Total Words Read × 100."""
    accuracy = calculate_accuracy(correct_words=30, total_words_read=32)
    assert accuracy == 93.75  # 30 / 32 * 100


def test_accuracy_uses_reference_denominator():
    """Total Words Read dari reference yang dicoba, bukan transcript."""
    # Sesuai acceptance criteria F-06:
    # Reference "Ibu pergi ke sekolah setiap pagi" (7 kata)
    # Transcript "Ibu pergi sekolah setiap pagi" (6 kata, "ke" hilang)
    # Total Words Read = 6 (kata yang dicoba, "ke" deletion)
    accuracy = calculate_accuracy(correct_words=6, total_words_read=6)
    assert accuracy == 100.0


def test_accuracy_zero_denominator_is_safe():
    """Total 0 → None (tidak dapat dihitung), tidak crash. null ≠ 0."""
    accuracy = calculate_accuracy(correct_words=0, total_words_read=0)
    assert accuracy is None


def test_accuracy_bands():
    """Klasifikasi accuracy sesuai kriteria Betts."""
    assert classify_accuracy(85.0) == "Perlu Intervensi"  # < 90
    assert classify_accuracy(89.9) == "Perlu Intervensi"
    assert classify_accuracy(90.0) == "Berkembang"  # 90-94
    assert classify_accuracy(92.0) == "Berkembang"
    assert classify_accuracy(94.9) == "Berkembang"
    assert classify_accuracy(95.0) == "Baik"  # >= 95
    assert classify_accuracy(100.0) == "Baik"


def test_accuracy_cannot_exceed_100():
    """Property test: bila correct <= total, accuracy <= 100."""
    # Ini dijamin oleh scoring.py (D1), test hanya memastikan formula
    for correct in range(0, 50):
        for total in range(correct, 50):
            if total > 0:
                acc = calculate_accuracy(correct, total)
                assert 0 <= acc <= 100
