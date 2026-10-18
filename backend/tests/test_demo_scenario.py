"""Test skenario demo F-08 end-to-end lewat API (3 asesmen).

Kelas 2, awal tahun, batas WCPM = 40.
A1 (WCPM 58, Acc 92%, R85/I70/Rf60) → INTERVENE (BR-02)
A2 (WCPM 68, Acc 95%, R90/I86/Rf82) → PROMOTION_CANDIDATE
A3 (WCPM 75, Acc 96%, R92/I88/Rf84) → PROMOTE

Menggunakan mock framework (transcript tiruan) untuk menghindari model Whisper.
"""
import pytest
from fastapi.testclient import TestClient

from seed.reading_texts import SEED_IDS
from services.speech import TranscriptResult
from tests.conftest import unlock_level, wav_bytes

STUDENT_DIKA = SEED_IDS["student_dika"]
READING_1 = SEED_IDS["reading_1"]
READING_4 = SEED_IDS["reading_4"]


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
    """TestClient dengan Level 1 Dika sudah tuntas → Level 2 terbuka.

    Modul ini menguji pipeline audio & pemahaman di Level 2 (READING_4), jadi
    prasyarat gerbang naik level dipenuhi di fixture — bukan dengan mematikan
    gerbangnya. Gerbang & tangganya diuji tersendiri di tests/test_progression.py.
    """
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DEMO_FALLBACK", "true")  # skip model load, transcribe di-mock

    import repository
    repository._repo = None

    import main
    with TestClient(main.app) as c:
        unlock_level(repository.get_repository(), STUDENT_DIKA, 2)
        yield c


