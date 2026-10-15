"""Test skenario demo F-08 end-to-end lewat API (3 asesmen).

Kelas 2, awal tahun, batas WCPM = 40.
A1 (WCPM 58, Acc 92%, R85/I70/Rf60) → INTERVENE (BR-02)
A2 (WCPM 68, Acc 95%, R90/I86/Rf82) → PROMOTION_CANDIDATE
A3 (WCPM 75, Acc 96%, R92/I88/Rf84) → PROMOTE

Menggunakan mock framework (transcript tiruan) untuk menghindari model Whisper.
"""
import pytest
from fastapi.testclient import TestClient

from services.speech import TranscriptResult


def make_alignment_words(n_correct: int, n_incorrect: int) -> list[dict]:
    """Buat alignment_words[] tiruan dengan n_correct kata benar dan n_incorrect salah."""
    words = []
    pos = 0
    for _ in range(n_correct):
        words.append({
            "position": pos, "reference_word": "kata", "transcript_word": "kata",
            "operation": "match", "model_probability": 0.9,
            "start_seconds": pos * 0.3, "end_seconds": pos * 0.3 + 0.2,
            "review_required": False, "review_reasons": [],
        })
        pos += 1
    for _ in range(n_incorrect):
        words.append({
            "position": pos, "reference_word": "salah", "transcript_word": "salah",
            "operation": "match", "model_probability": 0.3,
            "start_seconds": pos * 0.3, "end_seconds": pos * 0.3 + 0.2,
            "review_required": True, "review_reasons": ["low_model_probability"],
        })
        pos += 1
    return words


def mock_transcribe_for(wcpm: float, accuracy: float, duration: float = 10.0):
    """Buat fungsi transcribe tiruan yang menghasilkan WCPM & Accuracy tertentu.

    WCPM = correct / duration * 60
    Accuracy = correct / total * 100
    """
    # Pilih total = 20 kata
    total = 20
    correct = round((accuracy / 100) * total)
    incorrect = total - correct
    # Sesuaikan duration agar WCPM sesuai
    # WCPM = correct / duration * 60 → duration = correct * 60 / wcpm
    duration = (correct * 60 / wcpm) if wcpm > 0 else 10.0

    def _transcribe(audio_path, reference_text=None, reading_id=None,
                    reading_repository=None, output_dir=None):
        return TranscriptResult(
            raw_text="kata " * total,
            alignment_words=make_alignment_words(correct, incorrect),
            duration_seconds=duration,
            framework_result={
                "schema_version": "1.0.0",
                "job": {"status": "completed"},
                "alignment": {"status": "computed", "words": make_alignment_words(correct, incorrect)},
                "audio": {"duration_seconds": duration},
            },
            is_demo=False,
        )

    return _transcribe


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DEMO_FALLBACK", "true")  # skip model load, transcribe di-mock

    import repository
    repository._repo = None

    import main
    with TestClient(main.app) as c:
        yield c


