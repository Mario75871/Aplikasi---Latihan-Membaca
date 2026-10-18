"""Test gerbang naik level (services/progression.py + POST /assessments).

Aturan yang diuji:
- Tangga mulai Level 1 untuk SEMUA siswa (tidak melihat tingkat kelas).
- Level berikutnya terbuka hanya setelah SELURUH bacaan pada level berjalan
  tuntas (``session_state == "COMPLETED"``).
- Penegaknya backend: bacaan di atas level terbuka → 409 dengan pesan yang
  menyebut sisa bacaan yang belum tuntas.
"""
import pytest
from fastapi.testclient import TestClient

from seed.reading_texts import SEED_IDS
from services.progression import (
    completed_reading_ids,
    locked_reason,
    unlocked_level,
)
from services.speech import TranscriptResult
from tests.conftest import unlock_level, wav_bytes

STUDENT_DIKA = SEED_IDS["student_dika"]


# ========== Unit: tangga level ==========

#: Katalog tiruan: 2 bacaan per level, id pendek supaya asersi mudah dibaca.
CATALOG = [
    {"id": "r1", "title": "Bacaan Satu", "complexity": 1},
    {"id": "r2", "title": "Bacaan Dua", "complexity": 1},
    {"id": "r3", "title": "Bacaan Tiga", "complexity": 2},
    {"id": "r4", "title": "Bacaan Empat", "complexity": 2},
    {"id": "r5", "title": "Bacaan Lima", "complexity": 3},
    {"id": "r6", "title": "Bacaan Enam", "complexity": 3},
]


class _StubRepo:
    """Repository mini: cukup untuk `completed_reading_ids`."""

    def __init__(self, assessments: list[dict]):
        self._assessments = assessments

    def list_student_assessments(self, student_id: str) -> list[dict]:
        return [a for a in self._assessments if a["student_id"] == student_id]


def _completed(*reading_ids: str, student_id: str = "s1") -> list[dict]:
    return [
        {"student_id": student_id, "reading_id": rid, "session_state": "COMPLETED"}
        for rid in reading_ids
    ]


def test_unlocked_level_starts_at_one():
    """Siswa tanpa riwayat mulai di Level 1 — walau katalognya punya Level 3."""
    assert unlocked_level(CATALOG, set()) == 1


def test_unlocked_level_after_level1_complete():
    assert unlocked_level(CATALOG, {"r1", "r2"}) == 2


def test_unlocked_level_after_level1_and_2_complete():
    assert unlocked_level(CATALOG, {"r1", "r2", "r3", "r4"}) == 3


def test_unlocked_level_partial_level_stays():
    """Sebagian level tuntas → tetap di level itu (bukan naik)."""
    assert unlocked_level(CATALOG, {"r1"}) == 1
    assert unlocked_level(CATALOG, {"r1", "r2", "r3"}) == 2


def test_unlocked_level_caps_at_highest_level():
    """Semua level tuntas → tetap di level tertinggi yang dikenal."""
    assert unlocked_level(CATALOG, {"r1", "r2", "r3", "r4", "r5", "r6"}) == 3


def test_completed_reading_ids_only_counts_completed():
    """Sesi yang baru dibuka (DRAFT/COMPREHENSION) bukan "tuntas"."""
    repo = _StubRepo([
        {"student_id": "s1", "reading_id": "r1", "session_state": "COMPLETED"},
        {"student_id": "s1", "reading_id": "r2", "session_state": "COMPREHENSION"},
        {"student_id": "s1", "reading_id": "r3", "session_state": "DRAFT"},
        {"student_id": "s2", "reading_id": "r4", "session_state": "COMPLETED"},
    ])
    assert completed_reading_ids(repo, "s1") == {"r1"}


def test_locked_reason_none_for_unlocked_level():
    """Bacaan pada level terbuka (dan di bawahnya) tidak terkunci."""
    assert locked_reason(CATALOG, set(), CATALOG[0]) is None          # Level 1
    assert locked_reason(CATALOG, {"r1", "r2"}, CATALOG[2]) is None   # Level 2
    assert locked_reason(CATALOG, {"r1", "r2", "r3", "r4"}, CATALOG[4]) is None


def test_locked_reason_mentions_pending_readings():
    """Pesan menyebut level berjalan + judul bacaan yang belum tuntas."""
    reason = locked_reason(CATALOG, {"r1"}, CATALOG[2], student_name="Dika")
    assert reason is not None
    assert "Dika" in reason
    assert "Level 1" in reason
    assert "«Bacaan Dua»" in reason       # sisa Level 1 yang belum tuntas
    assert "«Bacaan Satu»" not in reason  # sudah tuntas → tidak disebut
    assert "Level 2" in reason


def test_locked_reason_lists_all_pending_when_none_completed():
    reason = locked_reason(CATALOG, set(), CATALOG[4])
    assert reason is not None
    assert "2 bacaan" in reason
    assert "«Bacaan Satu»" in reason and "«Bacaan Dua»" in reason


