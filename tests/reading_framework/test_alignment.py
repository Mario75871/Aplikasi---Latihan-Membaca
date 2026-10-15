"""Alignment per-kata tests: match/substitution/deletion/insertion + edge cases."""

from __future__ import annotations

from reading_framework.alignment import (
    OPERATION_DELETION,
    OPERATION_INSERTION,
    OPERATION_MATCH,
    OPERATION_SUBSTITUTION,
    align_words,
    edit_counts,
)


def _ops(reference, hypothesis):
    return [(op, r, h) for op, r, h in align_words(reference, hypothesis)]


def test_identical_all_matches():
    ops = _ops("ibu pergi ke pasar", "ibu pergi ke pasar")
    assert all(op == OPERATION_MATCH for op, _, _ in ops)
    assert edit_counts(ops) == {"matches": 4, "substitutions": 0,
                               "deletions": 0, "insertions": 0}


def test_single_substitution():
    ops = _ops("ibu pergi ke pasar", "ibu pergi ke pasap")
    assert ops[-1] == (OPERATION_SUBSTITUTION, "pasar", "pasap")
    assert edit_counts(ops)["substitutions"] == 1


def test_single_deletion_has_null_transcript_word():
    ops = _ops("a b c", "a c")
    assert ops[1] == (OPERATION_DELETION, "b", None)


def test_single_insertion_has_null_reference_word():
    ops = _ops("a c", "a b c")
    assert ops[1] == (OPERATION_INSERTION, None, "b")


def test_combined_edits():
    ops = _ops("a b c d", "a x c d e")
    counts = edit_counts(ops)
    assert counts["substitutions"] == 1  # b -> x
    assert counts["insertions"] == 1     # e
    assert counts["deletions"] == 0


def test_repeated_words_not_collapsed():
    ops = _ops("terima kasih terima kasih", "terima kasih terima kasih")
    assert edit_counts(ops)["matches"] == 4


def test_word_order_preserved():
    ops = _ops("satu dua tiga", "satu dua tiga")
    assert [r for _, r, _ in ops] == ["satu", "dua", "tiga"]


def test_punctuation_ignored_in_comparison():
    ops = _ops("Halo, dunia!", "halo dunia")
    assert all(op == OPERATION_MATCH for op, _, _ in ops)


def test_empty_both_sides():
    assert align_words("", "") == []


def test_empty_reference_all_insertions():
    ops = _ops("", "a b")
    assert all(op == OPERATION_INSERTION for op, _, _ in ops)


def test_empty_hypothesis_all_deletions():
    ops = _ops("a b", "")
    assert all(op == OPERATION_DELETION for op, _, _ in ops)


def test_leading_space_tokens_align_correctly():
    # token dengan leading space (umum dari Whisper) tidak boleh memecah alignment
    ops = _ops("Grafik perkembangan", " Grafik perkembangan")
    assert edit_counts(ops)["matches"] == 2
