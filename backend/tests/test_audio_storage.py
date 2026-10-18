"""Test penyimpanan audio Supabase Storage (integrasi #4, D2 / B.4).

Memakai klien PALSU (tanpa jaringan): menguji path objek, kontrak error-safe
(gagal unggah tidak melempar → mengembalikan None), dan pembentukan signed URL.
"""
from __future__ import annotations

from services import audio_storage


class _FakeBucket:
    def __init__(self, store, fail=False):
        self._store = store
        self._fail = fail

    def upload(self, path, data, opts):
        if self._fail:
            raise RuntimeError("storage down")
        self._store[path] = (data, opts)
        return {"path": path}

    def create_signed_url(self, path, ttl):
        if path not in self._store:
            raise RuntimeError("not found")
        return {"signedURL": f"https://x/{path}?token=abc"}

    def create_signed_upload_url(self, path, options=None):
        if self._fail:
            raise RuntimeError("storage down")
        return {
            "signed_url": f"https://x/upload/{path}?token=tk",
            "signedUrl": f"https://x/upload/{path}?token=tk",
            "token": "tk",
            "path": path,
        }

    def download(self, path):
        if self._fail or path not in self._store:
            raise RuntimeError("not found")
        return self._store[path][0]


class _FakeStorage:
    def __init__(self, bucket):
        self._bucket = bucket

    def from_(self, name):
        assert name == audio_storage.BUCKET
        return self._bucket


class _FakeClient:
    def __init__(self, fail=False):
        self.store: dict = {}
        self.storage = _FakeStorage(_FakeBucket(self.store, fail=fail))


def test_store_audio_path_and_content_type():
    client = _FakeClient()
    path = audio_storage.store_audio(client, "teacher-1", "assess-1", b"RIFF...", "wav")
    assert path == "teacher-1/assess-1/normalized.wav"
    data, opts = client.store[path]
    assert data == b"RIFF..."
    assert opts["content-type"] == "audio/wav"


def test_store_audio_mp3_content_type():
    client = _FakeClient()
    path = audio_storage.store_audio(client, "t", "a", b"ID3", "mp3", kind="original")
    assert path == "t/a/original.mp3"
    assert client.store[path][1]["content-type"] == "audio/mpeg"


def test_store_audio_failure_returns_none():
    client = _FakeClient(fail=True)
    assert audio_storage.store_audio(client, "t", "a", b"x", "wav") is None


def test_signed_url_after_store():
    client = _FakeClient()
    path = audio_storage.store_audio(client, "t", "a", b"x", "wav")
    url = audio_storage.signed_url(client, path)
    assert url is not None and path in url


def test_signed_url_empty_path_returns_none():
    client = _FakeClient()
    assert audio_storage.signed_url(client, "") is None


# ── Signed UPLOAD URL + download (integrasi #6, Opsi A) ──

def test_create_signed_upload_url_ok():
    client = _FakeClient()
    res = audio_storage.create_signed_upload_url(client, "t/a/normalized.wav")
    assert res is not None
    assert res["path"] == "t/a/normalized.wav"
    assert res["signed_url"].startswith("https://")
    assert res["token"] == "tk"


def test_create_signed_upload_url_failure_returns_none():
    client = _FakeClient(fail=True)
    assert audio_storage.create_signed_upload_url(client, "t/a/x.wav") is None


def test_create_signed_upload_url_empty_path_returns_none():
    client = _FakeClient()
    assert audio_storage.create_signed_upload_url(client, "") is None


def test_download_returns_bytes_after_store():
    client = _FakeClient()
    path = audio_storage.store_audio(client, "t", "a", b"RIFFdata", "wav")
    assert audio_storage.download(client, path) == b"RIFFdata"


def test_download_missing_returns_none():
    client = _FakeClient()
    assert audio_storage.download(client, "t/a/nope.wav") is None


def test_download_empty_path_returns_none():
    client = _FakeClient()
    assert audio_storage.download(client, "") is None
