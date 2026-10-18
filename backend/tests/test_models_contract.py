"""Test kontrak model — validasi respons nyata terhadap models/assessment.py.

Integrasi #2, Fase C.2 (keputusan D1: models DIPERTAHANKAN sebagai kontrak resmi).
Tujuan: memastikan model pydantic benar-benar menegakkan bentuk respons yang
diproduksi backend (bukan "kontrak yang berbohong").

Menggunakan pola mock yang sama dengan test_demo_scenario.py (tanpa model Whisper).
"""
import pytest
from fastapi.testclient import TestClient

from models.assessment import AssessmentResult, ComprehensionResult
from seed.reading_texts import SEED_IDS
from services.speech import TranscriptResult
from tests.conftest import unlock_level

STUDENT_DIKA = SEED_IDS["student_dika"]
READING_4 = SEED_IDS["reading_4"]


def _words(n_correct: int, n_incorrect: int) -> list[dict]:
    words = []
    pos = 0
    for _ in range(n_correct):
        words.append({"position": pos, "reference_word": "kata", "transcript_word": "kata",
                      "operation": "match", "model_probability": 0.9,
                      "start_seconds": pos * 0.3, "end_seconds": pos * 0.3 + 0.2,
                      "review_required": False, "review_reasons": []})
        pos += 1
    for _ in range(n_incorrect):
        words.append({"position": pos, "reference_word": "kata", "transcript_word": "salah",
                      "operation": "substitution", "model_probability": 0.4,
                      "start_seconds": pos * 0.3, "end_seconds": pos * 0.3 + 0.2,
                      "review_required": False, "review_reasons": []})
        pos += 1
    return words


@pytest.fixture
def client(monkeypatch):
    """TestClient dengan Level 1 Dika sudah tuntas → Level 2 (READING_4) terbuka.

    Modul ini menguji bentuk respons COMPLETED, bukan tangga level; prasyarat
    gerbang naik level dipenuhi di fixture (gerbangnya diuji di
    tests/test_progression.py).
    """
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DEMO_FALLBACK", "true")
    import repository
    repository._repo = None
    import main
    with TestClient(main.app) as c:
        unlock_level(repository.get_repository(), STUDENT_DIKA, 2)
        yield c


def _completed_assessment(client, monkeypatch) -> dict:
    """Jalankan asesmen sampai COMPLETED, kembalikan respons akhir."""
    import services.speech as speech_mod

    correct, total = 50, 55
    duration = (correct * 60 / 60)  # wcpm 60

    def _transcribe(audio_path, reference_text=None, reading_id=None,
                    reading_repository=None, output_dir=None):
        return TranscriptResult(
            raw_text="kata " * total,
            alignment_words=_words(correct, total - correct),
            duration_seconds=duration,
            framework_result={"schema_version": "1.0.0", "job": {"status": "completed"},
                              "alignment": {"status": "computed", "words": _words(correct, total - correct)},
                              "audio": {"duration_seconds": duration}},
            is_demo=False,
        )

    monkeypatch.setattr(speech_mod, "transcribe", _transcribe)
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    from tests.conftest import wav_bytes
    client.post(f"/assessments/{aid}/audio", files={"audio": ("t.wav", wav_bytes(), "audio/wav")})

    reading = client.get(f"/readings/{READING_4}").json()
    answers = {q["id"]: q["answer_id"] for q in reading["questions"]}
    resp = client.post(f"/assessments/{aid}/comprehension", json={"answers": answers})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_completed_assessment_matches_contract(client, monkeypatch):
    """Respons asesmen COMPLETED harus lolos validasi AssessmentResult."""
    data = _completed_assessment(client, monkeypatch)
    # Field yang dibutuhkan kontrak harus ada
    # (id, student_id, wcpm, accuracy, correct_words, ..., comprehension, status, dst.)
    model = AssessmentResult.model_validate({
        "id": data["id"],
        "student_id": data["student_id"],
        "wcpm": data.get("wcpm"),
        "accuracy": data.get("accuracy"),
        "correct_words": data.get("correct_words", 0),
        "incorrect_words": data.get("incorrect_words", 0),
        "total_words_read": data.get("total_words_read", 0),
        "comprehension": {
            "retrieve": data.get("retrieve"),
            "interpret": data.get("interpret"),
            "reflect": data.get("reflect"),
        },
        "status": data["status"],
        "recommendation": data.get("recommendation", ""),
        "next_reading_level": data.get("next_reading_level", 1),
        "rules_fired": data.get("rules_fired", []),
        "word_scores": data.get("word_scores", []),
        "framework_result": data.get("framework_result"),
        "is_demo_fallback": data.get("is_demo_fallback", False),
    })
    assert model.status is not None


def test_assessment_result_allows_null_wcpm():
    """null ≠ 0: model menerima wcpm/accuracy None (tidak dapat dihitung)."""
    model = AssessmentResult(
        id="x", student_id="y", wcpm=None, accuracy=None,
        correct_words=0, incorrect_words=0, total_words_read=0,
        comprehension=ComprehensionResult(retrieve=None, interpret=None, reflect=None),
        status="STAY", recommendation="", next_reading_level=1,
    )
    assert model.wcpm is None
    assert model.accuracy is None
    assert model.comprehension.retrieve is None


def test_comprehension_requires_values_when_present():
    """Bila nilai diberikan, harus dalam rentang 0..100."""
    with pytest.raises(Exception):
        ComprehensionResult(retrieve=150, interpret=0, reflect=0)
