"""Test repository layer (in-memory)."""
import pytest

from repository import InMemoryRepository


@pytest.fixture
def repo():
    return InMemoryRepository()


def test_student_crud(repo):
    students = repo.list_students()
    assert len(students) > 0
    s = repo.create_student("Test", 1, "cls-1a")
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
    a = repo.create_assessment("std-001", "rd-004")
    assert a["id"]
    updated = repo.update_assessment(a["id"], {"status": "STAY"})
    assert updated["status"] == "STAY"


def test_update_nonexistent_assessment(repo):
    with pytest.raises(ValueError):
        repo.update_assessment("xxx", {"status": "STAY"})


def test_list_student_assessments_ordered(repo):
    """Riwayat terurut waktu (descending)."""
    repo.create_assessment("std-001", "rd-004")
    repo.create_assessment("std-001", "rd-005")
    history = repo.list_student_assessments("std-001")
    assert len(history) == 2
    # Terurut descending by created_at
    if len(history) == 2:
        assert history[0]["created_at"] >= history[1]["created_at"]
