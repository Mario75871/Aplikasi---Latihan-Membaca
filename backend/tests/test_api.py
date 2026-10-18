"""Test API endpoints (Fase 2) — gunakan TestClient.

Set AUTH_DISABLED=true agar tidak perlu login di setiap test,
kecuali test auth itu sendiri.
"""
import os

import pytest
from fastapi.testclient import TestClient

from seed.reading_texts import SEED_IDS
from tests.conftest import unlock_level

STUDENT_DIKA = SEED_IDS["student_dika"]
CLASS_2A = SEED_IDS["class_2a"]
READING_1 = SEED_IDS["reading_1"]
READING_4 = SEED_IDS["reading_4"]


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


@pytest.fixture
def client_l2(client):
    """Level 1 Dika sudah tuntas → Level 2 (READING_4) boleh diases.

    Prasyarat gerbang naik level, bukan mematikannya; gerbangnya diuji di
    tests/test_progression.py.
    """
    import repository
    unlock_level(repository.get_repository(), STUDENT_DIKA, 2)
    return client


# ========== Health ==========

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "2.5"
    # Integrasi #3 (D.3): health bermakna — laporkan dependency.
    assert data["repository"] == "in-memory"
    assert data["framework_schema_version"] == "1.0.0"
    assert "whisper_loaded" in data
    assert data["supabase_configured"] is False


def test_ready_ok_in_demo_mode(client):
    """Integrasi #5 (C.4): /ready 200 saat siap (demo mode → model tak wajib)."""
    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["demo_mode"] is True


def test_request_id_header_present(client):
    """Integrasi #5 (D5): setiap respons membawa X-Request-ID."""
    resp = client.get("/health")
    assert resp.headers.get("X-Request-ID")


def test_request_id_echoed_when_provided(client):
    resp = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers.get("X-Request-ID") == "abc123"


def test_request_id_sanitized_when_malicious(client):
    """Integrasi #6 (E.1): X-Request-ID klien disanitasi (anti-injeksi log)."""
    resp = client.get(
        "/health",
        headers={"X-Request-ID": "abc\nINJECT\t<script>"},
    )
    rid = resp.headers.get("X-Request-ID")
    assert rid, "harus ada X-Request-ID pada respons"
    assert "\n" not in rid and "\t" not in rid and "<" not in rid


def test_request_id_generated_when_empty(client):
    """Header kosong/whitespace → di-generate (bukan string kosong)."""
    resp = client.get("/health", headers={"X-Request-ID": "   "})
    rid = resp.headers.get("X-Request-ID")
    assert rid and rid.strip() == rid and len(rid) > 0


# ========== Students ==========

def test_list_students(client):
    resp = client.get("/students")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_create_student(client):
    resp = client.post("/students", json={"name": "Test Anak", "grade": 2, "class_id": CLASS_2A})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Anak"


def test_create_student_empty_name_422(client):
    resp = client.post("/students", json={"name": "", "grade": 2, "class_id": CLASS_2A})
    assert resp.status_code == 422


def test_create_student_invalid_grade_422(client):
    resp = client.post("/students", json={"name": "X", "grade": 5, "class_id": CLASS_2A})
    assert resp.status_code == 422


def test_get_student_404(client):
    resp = client.get("/students/nonexistent")
    assert resp.status_code == 404


def test_student_assessments_history_ordered(client):
    """Riwayat terurut waktu."""
    resp = client.get(f"/students/{STUDENT_DIKA}/assessments")
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
    resp = client.get(f"/readings/{READING_1}")
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
    resp = client.get(f"/classes/{CLASS_2A}/students")
    assert resp.status_code == 200
    for s in resp.json():
        assert s["class_id"] == CLASS_2A


def test_get_class_404(client):
    resp = client.get("/classes/nonexistent")
    assert resp.status_code == 404


# ========== Dashboard ==========

def test_dashboard_class(client):
    resp = client.get(f"/dashboard/class/{CLASS_2A}")
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

def test_create_assessment(client_l2):
    resp = client_l2.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    assert resp.status_code == 200
    assert "id" in resp.json()


def test_create_assessment_invalid_student_404(client):
    """404 menang atas 409: siswa tak dikenal diperiksa sebelum gerbang level."""
    resp = client.post("/assessments", json={"student_id": "nonexistent", "reading_id": READING_4})
    assert resp.status_code == 404


def test_create_assessment_invalid_reading_404(client):
    """404 menang atas 409: bacaan tak dikenal diperiksa sebelum gerbang level."""
    resp = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": "nonexistent"})
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
    resp = client.get(f"/assessments?student_id={STUDENT_DIKA}")
    assert resp.status_code == 200
    for a in resp.json():
        assert a["student_id"] == STUDENT_DIKA


def test_comprehension_before_audio_422(client_l2):
    """Comprehension sebelum audio diproses → 422."""
    create = client_l2.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    resp = client_l2.post(f"/assessments/{aid}/comprehension", json={"answers": {}})
    assert resp.status_code == 422


# ========== F (integrasi #3): ambang lintas-sisi ==========

def test_config_thresholds_matches_backend_constants(client):
    """Ambau dari endpoint == konstanta backend (satu sumber, aturan #9)."""
    from rules.adaptive_rules import ACCURACY_HIGH, ACCURACY_LOW, COMPREHENSION_MIN
    resp = client.get("/config/thresholds")
    assert resp.status_code == 200
    data = resp.json()
    assert data["accuracy_low"] == ACCURACY_LOW == 90.0
    assert data["accuracy_high"] == ACCURACY_HIGH == 95.0
    assert data["comprehension_min"] == COMPREHENSION_MIN == 80.0


def test_frontend_thresholds_match_backend():
    """aturan #9: nilai di frontend lib/tokens.ts harus sama dengan backend.

    Mencegah duplikasi nilai yang lepas sinkron (batas produksi lintas-sisi).
    """
    import re
    from pathlib import Path

    from rules.adaptive_rules import ACCURACY_HIGH, ACCURACY_LOW, COMPREHENSION_MIN

    tokens = Path(__file__).resolve().parents[2] / "frontend" / "lib" / "tokens.ts"
    if not tokens.exists():
        import pytest
        pytest.skip("frontend/lib/tokens.ts tidak tersedia")
    text = tokens.read_text()

    m = re.search(r"accuracy:\s*\{\s*low:\s*(\d+),\s*high:\s*(\d+)\s*\}", text)
    assert m, "pola THRESHOLDS.accuracy tidak ditemukan di tokens.ts"
    assert float(m.group(1)) == ACCURACY_LOW
    assert float(m.group(2)) == ACCURACY_HIGH

    m2 = re.search(r"comprehension:\s*(\d+)", text)
    assert m2, "pola THRESHOLDS.comprehension tidak ditemukan di tokens.ts"
    assert float(m2.group(1)) == COMPREHENSION_MIN