def _run_assessment(client, monkeypatch, wcpm, accuracy, comprehension, reading_id="rd-004"):
    """Jalankan satu asesmen end-to-end dengan mock transcribe."""
    import services.speech as speech_mod
    monkeypatch.setattr(speech_mod, "transcribe", mock_transcribe_for(wcpm, accuracy))

    # Buat asesmen
    create = client.post("/assessments", json={"student_id": "std-001", "reading_id": reading_id})
    assert create.status_code == 200
    aid = create.json()["id"]

    # Upload audio (mock)
    files = {"audio": ("test.webm", b"fake audio bytes", "audio/webm")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    assert up.status_code == 200, up.text
    data = up.json()
    assert data["session_state"] == "COMPREHENSION"

    # Jawab comprehension
    reading = client.get(f"/readings/{reading_id}").json()
    questions = reading["questions"]
    # Bangun jawaban: sesuai comprehension yang diinginkan
    # comprehension dict: {"retrieve": bool_correct, "interpret": ..., "reflect": ...}
    answers = {}
    for q in questions:
        comp = q["competency"]
        if comprehension.get(comp, True):
            answers[q["id"]] = q["answer_id"]  # benar
        else:
            # pilih opsi salah
            wrong = [o["id"] for o in q["options"] if o["id"] != q["answer_id"]]
            answers[q["id"]] = wrong[0] if wrong else "x"

    resp = client.post(f"/assessments/{aid}/comprehension", json={"answers": answers})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_demo_scenario_end_to_end(client, monkeypatch):
    """Skenario demo 3 asesmen F-08."""
    # A1: WCPM 58, Acc 92%, R85/I70/Rf60 → INTERVENE (BR-02, Q13)
    a1 = _run_assessment(
        client, monkeypatch,
        wcpm=58, accuracy=92,
        comprehension={"retrieve": True, "interpret": False, "reflect": False},
    )
    assert a1["status"] == "INTERVENE", f"A1 status: {a1['status']}"

    # A2: WCPM 68, Acc 95%, R90/I86/Rf82 → PROMOTION_CANDIDATE
    a2 = _run_assessment(
        client, monkeypatch,
        wcpm=68, accuracy=95,
        comprehension={"retrieve": True, "interpret": True, "reflect": True},
    )
    assert a2["status"] == "PROMOTION_CANDIDATE", f"A2 status: {a2['status']}"

    # A3: WCPM 75, Acc 96%, R92/I88/Rf84 → PROMOTE (prev=CANDIDATE)
    a3 = _run_assessment(
        client, monkeypatch,
        wcpm=75, accuracy=96,
        comprehension={"retrieve": True, "interpret": True, "reflect": True},
    )
    assert a3["status"] == "PROMOTE", f"A3 status: {a3['status']}"
    assert a3["next_reading_level"] == 3  # rd-004 level 2 → naik ke level 3


def test_br07_via_api_single_drop(client, monkeypatch):
    """BR-07 lewat API: 1 penurunan → STAY + MONITOR."""
    # Asesmen pertama: WCPM 70, Acc 95
    a1 = _run_assessment(
        client, monkeypatch, wcpm=70, accuracy=95,
        comprehension={"retrieve": True, "interpret": True, "reflect": True},
    )
    # Asesmen kedua: WCPM 60 (turun), Acc 92
    a2 = _run_assessment(
        client, monkeypatch, wcpm=60, accuracy=92,
        comprehension={"retrieve": True, "interpret": True, "reflect": True},
    )
    assert a2["consecutive_drops"] == 1
    assert a2["status"] == "STAY"
    # rules_fired harus menyebut BR-07
    fired = [r["rule"] for r in a2["rules_fired"] if r["fired"]]
    assert "BR-07" in fired


def test_br07_via_api_two_drops(client, monkeypatch):
    """BR-07 lewat API: 2 penurunan berturut-turut → REVIEW/REMEDIAL."""
    # A1: WCPM 80, Acc 96
    _run_assessment(client, monkeypatch, wcpm=80, accuracy=96,
                    comprehension={"retrieve": True, "interpret": True, "reflect": True})
    # A2: WCPM 70 (turun), Acc 94
    _run_assessment(client, monkeypatch, wcpm=70, accuracy=94,
                    comprehension={"retrieve": True, "interpret": True, "reflect": True})
    # A3: WCPM 60 (turun lagi), Acc 92
    a3 = _run_assessment(client, monkeypatch, wcpm=60, accuracy=92,
                         comprehension={"retrieve": True, "interpret": True, "reflect": True})
    assert a3["consecutive_drops"] >= 2
    assert "REVIEW" in a3["recommendation"] or "REMEDIAL" in a3["recommendation"]


def test_br07_via_api_no_drop(client, monkeypatch):
    """BR-07 lewat API: tidak ada penurunan → drops 0."""
    _run_assessment(client, monkeypatch, wcpm=60, accuracy=92,
                    comprehension={"retrieve": True, "interpret": True, "reflect": True})
    a2 = _run_assessment(client, monkeypatch, wcpm=70, accuracy=94,
                         comprehension={"retrieve": True, "interpret": True, "reflect": True})
    assert a2["consecutive_drops"] == 0


def test_reading_time_zero_via_api(client, monkeypatch):
    """Reading time 0 → WCPM 0, tidak crash."""
    import services.speech as speech_mod

    def _zero_duration(audio_path, reference_text=None, reading_id=None,
                       reading_repository=None, output_dir=None):
        return TranscriptResult(
            raw_text="kata kata",
            alignment_words=make_alignment_words(2, 0),
            duration_seconds=0.0,  # durasi 0
            framework_result={"job": {"status": "completed"},
                              "alignment": {"status": "computed", "words": []}},
            is_demo=False,
        )

    monkeypatch.setattr(speech_mod, "transcribe", _zero_duration)
    create = client.post("/assessments", json={"student_id": "std-001", "reading_id": "rd-004"})
    aid = create.json()["id"]
    files = {"audio": ("test.webm", b"bytes", "audio/webm")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    assert up.status_code == 200
    assert up.json()["wcpm"] == 0.0


def test_asr_failure_returns_503(client, monkeypatch):
    """ASR gagal → 503 dengan pesan jelas (NFR-03)."""
    import services.speech as speech_mod

    def _fail(*args, **kwargs):
        raise RuntimeError("Speech processing failed: model error")

    monkeypatch.setattr(speech_mod, "transcribe", _fail)
    create = client.post("/assessments", json={"student_id": "std-001", "reading_id": "rd-004"})
    aid = create.json()["id"]
    files = {"audio": ("test.webm", b"bytes", "audio/webm")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    assert up.status_code == 503
    assert "Retry" in up.json()["detail"] or "coba lagi" in up.json()["detail"].lower()


def test_demo_fallback_flag(client, monkeypatch):
    """Mode demo menandai is_demo_fallback=true."""
    import services.speech as speech_mod

    def _demo(audio_path, reference_text=None, reading_id=None,
              reading_repository=None, output_dir=None):
        return TranscriptResult(
            raw_text="ibu pergi ke pasar",
            alignment_words=make_alignment_words(4, 0),
            duration_seconds=2.0,
            framework_result={"job": {"status": "completed"},
                              "alignment": {"status": "computed", "words": []}},
            is_demo=True,
        )

    monkeypatch.setattr(speech_mod, "transcribe", _demo)
    create = client.post("/assessments", json={"student_id": "std-001", "reading_id": "rd-004"})
    aid = create.json()["id"]
    files = {"audio": ("test.webm", b"bytes", "audio/webm")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    assert up.status_code == 200
    assert up.json()["is_demo_fallback"] is True


def test_framework_result_saved(client, monkeypatch):
    """framework_result (JSON audit) tersimpan."""
    import services.speech as speech_mod
    monkeypatch.setattr(speech_mod, "transcribe", mock_transcribe_for(68, 95))
    create = client.post("/assessments", json={"student_id": "std-001", "reading_id": "rd-004"})
    aid = create.json()["id"]
    files = {"audio": ("test.webm", b"bytes", "audio/webm")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    data = up.json()
    assert "framework_result" in data
    assert data["framework_result"]["job"]["status"] == "completed"


def test_accuracy_never_exceeds_100_via_api(client, monkeypatch):
    """Accuracy selalu 0-100 lewat API."""
    import services.speech as speech_mod
    monkeypatch.setattr(speech_mod, "transcribe", mock_transcribe_for(60, 100))
    create = client.post("/assessments", json={"student_id": "std-001", "reading_id": "rd-004"})
    aid = create.json()["id"]
    files = {"audio": ("test.webm", b"bytes", "audio/webm")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    acc = up.json()["accuracy"]
    assert 0 <= acc <= 100


def test_demo_fallback_real_end_to_end(client, monkeypatch):
    """DEMO_FALLBACK tanpa model: transkrip sintetis deterministik, bukan crash.

    Regresi: jalur demo dulu membaca fixture mentah dan berakhir KeyError.
    Sekarang harus menghasilkan WCPM/Accuracy + word_scores bertanda review.
    """
    # Tidak mem-mock transcribe → pakai jalur _demo_fallback asli.
    create = client.post("/assessments", json={"student_id": "std-001", "reading_id": "rd-001"})
    aid = create.json()["id"]
    files = {"audio": ("rekaman.webm", b"bytes", "audio/webm")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    assert up.status_code == 200, up.text
    data = up.json()
    assert data["is_demo_fallback"] is True
    assert data["session_state"] == "COMPREHENSION"
    assert data["total_words_read"] > 0
    assert data["accuracy"] > 0
    # Minimal satu kata ditandai "perlu diperiksa" (review flag), tanpa jenis kesalahan.
    flagged = [w for w in data["word_scores"] if w["review_reasons"]]
    assert len(flagged) >= 1
