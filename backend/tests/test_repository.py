"""Test repository layer (in-memory)."""
import pytest

from repository import InMemoryRepository
from seed.reading_texts import SEED_IDS


@pytest.fixture
def repo():
    return InMemoryRepository()


def test_student_crud(repo):
    students = repo.list_students()
    assert len(students) > 0
    s = repo.create_student("Test", 1, SEED_IDS["class_1a"])
    assert repo.get_student(s["id"])["name"] == "Test"


def test_get_nonexistent_student(repo):
    assert repo.get_student("xxx") is None


def test_readings_loaded_from_seed(repo):
    """Seed teks dimuat."""
    readings = repo.list_readings()
    assert len(readings) >= 5


def test_readings_filter(repo):
    r1 = repo.list_readings(complexity=1)
    for r in r1:
        assert r["complexity"] == 1


def test_class_crud(repo):
    c = repo.create_class("Kelas X", 3)
    assert repo.get_class(c["id"])["name"] == "Kelas X"


def test_assessment_lifecycle(repo):
    a = repo.create_assessment(SEED_IDS["student_dika"], SEED_IDS["reading_4"])
    assert a["id"]
    updated = repo.update_assessment(a["id"], {"status": "STAY"})
    assert updated["status"] == "STAY"


def test_update_nonexistent_assessment(repo):
    with pytest.raises(ValueError):
        repo.update_assessment("xxx", {"status": "STAY"})


def test_list_student_assessments_ordered(repo):
    """Riwayat terurut waktu (descending)."""
    repo.create_assessment(SEED_IDS["student_dika"], SEED_IDS["reading_4"])
    repo.create_assessment(SEED_IDS["student_dika"], SEED_IDS["reading_5"])
    history = repo.list_student_assessments(SEED_IDS["student_dika"])
    assert len(history) == 2
    # Terurut descending by created_at
    if len(history) == 2:
        assert history[0]["created_at"] >= history[1]["created_at"]


def test_word_scores_relational(repo):
    """Fase 0: word_scores disimpan di tabel relasional, bukan kolom assessments."""
    a = repo.create_assessment(SEED_IDS["student_dika"], SEED_IDS["reading_4"])
    repo.save_word_scores(a["id"], [
        {"position": 0, "reference_word": "ibu", "transcript_word": "ibu",
         "confidence": 0.9, "attempted": True, "is_correct": True,
         "is_proper_noun": False, "reason": "", "review_reasons": [],
         "ts_start": 0.0, "ts_end": 0.5},
    ])
    got = repo.get_assessment(a["id"])
    assert "word_scores" in got
    assert len(got["word_scores"]) == 1
    assert got["word_scores"][0]["reference_word"] == "ibu"
    # update_assessment tidak menyimpan word_scores sebagai kolom.
    repo.update_assessment(a["id"], {"status": "STAY"})
    assert len(repo.get_assessment(a["id"])["word_scores"]) == 1
