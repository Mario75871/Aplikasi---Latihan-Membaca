"""Test seed loader — bentuk baris sesuai skema kanonis (tanpa Supabase nyata).

Memverifikasi bahwa loader menghasilkan baris dengan nama kolom yang benar dan
idempotent secara struktur (upsert + delete-then-insert), memakai client tiruan.
"""
import pytest

from seed import load_supabase


class FakeQuery:
    """Query tiruan: mencatat operasi, dapat dirantai (.eq/.order)."""

    def __init__(self, log, table, op):
        self.log = log
        self.table = table
        self.op = op
        self.payload = None
        self.rows = []

    def upsert(self, payload, on_conflict=None):
        self.op = "upsert"
        self.payload = payload
        return self

    def insert(self, rows):
        self.op = "insert"
        self.rows = rows
        return self

    def delete(self):
        self.op = "delete"
        return self

    def select(self, *a, **k):
        self.op = "select"
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        self.log.append((self.table, self.op, self.payload if self.payload else self.rows))
        return type("Resp", (), {"data": []})()


class FakeClient:
    def __init__(self):
        self.log = []

    def table(self, name):
        return FakeQuery(self.log, name, None)


def test_reading_row_has_schema_columns():
    from seed.reading_texts import READING_TEXTS
    row = load_supabase._reading_row(READING_TEXTS[0])
    expected = {"id", "title", "content", "grade", "complexity", "book_level",
                "word_count", "theme", "proper_nouns", "version"}
    assert expected.issubset(row.keys())
    assert row["word_count"] == len(READING_TEXTS[0]["content"].split())


def test_question_rows_map_columns():
    from seed.reading_texts import READING_TEXTS
    rows = load_supabase._question_rows(READING_TEXTS[0])
    assert rows, "reading pertama harus punya pertanyaan"
    for r in rows:
        assert {"reading_id", "competency", "prompt", "options", "answer_id", "position"} <= r.keys()
    # position menaik untuk urutan stabil
    assert [r["position"] for r in rows] == list(range(len(rows)))


def test_load_readings_upserts_and_reshuffles_questions():
    client = FakeClient()
    n = load_supabase.load_readings(client)
    from seed.reading_texts import READING_TEXTS
    assert n == len(READING_TEXTS)
    # setiap teks: upsert reading_texts, delete lalu insert reading_questions
    upserts = [p for t, op, p in client.log if t == "reading_texts" and op == "upsert"]
    assert len(upserts) == len(READING_TEXTS)
    ops = {op for t, op, _ in client.log if t == "reading_questions"}
    assert "delete" in ops and "insert" in ops


def test_load_classes_assigns_teacher_id():
    """Integrasi #3 (D3): kelas seed punya teacher_id (guru demo)."""
    client = FakeClient()
    n = load_supabase.load_classes(client)
    assert n == len(load_supabase.SEED_CLASSES)
    for table, op, payload in client.log:
        assert table == "classes" and op == "upsert"
        assert payload["teacher_id"]  # terisi, bukan NULL


def test_load_students_upserts():
    client = FakeClient()
    n = load_supabase.load_students(client)
    assert n == len(load_supabase.SEED_STUDENTS)
    for table, op, payload in client.log:
        assert table == "students" and op == "upsert"
        assert {"id", "name", "grade", "class_id"} <= payload.keys()


def test_client_requires_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    with pytest.raises(RuntimeError):
        load_supabase._client()
