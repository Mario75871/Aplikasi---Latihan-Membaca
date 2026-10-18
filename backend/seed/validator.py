"""Validator seed teks bacaan (F-04, v2.5 "target panjang 2x").

Menolak teks yang melanggar batas level:
- Level 1 (B1): maks 7 kata/kalimat, maks 10 kalimat, maks 2 paragraf, 50-70 kata
- Level 2 (B2): maks 9 kata/kalimat, maks 14 kalimat, maks 2 paragraf, 90-126 kata
- Level 3 (B3): maks 12 kata/kalimat, maks 21 kalimat, maks 7 paragraf,
  maks 3 kalimat/paragraf, 160-216 kata

Catatan batas "per halaman" -> "per teks": dulu batas kalimat disebut per halaman
dan Level 1-2 dilarang punya paragraf. Ternyata aplikasi tidak punya konsep
halaman sama sekali (ReadingPassage merender seluruh isi sebagai satu blok teks
yang dipecah per kata untuk highlight rekaman), sehingga batas "per halaman"
selalu efektifnya "per teks". Sejak materi 2x, batasnya dinyatakan apa adanya
sebagai batas per teks dan pemenggalan paragraf (\n\n) diizinkan di semua level.
"""
from __future__ import annotations

import re

# Batas per level (F-04, target panjang 2x)
LEVEL_LIMITS = {
    1: {
        "max_words_per_sentence": 7,
        "max_sentences": 10,
        "max_paragraphs": 2,
        "min_word_count": 50,
        "max_word_count": 70,
    },
    2: {
        "max_words_per_sentence": 9,
        "max_sentences": 14,
        "max_paragraphs": 2,
        "min_word_count": 90,
        "max_word_count": 126,
    },
    3: {
        "max_words_per_sentence": 12,
        "max_sentences": 21,
        "max_paragraphs": 7,
        "max_sentences_per_paragraph": 3,
        "min_word_count": 160,
        "max_word_count": 216,
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
    
    # Validasi struktur (batas per teks; lihat catatan di docstring modul)
    max_sent = limits["max_sentences"]
    if len(sentences) > max_sent:
        errors.append(
            f"{reading_id}: {len(sentences)} kalimat > maks {max_sent} "
            f"(Level {complexity})"
        )

    paragraphs = split_paragraphs(content)
    max_par = limits["max_paragraphs"]
    if len(paragraphs) > max_par:
        errors.append(
            f"{reading_id}: {len(paragraphs)} paragraf > maks {max_par} "
            f"(Level {complexity})"
        )

    max_spp = limits.get("max_sentences_per_paragraph")
    if max_spp:
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
