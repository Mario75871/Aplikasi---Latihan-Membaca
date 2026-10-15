"""Validator seed teks bacaan (F-04, v2.5).

Menolak teks yang melanggar batas level:
- Level 1 (B1): maks 7 kata/kalimat, maks 5 kalimat/halaman, panjang 25-35 kata
- Level 2 (B2): maks 9 kata/kalimat, maks 7 kalimat/halaman, panjang 45-63 kata
- Level 3 (B3): maks 12 kata/kalimat, maks 3 paragraf/halaman,
  maks 3 kalimat/paragraf, panjang 80-108 kata
"""
from __future__ import annotations

import re

# Batas per level (F-04)
LEVEL_LIMITS = {
    1: {
        "max_words_per_sentence": 7,
        "max_sentences_per_page": 5,
        "min_word_count": 25,
        "max_word_count": 35,
        "structure": "flat",  # kalimat tunggal, belum ada paragraf
    },
    2: {
        "max_words_per_sentence": 9,
        "max_sentences_per_page": 7,
        "min_word_count": 45,
        "max_word_count": 63,
        "structure": "flat",
    },
    3: {
        "max_words_per_sentence": 12,
        "max_paragraphs_per_page": 3,
        "max_sentences_per_paragraph": 3,
        "min_word_count": 80,
        "max_word_count": 108,
        "structure": "paragraph",
    },
}

LEVEL_TO_BOOK = {1: "B1", 2: "B2", 3: "B3"}


class SeedValidationError(Exception):
    """Error validasi seed."""
    pass


def count_words(text: str) -> int:
    """Hitung jumlah kata (pisah whitespace)."""
    return len(text.split())


def split_sentences(text: str) -> list[str]:
    """Pisah teks menjadi kalimat (berdasarkan . ! ?)."""
    # Split by sentence-ending punctuation
    parts = re.split(r"[.!?]+", text)
    return [p.strip() for p in parts if p.strip()]


def split_paragraphs(text: str) -> list[str]:
    """Pisah teks menjadi paragraf (berdasarkan newline ganda)."""
    parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in parts if p.strip()]


def validate_reading(reading: dict) -> list[str]:
    """Validasi satu teks bacaan. Mengembalikan list error (kosong bila valid)."""
    errors = []
    
    complexity = reading.get("complexity")
    if complexity not in LEVEL_LIMITS:
        errors.append(f"complexity tidak valid: {complexity}")
        return errors
    
    limits = LEVEL_LIMITS[complexity]
    content = reading.get("content", "")
    reading_id = reading.get("id", "?")
    
    # Validasi book_level konsisten
    expected_book = LEVEL_TO_BOOK[complexity]
    if reading.get("book_level") != expected_book:
        errors.append(
            f"{reading_id}: book_level '{reading.get('book_level')}' tidak konsisten "
            f"dengan complexity {complexity} (harus {expected_book})"
        )
    
    # Validasi jumlah kata
    wc = count_words(content)
    if wc < limits["min_word_count"]:
        errors.append(
            f"{reading_id}: jumlah kata {wc} < minimum {limits['min_word_count']} "
            f"(Level {complexity})"
        )
    if wc > limits["max_word_count"]:
        errors.append(
            f"{reading_id}: jumlah kata {wc} > maksimum {limits['max_word_count']} "
            f"(Level {complexity})"
        )
    
    # Validasi kata per kalimat
    sentences = split_sentences(content)
    max_wps = limits["max_words_per_sentence"]
    for i, sent in enumerate(sentences):
        n = count_words(sent)
        if n > max_wps:
            errors.append(
                f"{reading_id}: kalimat {i+1} punya {n} kata > maks {max_wps} "
                f"(Level {complexity}): '{sent[:40]}...'"
            )
    
    # Validasi struktur
    if limits["structure"] == "flat":
        # Level 1-2: maks kalimat per halaman, tidak ada paragraf
        if "\n\n" in content:
            errors.append(f"{reading_id}: Level {complexity} tidak boleh punya paragraf")
        max_spp = limits["max_sentences_per_page"]
        if len(sentences) > max_spp:
            errors.append(
                f"{reading_id}: {len(sentences)} kalimat > maks {max_spp} per halaman "
                f"(Level {complexity})"
            )
    else:
        # Level 3: paragraf
        paragraphs = split_paragraphs(content)
        max_ppp = limits["max_paragraphs_per_page"]
        if len(paragraphs) > max_ppp:
            errors.append(
                f"{reading_id}: {len(paragraphs)} paragraf > maks {max_ppp} "
                f"(Level {complexity})"
            )
        max_spp = limits["max_sentences_per_paragraph"]
        for i, para in enumerate(paragraphs):
            n_sent = len(split_sentences(para))
            if n_sent > max_spp:
                errors.append(
                    f"{reading_id}: paragraf {i+1} punya {n_sent} kalimat > maks {max_spp} "
                    f"(Level {complexity})"
                )
    
    # Validasi pertanyaan (3-5, label retrieve/interpret/reflect)
    questions = reading.get("questions", [])
    if not (3 <= len(questions) <= 5):
        errors.append(
            f"{reading_id}: jumlah pertanyaan {len(questions)}, harus 3-5"
        )
    competencies = {q.get("competency") for q in questions}
    valid_competencies = {"retrieve", "interpret", "reflect"}
    if not competencies.issubset(valid_competencies):
        errors.append(
            f"{reading_id}: kompetensi tidak valid: {competencies - valid_competencies}"
        )
    
    return errors


def validate_all(readings: list[dict]) -> list[str]:
    """Validasi semua teks. Mengembalikan semua error."""
    all_errors = []
    for r in readings:
        all_errors.extend(validate_reading(r))
    return all_errors


def validate_or_raise(readings: list[dict]) -> None:
    """Validasi dan raise bila ada error."""
    errors = validate_all(readings)
    if errors:
        raise SeedValidationError(
            f"Seed validation failed dengan {len(errors)} error:\n" + "\n".join(errors)
        )
