"""Test seed validator (F-04)."""
import pytest

from seed.reading_texts import READING_TEXTS
from seed.validator import (
    LEVEL_LIMITS,
    SeedValidationError,
    count_words,
    split_paragraphs,
    split_sentences,
    validate_all,
    validate_or_raise,
    validate_reading,
)


def test_all_seed_readings_valid():
    """Semua teks seed harus valid."""
    errors = validate_all(READING_TEXTS)
    assert errors == [], f"Seed errors: {errors}"


def test_seed_count():
    """Seed harus 5-10 teks."""
    assert 5 <= len(READING_TEXTS) <= 10


def test_seed_covers_all_levels():
    """Seed harus mencakup Level 1, 2, dan 3."""
    complexities = {r["complexity"] for r in READING_TEXTS}
    assert complexities == {1, 2, 3}


def test_seed_book_level_consistent():
    """book_level harus konsisten dengan complexity."""
    mapping = {1: "B1", 2: "B2", 3: "B3"}
    for r in READING_TEXTS:
        assert r["book_level"] == mapping[r["complexity"]], f"{r['id']} book_level salah"


def test_seed_questions_count():
    """Setiap teks punya 3-5 pertanyaan."""
    for r in READING_TEXTS:
        n = len(r.get("questions", []))
        assert 3 <= n <= 5, f"{r['id']} punya {n} pertanyaan"


def test_seed_questions_competencies():
    """Pertanyaan harus berlabel retrieve/interpret/reflect."""
    valid = {"retrieve", "interpret", "reflect"}
    for r in READING_TEXTS:
        for q in r.get("questions", []):
            assert q["competency"] in valid


def test_count_words():
    assert count_words("satu dua tiga") == 3
    assert count_words("") == 0


def test_split_sentences():
    text = "Halo dunia. Apa kabar? Baik!"
    sents = split_sentences(text)
    assert len(sents) == 3


def test_split_paragraphs():
    text = "Para satu.\n\nPara dua.\n\nPara tiga."
    paras = split_paragraphs(text)
    assert len(paras) == 3


def test_validator_rejects_too_many_words_per_sentence():
    """Validator menolak kalimat dengan kata melebihi batas."""
    bad = {
        "id": "bad-1",
        "content": "Ini adalah kalimat yang sangat panjang sekali dengan banyak kata di dalamnya. "
                   "Kalimat kedua pendek. Kalimat ketiga pendek. Kalimat keempat pendek. "
                   "Kalimat kelima pendek.",
        "complexity": 1,  # maks 7 kata/kalimat
        "book_level": "B1",
        "questions": [
            {"competency": "retrieve"}, {"competency": "interpret"}, {"competency": "reflect"},
        ],
    }
    errors = validate_reading(bad)
    assert any("kata > maks" in e for e in errors)


def test_validator_rejects_wrong_book_level():
    """Validator menolak book_level tidak konsisten."""
    bad = {
        "id": "bad-2",
        "content": "Kalimat pendek. Kalimat pendek. Kalimat pendek. Kalimat pendek. Kalimat pendek.",
        "complexity": 1,
        "book_level": "B3",  # harus B1
        "questions": [
            {"competency": "retrieve"}, {"competency": "interpret"}, {"competency": "reflect"},
        ],
    }
    errors = validate_reading(bad)
    assert any("book_level" in e for e in errors)


def test_validator_rejects_too_few_questions():
    """Validator menolak pertanyaan < 3."""
    bad = {
        "id": "bad-3",
        "content": "Kalimat pendek. Kalimat pendek. Kalimat pendek. Kalimat pendek. Kalimat pendek.",
        "complexity": 1,
        "book_level": "B1",
        "questions": [{"competency": "retrieve"}],
    }
    errors = validate_reading(bad)
    assert any("pertanyaan" in e for e in errors)


def test_validator_rejects_paragraph_in_level1():
    """Validator menolak paragraf di Level 1."""
    bad = {
        "id": "bad-4",
        "content": "Kalimat satu pendek.\n\nKalimat dua pendek. Kalimat tiga pendek. Kalimat empat pendek. Kalimat lima pendek.",
        "complexity": 1,
        "book_level": "B1",
        "questions": [
            {"competency": "retrieve"}, {"competency": "interpret"}, {"competency": "reflect"},
        ],
    }
    errors = validate_reading(bad)
    assert any("paragraf" in e for e in errors)


def test_validate_or_raise_ok():
    """validate_or_raise tidak raise untuk seed valid."""
    validate_or_raise(READING_TEXTS)  # tidak raise
