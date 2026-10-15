"""Normalization profile tests."""

from __future__ import annotations

from reading_framework.alignment import (
    normalize_chars,
    normalize_for_alignment,
    normalize_tokens,
)
from reading_framework.config import NormalizationProfile


def test_lowercase_and_punctuation_stripped():
    assert normalize_for_alignment("Halo, Dunia!") == "halo dunia"


def test_curly_apostrophes_normalized():
    assert normalize_for_alignment("don\u2019t") == "don't"


def test_whitespace_collapsed_and_trimmed():
    assert normalize_for_alignment("  halo    dunia  ") == "halo dunia"


def test_leading_space_token_preserved_in_raw_but_not_comparison():
    # token mentah Whisper sering punya leading space; normalisasi harus stabil
    assert normalize_tokens(" Grafik perkembangan") == ["grafik", "perkembangan"]


def test_normalize_chars_removes_spaces():
    assert normalize_chars("a b c") == "abc"


def test_profile_toggle_case_sensitive():
    profile = NormalizationProfile(lowercase=False)
    assert normalize_for_alignment("Halo", profile) == "Halo"


def test_empty_and_none():
    assert normalize_for_alignment(None) == ""
    assert normalize_for_alignment("") == ""
    assert normalize_tokens("   ") == []


def test_numbers_are_not_word_normalized():
    # tidak ada normalisasi angka->kata otomatis. Tanda baca (titik) dibuang
    # sesuai profil, jadi "4.2" -> "4 2" (eksplisit & terdokumentasi).
    assert normalize_tokens("47 pasukan") == ["47", "pasukan"]
    assert normalize_tokens("4.2 juta") == ["4", "2", "juta"]
