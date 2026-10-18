"""Test endpoint audio-url (integrasi #5, D3 / B.1b) — unit, tanpa jaringan.

Menguji logika endpoint `GET /assessments/{id}/audio-url` dengan repo & storage
di-mock: pemilik dapat signed URL; audio_url null → 404; signed gagal → 502;
bukan pemilik → 404 (via repo.get_assessment → None).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DEMO_FALLBACK", "true")

    import repository
    repository._repo = None

    import main
    with TestClient(main.app) as c:
        yield c


def test_audio_url_owner_ok(client, monkeypatch):
    import api.assessments as asmt_mod
    from api.auth import _demo_teacher_id

    monkeypatch.setattr(
        asmt_mod, "_owned_assessment",
        lambda repo, aid, teacher: {"id": aid, "audio_url": "t/a/normalized.wav"},
    )
    monkeypatch.setattr(asmt_mod, "teacher_supabase_client", lambda tok: object())
    monkeypatch.setattr(
        asmt_mod.audio_storage, "signed_url",
        lambda c, p, ttl=None: "https://signed/x",
    )
    r = client.get("/assessments/AAA/audio-url")
    assert r.status_code == 200
    assert r.json()["url"] == "https://signed/x"
    assert "expires_in" in r.json()


def test_audio_url_null_is_404(client, monkeypatch):
    """audio_url null → 404 (rekaman tidak tersedia; bukan error server)."""
    import api.assessments as asmt_mod

    monkeypatch.setattr(
        asmt_mod, "_owned_assessment",
        lambda repo, aid, teacher: {"id": aid, "audio_url": None},
    )
    r = client.get("/assessments/AAA/audio-url")
    assert r.status_code == 404


def test_audio_url_signed_failure_is_502(client, monkeypatch):
    import api.assessments as asmt_mod

    monkeypatch.setattr(
        asmt_mod, "_owned_assessment",
        lambda repo, aid, teacher: {"id": aid, "audio_url": "t/a/x.wav"},
    )
    monkeypatch.setattr(asmt_mod, "teacher_supabase_client", lambda tok: object())
    monkeypatch.setattr(asmt_mod.audio_storage, "signed_url", lambda c, p, ttl=None: None)
    r = client.get("/assessments/AAA/audio-url")
    assert r.status_code == 502


def test_audio_url_no_storage_client_is_502(client, monkeypatch):
    import api.assessments as asmt_mod

    monkeypatch.setattr(
        asmt_mod, "_owned_assessment",
        lambda repo, aid, teacher: {"id": aid, "audio_url": "t/a/x.wav"},
    )
    monkeypatch.setattr(asmt_mod, "teacher_supabase_client", lambda tok: None)
    r = client.get("/assessments/AAA/audio-url")
    assert r.status_code == 502


def test_audio_url_not_owned_is_404(client, monkeypatch):
    """Bukan milik guru → 404 (via _owned_assessment raising)."""
    import api.assessments as asmt_mod
    from fastapi import HTTPException

    def _raise(repo, aid, teacher):
        raise HTTPException(status_code=404, detail="Assessment not found")

    monkeypatch.setattr(asmt_mod, "_owned_assessment", _raise)
    r = client.get("/assessments/AAA/audio-url")
    assert r.status_code == 404


# ── Upload URL (integrasi #6, Opsi A) ──

def test_upload_url_signed_ok(client, monkeypatch):
    """Pemilik → mode 'signed' + path/signed_url/token."""
    import api.assessments as asmt_mod

    monkeypatch.setattr(asmt_mod, "_owned_assessment", lambda repo, aid, t: {"id": aid})
    monkeypatch.setattr(asmt_mod, "teacher_supabase_client", lambda tok: object())
    monkeypatch.setattr(
        asmt_mod.audio_storage, "create_signed_upload_url",
        lambda c, p, **kw: {"path": p, "signed_url": "https://signed/put", "token": "tk"},
    )
    r = client.post("/assessments/AAA/audio/upload-url")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "signed"
    assert body["signed_url"] == "https://signed/put"
    assert body["token"] == "tk"
    assert body["path"].endswith("/AAA/normalized.wav")


def test_upload_url_multipart_when_no_storage(client, monkeypatch):
    """Storage tak dikonfigurasi → mode 'multipart' (fallback)."""
    import api.assessments as asmt_mod

    monkeypatch.setattr(asmt_mod, "_owned_assessment", lambda repo, aid, t: {"id": aid})
    monkeypatch.setattr(asmt_mod, "teacher_supabase_client", lambda tok: None)
    r = client.post("/assessments/AAA/audio/upload-url")
    assert r.status_code == 200
    assert r.json()["mode"] == "multipart"


def test_upload_url_signed_failure_is_502(client, monkeypatch):
    import api.assessments as asmt_mod

    monkeypatch.setattr(asmt_mod, "_owned_assessment", lambda repo, aid, t: {"id": aid})
    monkeypatch.setattr(asmt_mod, "teacher_supabase_client", lambda tok: object())
    monkeypatch.setattr(
        asmt_mod.audio_storage, "create_signed_upload_url", lambda c, p, **kw: None
    )
    r = client.post("/assessments/AAA/audio/upload-url")
    assert r.status_code == 502


def test_upload_url_not_owned_is_404(client, monkeypatch):
    import api.assessments as asmt_mod
    from fastapi import HTTPException

    def _raise(repo, aid, t):
        raise HTTPException(status_code=404, detail="Assessment not found")

    monkeypatch.setattr(asmt_mod, "_owned_assessment", _raise)
    r = client.post("/assessments/AAA/audio/upload-url")
    assert r.status_code == 404


# ── Validasi path (anti IDOR / traversal) ──

def test_validate_audio_path_rejects_traversal():
    import api.assessments as asmt_mod
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e:
        asmt_mod._validate_audio_path("t/a/../../etc/passwd", "t", "a")
    assert e.value.status_code == 422


def test_validate_audio_path_rejects_wrong_owner():
    import api.assessments as asmt_mod
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e:
        asmt_mod._validate_audio_path("other/a/x.wav", "t", "a")
    assert e.value.status_code == 403


def test_validate_audio_path_accepts_own():
    import api.assessments as asmt_mod

    asmt_mod._validate_audio_path("t/a/x.wav", "t", "a")  # tidak raise
