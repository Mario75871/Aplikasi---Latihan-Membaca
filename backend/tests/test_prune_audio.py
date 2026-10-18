"""Test prune_audio (retensi) — unit, tanpa jaringan (integrasi #5, D2 / B.2).

Menguji: dry-run tak mengubah apa pun; apply menghapus objek > N bulan + null-kan
referensi + log PURGED; gagal hapus → retry, referensi DIPERTAHANKAN, log FAILED;
idempotent saat dijalankan ulang.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from scripts import prune_audio


# ── Fake klien Supabase (tabel + storage) ──

class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeStorageBucket:
    def __init__(self, store, fail_times=0):
        self._store = store
        self._fail_times = fail_times
        self.removed: list[str] = []
        self.attempts = 0

    def remove(self, paths):
        self.attempts += 1
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("storage down")
        for p in paths:
            self._store.pop(p, None)
            self.removed.append(p)
        return {"status": "ok"}


class _FakeStorage:
    def __init__(self, bucket):
        self._bucket = bucket

    def from_(self, name):
        return self._bucket


class _Query:
    """Rantai query minimal meniru postgrest (select/eq/update/insert/execute)."""

    def __init__(self, fake, table):
        self._fake = fake
        self._table = table
        self._op = "select"
        self._not_null: str | None = None
        self._eq: tuple | None = None
        self._payload = None

    @property
    def not_(self):
        return self

    def is_(self, col, val):
        if val == "null":
            self._not_null = None  # diabaikan; not_.is_ = filter not null
        return self

    def select(self, cols):
        self._op = "select"
        return self

    def eq(self, col, val):
        self._eq = (col, val)
        return self

    def update(self, data):
        self._op = "update"
        self._payload = data
        return self

    def insert(self, data):
        self._op = "insert"
        self._payload = data
        return self

    def execute(self):
        rows = self._fake.tables.setdefault(self._table, [])

        if self._op == "select":
            out = [dict(r) for r in rows if r.get("audio_url")]
            return _FakeResult(out)

        if self._op == "update":
            col, val = self._eq
            for r in rows:
                if r.get(col) == val:
                    r.update(self._payload)
            return _FakeResult([])

        if self._op == "insert":
            rows.append(dict(self._payload))
            return _FakeResult([self._payload])

        return _FakeResult([])


class _FakeAdmin:
    def __init__(self, tables=None, storage_fail_times=0):
        self.tables = tables or {}
        self._store: dict = {}
        self._bucket = _FakeStorageBucket(self._store, fail_times=storage_fail_times)
        self.storage = _FakeStorage(self._bucket)

    def table(self, name):
        return _Query(self, name)

    # Kemudahan untuk assertion
    @property
    def removed(self):
        return self._bucket.removed


def _old_row(aid, path, months_ago=13):
    ts = datetime.now(timezone.utc) - timedelta(days=30 * months_ago)
    return {
        "id": aid, "audio_url": path,
        "completed_at": ts.isoformat(), "created_at": ts.isoformat(),
    }


def _recent_row(aid, path, months_ago=1):
    ts = datetime.now(timezone.utc) - timedelta(days=30 * months_ago)
    return {
        "id": aid, "audio_url": path,
        "completed_at": ts.isoformat(), "created_at": ts.isoformat(),
    }


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Hindari tidur nyata pada retry backoff."""
    monkeypatch.setattr(prune_audio.time, "sleep", lambda *_: None)


# ── Test ──

def test_dry_run_touches_nothing(monkeypatch):
    monkeypatch.setenv("AUDIO_RETENTION_MONTHS", "12")
    admin = _FakeAdmin({"assessments": [_old_row("a1", "t/a1/normalized.wav")]})
    result = prune_audio.run(admin=admin, apply=False)
    assert admin.removed == []
    assert admin.tables["assessments"][0]["audio_url"] == "t/a1/normalized.wav"
    assert "audio_purge_log" not in admin.tables or admin.tables["audio_purge_log"] == []
    assert result["purged"] == 1  # rencana, bukan eksekusi
    assert result["failed"] == 0


def test_apply_removes_and_nulls_and_logs(monkeypatch):
    monkeypatch.setenv("AUDIO_RETENTION_MONTHS", "12")
    admin = _FakeAdmin({"assessments": [_old_row("a1", "t/a1/normalized.wav")]})
    result = prune_audio.run(admin=admin, apply=True)
    assert admin.removed == ["t/a1/normalized.wav"]
    assert admin.tables["assessments"][0]["audio_url"] is None
    assert admin.tables["audio_purge_log"][-1]["status"] == "PURGED"
    assert result["purged"] == 1


def test_failed_delete_keeps_reference_and_logs_failed(monkeypatch):
    monkeypatch.setenv("AUDIO_RETENTION_MONTHS", "12")
    admin = _FakeAdmin(
        {"assessments": [_old_row("a1", "t/a1/normalized.wav")]},
        storage_fail_times=99,  # selalu gagal
    )
    result = prune_audio.run(admin=admin, apply=True)
    # referensi TIDAK dinull-kan (anti objek yatim)
    assert admin.tables["assessments"][0]["audio_url"] == "t/a1/normalized.wav"
    assert admin.tables["audio_purge_log"][-1]["status"] == "FAILED"
    assert result["failed"] == 1
    assert admin._bucket.attempts == len(prune_audio.RETRY_BACKOFF_SEC)  # retry 3×


def test_retry_then_success(monkeypatch):
    monkeypatch.setenv("AUDIO_RETENTION_MONTHS", "12")
    admin = _FakeAdmin(
        {"assessments": [_old_row("a1", "t/a1/normalized.wav")]},
        storage_fail_times=2,  # gagal 2× lalu sukses pada percobaan ke-3
    )
    result = prune_audio.run(admin=admin, apply=True)
    assert result["purged"] == 1
    assert admin.tables["assessments"][0]["audio_url"] is None
    assert admin.tables["audio_purge_log"][-1]["status"] == "PURGED"
    assert admin.tables["audio_purge_log"][-1]["attempts"] == 3


def test_recent_rows_untouched(monkeypatch):
    monkeypatch.setenv("AUDIO_RETENTION_MONTHS", "12")
    admin = _FakeAdmin({"assessments": [_recent_row("a1", "t/a1/normalized.wav")]})
    result = prune_audio.run(admin=admin, apply=True)
    assert admin.removed == []
    assert admin.tables["assessments"][0]["audio_url"] == "t/a1/normalized.wav"
    assert result["purged"] == 0


def test_idempotent_second_run(monkeypatch):
    monkeypatch.setenv("AUDIO_RETENTION_MONTHS", "12")
    admin = _FakeAdmin({"assessments": [_old_row("a1", "t/a1/normalized.wav")]})
    first = prune_audio.run(admin=admin, apply=True)
    second = prune_audio.run(admin=admin, apply=True)
    assert first["purged"] == 1
    assert second["purged"] == 0  # sudah bersih → tak ada baris ber-audio_url
    assert admin.tables["assessments"][0]["audio_url"] is None
