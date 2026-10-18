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


def test_seed_questions_options_and_answer():
    """Setiap pertanyaan punya tepat 2 opsi dan kuncinya menunjuk opsi yang ada.

    Mode Siswa hanya merender pilihan ganda dan skoring backend mencocokkan
    `answer_id` dengan opsi yang dipilih; pertanyaan tanpa opsi (atau dengan
    kunci yang tidak menunjuk opsi mana pun) mustahil dijawab.
    """
    for r in READING_TEXTS:
        for q in r.get("questions", []):
            opts = q.get("options", [])
            assert len(opts) == 2, f"{r['id']}/{q['id']} punya {len(opts)} opsi, harus 2"
            ids = [o["id"] for o in opts]
            assert len(set(ids)) == 2, f"{r['id']}/{q['id']} id opsi duplikat: {ids}"
            assert all(o.get("text") for o in opts), f"{r['id']}/{q['id']} ada opsi tanpa teks"
            assert q["answer_id"] in ids, (
                f"{r['id']}/{q['id']} answer_id '{q['answer_id']}' bukan salah satu opsi {ids}"
            )


def test_seed_answers_not_always_first_option():
    """Kunci jawaban harus tersebar, bukan selalu opsi 'a'.

    Seed lama menaruh semua kunci di opsi "a", sehingga siswa bisa menebak benar
    tanpa membaca teks.
    """
    answers = [q["answer_id"] for r in READING_TEXTS for q in r["questions"]]
    assert answers.count("a") < len(answers), "semua kunci di opsi 'a'"
    assert answers.count("b") >= len(READING_TEXTS) // 2, (
        f"kunci di opsi 'b' terlalu sedikit: {answers.count('b')} dari {len(answers)}"
    )


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


def test_validator_rejects_too_many_sentences():
    """Validator menolak teks dengan kalimat melebihi batas level.

    Sejak materi "target panjang 2x", batasnya dinyatakan per teks (bukan per
    halaman) karena aplikasi tidak punya konsep halaman. Level 1 = maks 10 kalimat.
    """
    bad = {
        "id": "bad-4",
        "content": " ".join(["Ani membaca buku."] * 11),
        "complexity": 1,  # maks 10 kalimat
        "book_level": "B1",
        "questions": [
            {"competency": "retrieve"}, {"competency": "interpret"}, {"competency": "reflect"},
        ],
    }
    errors = validate_reading(bad)
    assert any("kalimat > maks" in e for e in errors), errors


def test_validator_rejects_too_many_paragraphs():
    """Validator menolak teks dengan paragraf melebihi batas level.

    Paragraf kini diizinkan di semua level (Level 1-2 maks 2, Level 3 maks 7),
    jadi yang diuji adalah batas jumlahnya, bukan larangan adanya paragraf.
    """
    bad = {
        "id": "bad-5",
        "content": "Bagian satu di sini.\n\nBagian dua di sini.\n\nBagian tiga di sini.",
        "complexity": 1,  # maks 2 paragraf
        "book_level": "B1",
        "questions": [
            {"competency": "retrieve"}, {"competency": "interpret"}, {"competency": "reflect"},
        ],
    }
    errors = validate_reading(bad)
    assert any("paragraf > maks" in e for e in errors), errors


def test_validate_or_raise_ok():
    """validate_or_raise tidak raise untuk seed valid."""
    validate_or_raise(READING_TEXTS)  # tidak raise


# ========== UUID tetap (Fase 1) ==========

def test_seed_ids_are_valid_uuid():
    """Semua id seed harus uuid valid (bentuk in-memory == Supabase)."""
    import uuid as _uuid

    from seed.reading_texts import SEED_CLASSES, SEED_IDS, SEED_STUDENTS

    for key, value in SEED_IDS.items():
        assert _uuid.UUID(str(value)), f"SEED_IDS[{key}] bukan uuid"
    for r in READING_TEXTS:
        assert _uuid.UUID(str(r["id"])), f"reading {r['title']} id bukan uuid"
    for c in SEED_CLASSES:
        assert _uuid.UUID(str(c["id"]))
    for s in SEED_STUDENTS:
        assert _uuid.UUID(str(s["id"]))


def test_seed_ids_unique():
    """Tidak ada uuid yang terpakai ganda."""
    from seed.reading_texts import SEED_IDS

    values = list(SEED_IDS.values())
    assert len(values) == len(set(values)), "uuid seed duplikat"


def test_seed_students_reference_seed_classes():
    """class_id siswa harus merujuk kelas seed (FK konsisten)."""
    from seed.reading_texts import SEED_CLASSES, SEED_STUDENTS

    class_ids = {c["id"] for c in SEED_CLASSES}
    for s in SEED_STUDENTS:
        assert s["class_id"] in class_ids, f"{s['name']} class_id bukan kelas seed"


def test_legacy_id_map_points_to_seed_ids():
    """Alias lama harus menunjuk uuid seed yang benar."""
    from seed.reading_texts import LEGACY_ID_MAP, SEED_IDS

    assert LEGACY_ID_MAP["rd-001"] == SEED_IDS["reading_1"]
    assert LEGACY_ID_MAP["std-001"] == SEED_IDS["student_dika"]
    assert LEGACY_ID_MAP["cls-2a"] == SEED_IDS["class_2a"]
