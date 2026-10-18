"""Tests untuk normalisasi ejaan ID opsional (tahap terpisah setelah ASR)."""

from __future__ import annotations

from reading_framework.spelling_normalization import (
    CURATED_RULES,
    SPELLING_NORMALIZATION_PROFILE_ID,
    SpellingRule,
    normalize_spelling,
)


def test_computer_normalized_to_komputer_with_change_record():
    res = normalize_spelling("Computer diperbaiki di Jakarta")
    assert res.text == "Komputer diperbaiki di Jakarta"
    assert len(res.changes) == 1
    change = res.changes[0]
    assert change.original == "Computer"
    assert change.normalized == "Komputer"
    assert change.rule_id == "id_computer_komputer"
    assert change.source  # aturan wajib punya dasar
    assert change.reason


def test_lowercase_computer():
    res = normalize_spelling("computer rusak")
    assert res.text == "komputer rusak"
    assert res.changes[0].original == "computer"
    assert res.changes[0].normalized == "komputer"


def test_unknown_words_are_not_changed():
    res = normalize_spelling("jakarta xyz dolar suharto")
    assert res.text == "jakarta xyz dolar suharto"
    assert res.changes == []


def test_word_containing_rule_is_not_touched():
    # 'komputernya' bukan token 'computer' -> tidak diubah
    res = normalize_spelling("komputernya computer")
    assert res.text == "komputernya komputer"
    assert len(res.changes) == 1


def test_disabled_returns_input_unchanged():
    res = normalize_spelling("Computer diperbaiki", enabled=False)
    assert res.text == "Computer diperbaiki"
    assert res.changes == []
    assert res.enabled is False


def test_none_input_is_empty():
    res = normalize_spelling(None)
    assert res.text == ""
    assert res.changes == []


def test_profile_id_present():
    res = normalize_spelling("computer")
    assert res.profile_id == SPELLING_NORMALIZATION_PROFILE_ID


def test_custom_rules_only_verified_applied():
    rule = SpellingRule(rule_id="x", original="dolar", normalized="dolar",
                        reason="no-op", source="test")
    res = normalize_spelling("dolar", rules=[rule])
    assert res.text == "dolar"
    assert res.changes == []


def test_curated_rules_have_sources():
    for rule in CURATED_RULES:
        assert rule.source, f"rule {rule.rule_id} missing verification source"


def test_position_recorded():
    res = normalize_spelling("Computer")
    assert res.changes[0].position == 0
