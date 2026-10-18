"""Penjaga bentuk UUID di SupabaseRepository (regresi 500 → 404).

Kenapa tes ini ada: kolom ``id`` di Supabase bertipe ``uuid``. Sebelum penjaganya,
``get_student("nonexistent")`` meneruskan string itu ke PostgREST, Postgres menolak
("invalid input syntax for type uuid"), dan endpoint menjawab **500** — padahal artinya
"tidak ditemukan" (**404**). ``tests/test_api.py`` tidak menangkapnya karena menguji
repo in-memory (`DEMO_FALLBACK`) yang tidak punya tipe kolom.

TestClient di sini adalah **stub** yang menirukan sifat penting Postgres itu: menolak
nilai non-UUID pada kolom uuid. Jadi tes ini gagal pada kode lama tanpa perlu database.
"""
import uuid

import pytest

from repository import SupabaseRepository, _is_uuid

#: Kolom bertipe uuid di skema — stub menolak nilai non-UUID di sini, seperti Postgres.
UUID_COLUMNS = {"id", "student_id", "reading_id", "assessment_id", "class_id", "teacher_id"}


class _StubQuery:
    """Kueri postgrest tiruan: hasil selalu kosong, tapi tipe kolom ditegakkan."""

    def __init__(self) -> None:
        self.filters: list[tuple[str, object]] = []

    def select(self, *a, **k):
        return self

    def eq(self, column: str, value: object):
        if column in UUID_COLUMNS and not _is_uuid(value):
            raise RuntimeError(f'invalid input syntax for type uuid: "{value}"')
        self.filters.append((column, value))
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        return type("Resp", (), {"data": []})()


class _StubClient:
    def __init__(self) -> None:
        self.queries: list[_StubQuery] = []

    def table(self, name: str) -> _StubQuery:
        q = _StubQuery()
        self.queries.append(q)
        return q


@pytest.fixture
def repo():
    """SupabaseRepository dengan klien tiruan (tanpa jaringan, tanpa Supabase)."""
    r = SupabaseRepository.__new__(SupabaseRepository)   # lewati __init__ (tak ada jaringan)
    r.client = _StubClient()
    return r


# ========== Unit: bentuk UUID ==========

def test_is_uuid_accepts_uuid_and_bare_hex():
    assert _is_uuid(str(uuid.uuid4()))
    assert _is_uuid(uuid.uuid4())                   # objek UUID, bukan hanya string
    assert _is_uuid("7cc03b4a091779173941d6e8bd345d52")   # 32 heks tanpa tanda hubung


@pytest.mark.parametrize("value", ["", "nonexistent", "reading_1", "  ", "123", None, 42])
def test_is_uuid_rejects_impossible_shapes(value):
    assert _is_uuid(value) is False


# ========== Penjaga: bentuk mustahil → "tidak ditemukan", bukan galat ==========

def test_get_student_non_uuid_returns_none(repo):
    assert repo.get_student("nonexistent") is None


def test_get_reading_non_uuid_returns_none(repo):
    assert repo.get_reading("nonexistent") is None


def test_get_assessment_non_uuid_returns_none(repo):
    assert repo.get_assessment("nonexistent") is None


def test_get_class_non_uuid_returns_none(repo):
    assert repo.get_class("nonexistent") is None


def test_list_student_assessments_non_uuid_returns_empty(repo):
    assert repo.list_student_assessments("nonexistent") == []


def test_list_word_scores_non_uuid_returns_empty(repo):
    assert repo.list_word_scores("nonexistent") == []


def test_guard_does_not_reach_the_database(repo):
    """Bentuk mustahil ditolak SEBELUM kueri — bukan setelah Postgres melempar."""
    repo.get_student("nonexistent")
    repo.get_reading("nonexistent")
    repo.get_assessment("nonexistent")
    repo.get_class("nonexistent")
    repo.list_student_assessments("nonexistent")
    repo.list_word_scores("nonexistent")
    assert repo.client.queries == []


# ========== Kontrol: id sah tetap lewat seperti biasa ==========

def test_valid_uuid_still_queried(repo):
    """UUID sah (walau tidak ada barisnya) harus tetap dikirim ke basis data."""
    assert repo.get_student(str(uuid.uuid4())) is None
    assert repo.get_assessment(str(uuid.uuid4())) is None
    assert len(repo.client.queries) == 2
    assert repo.client.queries[0].filters[0][0] == "id"
