"""Metric tests: WER/CER/S-D-I + status not_computed handling."""

from __future__ import annotations

import math

from reading_framework.metrics import (
    STATUS_COMPUTED,
    STATUS_NOT_COMPUTED,
    REASON_REFERENCE_INVALID,
    REASON_REFERENCE_NOT_PROVIDED,
    calculate_metrics,
)


def test_identical_zero_wer_cer():
    m = calculate_metrics("halo dunia", "halo dunia")
    assert m.status == STATUS_COMPUTED
    assert m.wer == 0.0
    assert m.cer == 0.0


def test_one_substitution():
    m = calculate_metrics("ibu pergi ke pasar", "ibu pergi ke pasap")
    assert m.substitutions == 1
    assert m.wer == 1 / 4


def test_one_deletion():
    m = calculate_metrics("a b c", "a c")
    assert m.deletions == 1
    assert m.wer == 1 / 3


def test_one_insertion():
    m = calculate_metrics("a c", "a b c")
    assert m.insertions == 1
    assert m.wer == 1 / 2


def test_combined_edits_wer_matches_formula():
    m = calculate_metrics("a b c d", "a x c d e")
    assert m.wer == (m.substitutions + m.deletions + m.insertions) / 4


def test_edit_distance_consistent_with_counts():
    m = calculate_metrics("a b c d", "a x c d e")
    assert m.edit_distance == m.substitutions + m.deletions + m.insertions


def test_reference_not_provided_is_not_computed():
    m = calculate_metrics(None, "a b")
    assert m.status == STATUS_NOT_COMPUTED
    assert m.reason == REASON_REFERENCE_NOT_PROVIDED
    assert m.wer is None


def test_reference_empty_is_not_computed_no_div_by_zero():
    m = calculate_metrics("   ", "a b")
    assert m.status == STATUS_NOT_COMPUTED
    assert m.reason == REASON_REFERENCE_INVALID
    assert m.wer is None  # bukan 0


def test_wer_not_rounded_internally():
    m = calculate_metrics("a b c", "a b d")
    assert not m.wer.is_integer() or m.wer == m.wer
    assert math.isclose(m.wer, 1 / 3, rel_tol=1e-12)


def test_cer_uses_char_distance():
    m = calculate_metrics("kucing", "kucin")
    assert m.cer is not None and 0 < m.cer < 1


def test_wer_zero_does_not_imply_pronunciation():
    # metrik hanya angka; interpretasi ada di assessment (tetap false)
    m = calculate_metrics("ibu pergi ke pasar", "ibu pergi ke pasar")
    assert m.wer == 0.0
