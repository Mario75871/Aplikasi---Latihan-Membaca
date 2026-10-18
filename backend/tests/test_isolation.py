"""Test isolasi data per-guru (integrasi #3, Fase A.5).

Membuktikan bahwa guru A tidak dapat melihat/mengakses data guru B, baik di
lapisan repository (filter `teacher_id`) maupun di endpoint (scoping via JWT).

Karena mode demo memakai satu guru (token lokal), isolasi diuji dengan dua
`teacher_id` berbeda langsung pada repository + endpoint dengan identitas yang
disuntikkan.
"""
import pytest
from fastapi.testclient import TestClient

from repository import InMemoryRepository
from seed.reading_texts import SEED_IDS

TEACHER_A = "00000000-0000-0000-0000-000000000401"
TEACHER_B = "00000000-0000-0000-0000-000000000402"


@pytest.fixture
def repo():
    return InMemoryRepository()


# ========== Repository level ==========

def test_list_classes_scoped_by_teacher(repo):
    ca = repo.create_class("Kelas A", 2, teacher_id=TEACHER_A)
    cb = repo.create_class("Kelas B", 2, teacher_id=TEACHER_B)
    assert {c["id"] for c in repo.list_classes(teacher_id=TEACHER_A)} == {ca["id"]}
    assert {c["id"] for c in repo.list_classes(teacher_id=TEACHER_B)} == {cb["id"]}


def test_list_students_scoped_by_teacher(repo):
    ca = repo.create_class("Kelas A", 2, teacher_id=TEACHER_A)
    cb = repo.create_class("Kelas B", 2, teacher_id=TEACHER_B)
    sa = repo.create_student("Anak A", 2, ca["id"])
    sb = repo.create_student("Anak B", 2, cb["id"])
    assert {s["id"] for s in repo.list_students(teacher_id=TEACHER_A)} == {sa["id"]}
    assert {s["id"] for s in repo.list_students(teacher_id=TEACHER_B)} == {sb["id"]}


def test_create_student_denormalizes_teacher_id(repo):
    """D3: siswa mewarisi teacher_id dari kelas."""
    ca = repo.create_class("Kelas A", 2, teacher_id=TEACHER_A)
    s = repo.create_student("Anak A", 2, ca["id"])
    assert s["teacher_id"] == TEACHER_A


def test_assessment_denormalizes_teacher_id(repo):
    """D3: asesmen mewarisi teacher_id dari siswa."""
    ca = repo.create_class("Kelas A", 2, teacher_id=TEACHER_A)
    s = repo.create_student("Anak A", 2, ca["id"])
    a = repo.create_assessment(s["id"], SEED_IDS["reading_4"])
    assert a["teacher_id"] == TEACHER_A


def test_list_all_assessments_scoped(repo):
    ca = repo.create_class("Kelas A", 2, teacher_id=TEACHER_A)
    cb = repo.create_class("Kelas B", 2, teacher_id=TEACHER_B)
    sa = repo.create_student("Anak A", 2, ca["id"])
    sb = repo.create_student("Anak B", 2, cb["id"])
    aa = repo.create_assessment(sa["id"], SEED_IDS["reading_4"])
    repo.create_assessment(sb["id"], SEED_IDS["reading_4"])
    ids_a = {a["id"] for a in repo.list_all_assessments(teacher_id=TEACHER_A)}
    assert ids_a == {aa["id"]}


def test_create_assessment_status_is_none_not_pending(repo):
    """D.1: status awal None (bukan "PENDING" yang melanggar check constraint)."""
    ca = repo.create_class("Kelas A", 2, teacher_id=TEACHER_A)
    s = repo.create_student("Anak A", 2, ca["id"])
    a = repo.create_assessment(s["id"], SEED_IDS["reading_4"])
    assert a["status"] is None


# ========== Endpoint level (identitas disuntikkan) ==========

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("DEMO_FALLBACK", "true")
    import repository
    repository._repo = None
    repository._repo = InMemoryRepository()
    # Isi data dua guru.
    ca = repository._repo.create_class("Kelas A", 2, teacher_id=TEACHER_A)
    cb = repository._repo.create_class("Kelas B", 2, teacher_id=TEACHER_B)
    repository._repo.create_student("Anak A", 2, ca["id"])
    repository._repo.create_student("Anak B", 2, cb["id"])

    import api.auth as auth_mod

    # Patch verify_token → identitas guru A/B per header.
    def fake_verify(authorization):
        if authorization and authorization.endswith("B"):
            return {"username": "guruB", "user_id": TEACHER_B}
        return {"username": "guruA", "user_id": TEACHER_A}

    monkeypatch.setattr(auth_mod, "verify_token", fake_verify)
    import main
    with TestClient(main.app) as c:
        yield c


def _hdr(which: str) -> dict:
    return {"Authorization": f"Bearer {which}"}


def test_endpoint_classes_isolated(client):
    a = client.get("/classes", headers=_hdr("A")).json()
    b = client.get("/classes", headers=_hdr("B")).json()
    assert {c["name"] for c in a} == {"Kelas A"}
    assert {c["name"] for c in b} == {"Kelas B"}


def test_endpoint_students_isolated(client):
    a = client.get("/students", headers=_hdr("A")).json()
    b = client.get("/students", headers=_hdr("B")).json()
    assert {s["name"] for s in a} == {"Anak A"}
    assert {s["name"] for s in b} == {"Anak B"}


def test_endpoint_cross_teacher_class_404(client):
    """Guru B tidak bisa membaca kelas guru A."""
    a_classes = client.get("/classes", headers=_hdr("A")).json()
    class_a_id = a_classes[0]["id"]
    resp = client.get(f"/classes/{class_a_id}", headers=_hdr("B"))
    assert resp.status_code == 404


def test_endpoint_cross_teacher_student_404(client):
    a_students = client.get("/students", headers=_hdr("A")).json()
    student_a_id = a_students[0]["id"]
    resp = client.get(f"/students/{student_a_id}", headers=_hdr("B"))
    assert resp.status_code == 404


def test_endpoint_list_assessments_scoped(client):
    """Guru B hanya melihat asesmen miliknya (tidak ada jalur 'semua').

    Memakai reading_1 (Level 1) supaya gerbang naik level tidak ikut bermain —
    subjek tes ini adalah pemisahan data antar-guru.
    """
    a_students = client.get("/students", headers=_hdr("A")).json()
    client.post("/assessments", headers=_hdr("A"),
                json={"student_id": a_students[0]["id"], "reading_id": SEED_IDS["reading_1"]})
    b_list = client.get("/assessments", headers=_hdr("B")).json()
    assert b_list == []  # guru B tidak melihat asesmen guru A
    a_list = client.get("/assessments", headers=_hdr("A")).json()
    assert len(a_list) == 1