# ========== API: penegakan di POST /assessments ==========

@pytest.fixture
def client(monkeypatch):
    """TestClient dengan repo in-memory fresh (tanpa prasyarat level apa pun)."""
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DEMO_FALLBACK", "true")

    import repository
    repository._repo = None

    import main
    with TestClient(main.app) as c:
        yield c


def _post(client, reading_id: str):
    return client.post(
        "/assessments", json={"student_id": STUDENT_DIKA, "reading_id": reading_id}
    )


def test_level1_always_allowed(client):
    """Level 1 selalu boleh — siswa baru mulai dari sini."""
    resp = _post(client, SEED_IDS["reading_1"])
    assert resp.status_code == 200
    assert "id" in resp.json()


@pytest.mark.parametrize("slot", ["reading_2", "reading_3"])
def test_all_level1_readings_allowed(client, slot):
    assert _post(client, SEED_IDS[slot]).status_code == 200


@pytest.mark.parametrize("slot", ["reading_4", "reading_7"])
def test_locked_level_returns_409_with_reason(client, slot):
    """Level 2/3 terkunci selama Level 1 belum tuntas → 409 + pesan jelas."""
    resp = _post(client, SEED_IDS[slot])
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert "Level 1" in detail
    assert "Dika" in detail  # nama siswa, agar guru tahu ini siswa yang mana


def test_level2_opens_after_level1_complete(client):
    """Setelah seluruh bacaan Level 1 tuntas → Level 2 terbuka, Level 3 belum."""
    assert _post(client, SEED_IDS["reading_4"]).status_code == 409

    import repository
    unlock_level(repository.get_repository(), STUDENT_DIKA, 2)

    assert _post(client, SEED_IDS["reading_4"]).status_code == 200
    assert _post(client, SEED_IDS["reading_7"]).status_code == 409


def test_level3_opens_after_level2_complete(client):
    import repository
    unlock_level(repository.get_repository(), STUDENT_DIKA, 3)
    assert _post(client, SEED_IDS["reading_7"]).status_code == 200


def _complete_reading(client, monkeypatch, reading_id: str) -> dict:
    """Tuntaskan satu bacaan lewat pipeline NYATA (audio → pemahaman).

    Memakai jalur asli, bukan menulis status langsung, supaya tes ini benar-benar
    membuktikan bahwa "tuntas" terjadi setelah seluruh pipeline selesai.
    """
    import services.speech as speech_mod

    def _transcribe(audio_path, reference_text=None, reading_id=None,
                    reading_repository=None, output_dir=None):
        words = [
            {"position": i, "reference_word": "kata", "transcript_word": "kata",
             "operation": "match", "model_probability": 0.9,
             "start_seconds": i * 0.3, "end_seconds": i * 0.3 + 0.2,
             "review_required": False, "review_reasons": []}
            for i in range(20)
        ]
        return TranscriptResult(
            raw_text="kata " * 20,
            alignment_words=words,
            duration_seconds=20.0,
            framework_result={
                "schema_version": "1.0.0",
                "job": {"status": "completed"},
                "alignment": {"status": "computed", "words": words},
                "audio": {"duration_seconds": 20.0},
            },
            is_demo=False,
        )

    monkeypatch.setattr(speech_mod, "transcribe", _transcribe)

    created = _post(client, reading_id)
    assert created.status_code == 200, created.text
    aid = created.json()["id"]

    up = client.post(f"/assessments/{aid}/audio",
                     files={"audio": ("t.wav", wav_bytes(), "audio/wav")})
    assert up.status_code == 200, up.text
    assert up.json()["session_state"] == "COMPREHENSION"  # belum tuntas

    reading = client.get(f"/readings/{reading_id}").json()
    answers = {q["id"]: q["answer_id"] for q in reading["questions"]}
    done = client.post(f"/assessments/{aid}/comprehension", json={"answers": answers})
    assert done.status_code == 200, done.text
    assert done.json()["session_state"] == "COMPLETED"
    return done.json()


def test_ladder_end_to_end_through_real_pipeline(client, monkeypatch):
    """Menuntaskan tiga bacaan Level 1 satu per satu membuka Level 2.

    Level 2 masih terkunci setelah dua bacaan tuntas — gerbangnya menuntut
    "seluruhnya", bukan "sebagian".
    """
    assert _post(client, SEED_IDS["reading_4"]).status_code == 409

    _complete_reading(client, monkeypatch, SEED_IDS["reading_1"])
    _complete_reading(client, monkeypatch, SEED_IDS["reading_2"])
    assert _post(client, SEED_IDS["reading_4"]).status_code == 409  # 2 dari 3

    _complete_reading(client, monkeypatch, SEED_IDS["reading_3"])
    assert _post(client, SEED_IDS["reading_4"]).status_code == 200
    assert _post(client, SEED_IDS["reading_7"]).status_code == 409  # Level 3 belum
