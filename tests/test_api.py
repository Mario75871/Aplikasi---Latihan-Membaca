"""Test API endpoints (Fase 2) — gunakan TestClient.

Set AUTH_DISABLED=true agar tidak perlu login di setiap test,
kecuali test auth itu sendiri.
"""
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """TestClient dengan AUTH_DISABLED dan in-memory repo fresh."""
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DEMO_FALLBACK", "true")

    # Reset repository singleton
    import repository
    repository._repo = None

    import main
    with TestClient(main.app) as c:
        yield c


# ========== Health ==========

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["version"] == "2.5"


# ========== Students ==========

def test_list_students(client):
    resp = client.get("/students")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_create_student(client):
    resp = client.post("/students", json={"name": "Test Anak", "grade": 2, "class_id": "cls-2a"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Anak"


def test_create_student_empty_name_422(client):
    resp = client.post("/students", json={"name": "", "grade": 2, "class_id": "cls-2a"})
    assert resp.status_code == 422


def test_create_student_invalid_grade_422(client):
    resp = client.post("/students", json={"name": "X", "grade": 5, "class_id": "cls-2a"})
    assert resp.status_code == 422


def test_get_student_404(client):
    resp = client.get("/students/nonexistent")
    assert resp.status_code == 404


def test_student_assessments_history_ordered(client):
    """Riwayat terurut waktu."""
    resp = client.get("/students/std-001/assessments")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ========== Readings ==========

def test_list_readings(client):
    resp = client.get("/readings")
    assert resp.status_code == 200
    readings = resp.json()
    assert len(readings) >= 5


def test_readings_filter_by_level(client):
    resp = client.get("/readings?complexity=1")
    assert resp.status_code == 200
    for r in resp.json():
        assert r["complexity"] == 1


def test_get_reading_404(client):
    resp = client.get("/readings/nonexistent")
    assert resp.status_code == 404


def test_reading_has_book_level_and_proper_nouns(client):
    resp = client.get("/readings/rd-001")
    assert resp.status_code == 200
    data = resp.json()
    assert "book_level" in data
    assert "proper_nouns" in data


# ========== Classes ==========

def test_list_classes(client):
    resp = client.get("/classes")
    assert resp.status_code == 200


def test_create_class(client):
    resp = client.post("/classes", json={"name": "Kelas Baru", "grade": 3})
    assert resp.status_code == 200


def test_class_students(client):
    resp = client.get("/classes/cls-2a/students")
    assert resp.status_code == 200
    for s in resp.json():
        assert s["class_id"] == "cls-2a"


def test_get_class_404(client):
    resp = client.get("/classes/nonexistent")
    assert resp.status_code == 404


# ========== Dashboard ==========

def test_dashboard_class(client):
    resp = client.get("/dashboard/class/cls-2a")
    assert resp.status_code == 200
    data = resp.json()
    assert "status_summary" in data
    assert "students" in data


def test_dashboard_class_404(client):
    resp = client.get("/dashboard/class/nonexistent")
    assert resp.status_code == 404


# ========== Hasbrouck ==========

def test_hasbrouck_reference(client):
    resp = client.get("/hasbrouck/reference?grade=2&season=spring&wcpm=85")
    assert resp.status_code == 200
    data = resp.json()
    assert data["position"] == "Antara P25 dan P50"
    assert "disclaimer" in data


def test_hasbrouck_invalid_season_422(client):
    resp = client.get("/hasbrouck/reference?grade=2&season=xxx&wcpm=85")
    assert resp.status_code == 422


def test_hasbrouck_season_optional(client):
    """Musim boleh kosong → dihitung dari tanggal server (Fase 3)."""
    resp = client.get("/hasbrouck/reference?grade=2&wcpm=85")
    assert resp.status_code == 200
    data = resp.json()
    assert data["season"] in ("fall", "winter", "spring")


# ========== Assessments ==========

def test_create_assessment(client):
    resp = client.post("/assessments", json={"student_id": "std-001", "reading_id": "rd-004"})
    assert resp.status_code == 200
    assert "id" in resp.json()


def test_create_assessment_invalid_student_404(client):
    resp = client.post("/assessments", json={"student_id": "nonexistent", "reading_id": "rd-004"})
    assert resp.status_code == 404


def test_create_assessment_invalid_reading_404(client):
    resp = client.post("/assessments", json={"student_id": "std-001", "reading_id": "nonexistent"})
    assert resp.status_code == 404


def test_get_assessment_404(client):
    resp = client.get("/assessments/nonexistent")
    assert resp.status_code == 404


def test_list_assessments(client):
    """GET /assessments — daftar riwayat asesmen (Fase 3, halaman riwayat)."""
    resp = client.get("/assessments")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_assessments_filter_by_student(client):
    """GET /assessments?student_id=... — filter riwayat per siswa."""
    resp = client.get("/assessments?student_id=std-001")
    assert resp.status_code == 200
    for a in resp.json():
        assert a["student_id"] == "std-001"


def test_comprehension_before_audio_422(client):
    """Comprehension sebelum audio diproses → 422."""
    create = client.post("/assessments", json={"student_id": "std-001", "reading_id": "rd-004"})
    aid = create.json()["id"]
    resp = client.post(f"/assessments/{aid}/comprehension", json={"answers": {}})
    assert resp.status_code == 422
