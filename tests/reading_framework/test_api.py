"""API tests (TestClient). Menguji kontrak respons & keamanan tanpa model nyata.

Endpoint /transcribe memerlukan model; test di file ini fokus pada endpoint
yang tidak butuh model + validasi keamanan.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from reading_framework.integrations.fastapi_app import LocalJobStore, create_app


@pytest.fixture
def client(tmp_path, question_bank_path):
    app = create_app(question_bank_path=question_bank_path,
                     store=LocalJobStore(tmp_path / "jobs"))
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["schema_version"] == "1.0.0"


def test_create_job_with_valid_question(client):
    r = client.post("/jobs", data={"question_id": "indo_1-1_correct"})
    assert r.status_code == 200
    assert r.json()["status"] == "created"


def test_create_job_missing_question(client):
    r = client.post("/jobs", data={"question_id": "nope"})
    assert r.status_code == 404


def test_unknown_job_status_404(client):
    assert client.get("/jobs/does-not-exist").status_code == 404


def test_upload_rejects_bad_extension(client):
    job = client.post("/jobs", data={"question_id": "indo_1-1_correct"}).json()["job_id"]
    r = client.post(f"/jobs/{job}/audio", files={"file": ("evil.exe", b"x" * 10)})
    assert r.status_code == 400


def test_upload_rejects_empty(client):
    job = client.post("/jobs", data={"question_id": "indo_1-1_correct"}).json()["job_id"]
    r = client.post(f"/jobs/{job}/audio", files={"file": ("a.wav", b"")})
    assert r.status_code == 400


def test_upload_sanitizes_traversal_filename(client, tmp_path):
    job = client.post("/jobs", data={"question_id": "indo_1-1_correct"}).json()["job_id"]
    r = client.post(f"/jobs/{job}/audio",
                    files={"file": ("../../../../etc/passwd.wav", b"RIFF0000")})
    assert r.status_code == 200
    # tidak ada file bernama passwd di luar area job
    assert "passwd" not in r.json()["filename"] or "/" not in r.json()["filename"]


def test_transcribe_without_audio_400(client):
    job = client.post("/jobs", data={"question_id": "indo_1-1_correct"}).json()["job_id"]
    assert client.post(f"/jobs/{job}/transcribe").status_code == 400


def test_result_not_ready_conflict(client):
    job = client.post("/jobs", data={"question_id": "indo_1-1_correct"}).json()["job_id"]
    r = client.get(f"/jobs/{job}/result")
    assert r.status_code == 409


def test_transcript_unavailable_404(client):
    job = client.post("/jobs", data={"question_id": "indo_1-1_correct"}).json()["job_id"]
    assert client.get(f"/jobs/{job}/transcript").status_code == 404


def test_save_review_unknown_job_404(client):
    r = client.post("/jobs/nope/review",
                    json={"reviewer_id": "r1", "decisions": []})
    assert r.status_code == 404


def test_openapi_available(client):
    assert client.get("/openapi.json").status_code == 200