def _run_assessment(client, monkeypatch, wcpm, accuracy, comprehension, reading_id=READING_4):
    """Jalankan satu asesmen end-to-end dengan mock transcribe."""
    import services.speech as speech_mod
    monkeypatch.setattr(speech_mod, "transcribe", mock_transcribe_for(wcpm, accuracy))

    # Buat asesmen
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": reading_id})
    assert create.status_code == 200
    aid = create.json()["id"]

    # Upload audio (mock)
    from tests.conftest import wav_bytes
    files = {"audio": ("test.wav", wav_bytes(), "audio/wav")}
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
    assert a3["next_reading_level"] == 3  # reading_4 level 2 → naik ke level 3


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
    """Reading time 0 → WCPM None (tidak dapat dihitung), tidak crash.

    Aturan null ≠ 0 (JSON_SCHEMA §2): durasi 0 berarti WCPM TIDAK DAPAT dihitung,
    bukan nol.
    """
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
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    from tests.conftest import wav_bytes
    files = {"audio": ("test.wav", wav_bytes(), "audio/wav")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    assert up.status_code == 200
    assert up.json()["wcpm"] is None


def test_asr_failure_returns_503(client, monkeypatch):
    """ASR gagal → 503 dengan pesan jelas (NFR-03)."""
    import services.speech as speech_mod

    def _fail(*args, **kwargs):
        raise RuntimeError("Speech processing failed: model error")

    monkeypatch.setattr(speech_mod, "transcribe", _fail)
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    from tests.conftest import wav_bytes
    files = {"audio": ("test.wav", wav_bytes(), "audio/wav")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    assert up.status_code == 503
    assert "Retry" in up.json()["detail"] or "coba lagi" in up.json()["detail"].lower()


def test_audio_too_long_returns_422(client, monkeypatch):
    """Durasi audio > batas (integrasi #5, D4) → 422 dengan pesan jelas."""
    import services.speech as speech_mod

    monkeypatch.setenv("MAX_AUDIO_DURATION_SEC", "300")

    def _long(audio_path, reference_text=None, reading_id=None,
              reading_repository=None, output_dir=None):
        return TranscriptResult(
            raw_text="kata " * 10,
            alignment_words=make_alignment_words(10, 0),
            duration_seconds=301.0,  # > 300 detik
            framework_result={"job": {"status": "completed"},
                              "alignment": {"status": "computed", "words": []}},
            is_demo=False,
        )

    monkeypatch.setattr(speech_mod, "transcribe", _long)
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    from tests.conftest import wav_bytes
    files = {"audio": ("test.wav", wav_bytes(), "audio/wav")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    assert up.status_code == 422
    assert "melebihi batas" in up.json()["detail"]


def test_asr_timeout_returns_504(client, monkeypatch):
    """ASR melebihi ASR_TIMEOUT_SEC → 504 (integrasi #5, C.2), bukan menggantung."""
    import time

    import services.speech as speech_mod

    monkeypatch.setenv("ASR_TIMEOUT_SEC", "0.2")

    def _slow(audio_path, reference_text=None, reading_id=None,
              reading_repository=None, output_dir=None):
        time.sleep(1.0)  # > timeout
        return TranscriptResult(
            raw_text="x", alignment_words=make_alignment_words(1, 0),
            duration_seconds=5.0,
            framework_result={"job": {"status": "completed"},
                              "alignment": {"status": "computed", "words": []}},
            is_demo=False,
        )

    monkeypatch.setattr(speech_mod, "transcribe", _slow)
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    from tests.conftest import wav_bytes
    files = {"audio": ("test.wav", wav_bytes(), "audio/wav")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    assert up.status_code == 504
    assert "batas waktu" in up.json()["detail"].lower() or "Retry" in up.json()["detail"]


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
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    from tests.conftest import wav_bytes
    files = {"audio": ("test.wav", wav_bytes(), "audio/wav")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    assert up.status_code == 200
    assert up.json()["is_demo_fallback"] is True


def test_framework_result_saved(client, monkeypatch):
    """framework_result (JSON audit) tersimpan."""
    import services.speech as speech_mod
    monkeypatch.setattr(speech_mod, "transcribe", mock_transcribe_for(68, 95))
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    from tests.conftest import wav_bytes
    files = {"audio": ("test.wav", wav_bytes(), "audio/wav")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    data = up.json()
    assert "framework_result" in data
    assert data["framework_result"]["job"]["status"] == "completed"


def test_accuracy_never_exceeds_100_via_api(client, monkeypatch):
    """Accuracy selalu 0-100 lewat API."""
    import services.speech as speech_mod
    monkeypatch.setattr(speech_mod, "transcribe", mock_transcribe_for(60, 100))
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    from tests.conftest import wav_bytes
    files = {"audio": ("test.wav", wav_bytes(), "audio/wav")}
    up = client.post(f"/assessments/{aid}/audio", files=files)
    acc = up.json()["accuracy"]
    assert 0 <= acc <= 100


def test_demo_fallback_real_end_to_end(client, monkeypatch):
    """DEMO_FALLBACK tanpa model: transkrip sintetis deterministik, bukan crash.

    Regresi: jalur demo dulu membaca fixture mentah dan berakhir KeyError.
    Sekarang harus menghasilkan WCPM/Accuracy + word_scores bertanda review.
    """
    # Tidak mem-mock transcribe → pakai jalur _demo_fallback asli.
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_1})
    aid = create.json()["id"]
    from tests.conftest import wav_bytes
    files = {"audio": ("rekaman.wav", wav_bytes(), "audio/wav")}
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


# ========== C.7 (integrasi #2): validasi answers comprehension ==========

def test_comprehension_rejects_unknown_question_id(client, monkeypatch):
    """Fase C.7: jawaban dengan question_id asing → 422 (bentrok #8 ditutup)."""
    import services.speech as speech_mod
    monkeypatch.setattr(speech_mod, "transcribe", mock_transcribe_for(60, 95))

    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    from tests.conftest import wav_bytes
    files = {"audio": ("test.wav", wav_bytes(), "audio/wav")}
    assert client.post(f"/assessments/{aid}/audio", files=files).status_code == 200

    reading = client.get(f"/readings/{READING_4}").json()
    answers = {q["id"]: q["answer_id"] for q in reading["questions"]}
    answers["q-tidak-ada-999"] = "x"  # question_id asing

    resp = client.post(f"/assessments/{aid}/comprehension", json={"answers": answers})
    assert resp.status_code == 422
    assert "tidak dikenal" in resp.json()["detail"]


def test_comprehension_accepts_only_valid_question_ids(client, monkeypatch):
    """Fase C.7: jawaban sah tetap diterima (tidak over-reject)."""
    result = _run_assessment(client, monkeypatch, wcpm=60, accuracy=95, comprehension={})
    assert result["status"] is not None


# ========== C.2 (integrasi #3): validasi format upload di endpoint ==========

def test_upload_rejects_webm_415(client, monkeypatch):
    """D4: webm (default MediaRecorder) ditolak 415; hanya WAV/MP3."""
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    files = {"audio": ("rekaman.webm", b"\x1a\x45\xdf\xa3" + b"\x00" * 100, "audio/webm")}
    resp = client.post(f"/assessments/{aid}/audio", files=files)
    assert resp.status_code == 415
    assert "WAV" in resp.json()["detail"] or "MP3" in resp.json()["detail"]


# ========== Integrasi #6 (Opsi A): upload via audio_path (signed upload) ==========

def test_upload_via_audio_path_end_to_end(client, monkeypatch):
    """Klien unggah ke Storage dulu → POST /audio {audio_path} → pipeline jalan."""
    import api.assessments as asmt_mod
    import services.speech as speech_mod
    from api.auth import _demo_teacher_id
    from tests.conftest import wav_bytes

    monkeypatch.setattr(speech_mod, "transcribe", mock_transcribe_for(60, 95))

    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    teacher = _demo_teacher_id()
    path = f"{teacher}/{aid}/normalized.wav"

    # Storage palsu: klien guru ada; unduh mengembalikan WAV valid.
    monkeypatch.setattr(asmt_mod, "teacher_supabase_client", lambda tok: object())
    monkeypatch.setattr(asmt_mod.audio_storage, "download", lambda c, p: wav_bytes())

    resp = client.post(f"/assessments/{aid}/audio", json={"audio_path": path})
    assert resp.status_code == 200, resp.text
    assert resp.json()["session_state"] == "COMPREHENSION"
    # audio_url = path yang sudah diunggah (tak diunggah ulang).
    assert resp.json()["audio_url"] == path


def test_upload_via_audio_path_wrong_owner_403(client, monkeypatch):
    """audio_path milik guru lain → 403 (anti IDOR)."""
    import api.assessments as asmt_mod
    from tests.conftest import wav_bytes

    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    monkeypatch.setattr(asmt_mod, "teacher_supabase_client", lambda tok: object())
    monkeypatch.setattr(asmt_mod.audio_storage, "download", lambda c, p: wav_bytes())

    resp = client.post(f"/assessments/{aid}/audio", json={"audio_path": f"other/{aid}/normalized.wav"})
    assert resp.status_code == 403


def test_upload_no_audio_422(client, monkeypatch):
    """Tanpa audio (multipart) maupun audio_path → 422."""
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    resp = client.post(f"/assessments/{aid}/audio", json={})
    assert resp.status_code == 422


def test_upload_rejects_oversize_413(client, monkeypatch):
    """D4: file > batas → 413."""
    monkeypatch.setenv("MAX_AUDIO_BYTES", "1000")
    create = client.post("/assessments", json={"student_id": STUDENT_DIKA, "reading_id": READING_4})
    aid = create.json()["id"]
    payload = wav_bytes(n_samples=2000)  # > 1000 byte
    files = {"audio": ("besar.wav", payload, "audio/wav")}
    resp = client.post(f"/assessments/{aid}/audio", files=files)
    assert resp.status_code == 413
