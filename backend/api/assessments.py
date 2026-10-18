"""Assessment API — end-to-end pipeline (v2.5).

Alur: audio → Model #1 (framework) → alignment per kata → Model #2 (scoring)
      → WCPM/Accuracy → comprehension → Adaptive Engine → hasil.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel

from api.auth import require_teacher
from repository import Repository, get_teacher_repository, teacher_supabase_client
from rules.adaptive_rules import (
    calculate_consecutive_drops,
    determine_season,
)
from services import assessment, audio_storage, progression, speech
from services.adaptive import make_decision
from services.audio_validation import (
    AudioValidationError,
    suffix_for_format,
    validate_audio_bytes,
    validate_audio_duration,
    warn_if_oversampled,
)
from services.scoring import score_alignment

router = APIRouter(prefix="/assessments", tags=["assessments"])


class CreateAssessmentRequest(BaseModel):
    student_id: str
    reading_id: str


class ComprehensionRequest(BaseModel):
    answers: dict[str, str]


def _owned_assessment(repo, assessment_id: str, teacher: str) -> dict:
    """Ambil asesmen & pastikan milik guru (integrasi #3, A.2). Raise 404 bila bukan."""
    asmt = repo.get_assessment(assessment_id)
    if not asmt:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if asmt.get("teacher_id") not in (None, teacher):
        raise HTTPException(status_code=404, detail="Assessment not found")
    return asmt


def _bearer(authorization: str | None) -> str | None:
    """Ambil token dari header 'Authorization: Bearer <token>'."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def _validate_audio_path(path: str, teacher: str, assessment_id: str) -> None:
    """Pastikan `audio_path` milik guru & asesmen ini (integrasi #6, Opsi A).

    Mencegah **path traversal / IDOR**: klien hanya boleh merujuk objek di
    ``{teacher}/{assessment_id}/``. Bukan → 403/422.
    """
    if not path or ".." in path.split("/"):
        raise HTTPException(status_code=422, detail="Path audio tidak valid.")
    prefix = f"{teacher}/{assessment_id}/"
    if not path.startswith(prefix):
        raise HTTPException(
            status_code=403, detail="Path audio bukan milik asesmen ini."
        )


def asr_timeout_sec() -> float:
    """Batas waktu ASR dari env ASR_TIMEOUT_SEC (fallback 120 detik)."""
    raw = os.getenv("ASR_TIMEOUT_SEC")
    if not raw:
        return 120.0
    try:
        val = float(raw)
        return val if val > 0 else 120.0
    except ValueError:
        return 120.0


async def _transcribe_with_timeout(path: str, **kwargs):
    """Jalankan `speech.transcribe` (CPU-bound) di thread dengan batas waktu.

    Integrasi #5 (C.2): mencegah request menggantung bila ASR lambat/bermasalah.
    Raise `TimeoutError` bila melewati `ASR_TIMEOUT_SEC`.
    """
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(None, lambda: speech.transcribe(path, **kwargs)),
        timeout=asr_timeout_sec(),
    )


@router.get("")
def list_assessments(request: Request, student_id: str | None = None,
                     teacher: str = Depends(require_teacher),
                     repo: Repository = Depends(get_teacher_repository)):
    """GET /assessments — riwayat asesmen milik guru (filter per siswa opsional).

    Integrasi #3 (A.2): jalur "semua asesmen" DILARANG; selalu di-scope ke guru.
    """
    if student_id:
        student = repo.get_student(student_id)
        if not student or student.get("teacher_id") not in (None, teacher):
            raise HTTPException(status_code=404, detail="Student not found")
        return repo.list_student_assessments(student_id)
    return repo.list_all_assessments(teacher_id=teacher)


@router.post("")
def create_assessment(req: CreateAssessmentRequest, request: Request,
                      teacher: str = Depends(require_teacher),
                      repo: Repository = Depends(get_teacher_repository)):
    """POST /assessments — buat sesi asesmen (milik guru).

    Gerbang naik level ditegakkan di sini (bukan hanya di UI) karena keputusan
    tinggal di backend: ``/assess/read?reading=<id>`` menerima id bacaan apa pun,
    jadi UI saja bisa ditembus. Urutannya penting — siswa/bacaan yang tidak
    dikenal harus tetap menjawab 404, bukan 409 (lihat tests/test_api.py).
    """
    student = repo.get_student(req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.get("teacher_id") not in (None, teacher):
        raise HTTPException(status_code=404, detail="Student not found")
    reading = repo.get_reading(req.reading_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")

    completed = progression.completed_reading_ids(repo, req.student_id)
    reason = progression.locked_reason(
        repo.list_readings(), completed, reading, student_name=student.get("name")
    )
    if reason:
        raise HTTPException(status_code=409, detail=reason)

    asmt = repo.create_assessment(req.student_id, req.reading_id,
                                  reading.get("complexity"), teacher_id=teacher)
    return asmt


@router.post("/{assessment_id}/audio/upload-url")
def get_audio_upload_url(assessment_id: str,
                         authorization: str | None = Header(None),
                         teacher: str = Depends(require_teacher),
                         repo: Repository = Depends(get_teacher_repository)):
    """POST /assessments/{id}/audio/upload-url — terbitkan signed upload URL.

    Integrasi #6 (Fase D, Opsi A): klien mengunggah audio **langsung ke Supabase**
    (bypass batas body Vercel 4.5 MB). Backend hanya menerbitkan URL berumur pendek
    setelah verifikasi kepemilikan (guru lain → 404).

    Bila Storage tak dikonfigurasi (in-memory/demo) → ``{"mode": "multipart"}`` agar
    klien memakai jalur lama.
    """
    _owned_assessment(repo, assessment_id, teacher)  # guru lain → 404
    client = teacher_supabase_client(_bearer(authorization))
    if client is None:
        return {"mode": "multipart"}
    path = f"{teacher}/{assessment_id}/normalized.wav"
    signed = audio_storage.create_signed_upload_url(client, path)
    if not signed:
        raise HTTPException(
            status_code=502, detail="Gagal membuat tautan unggah. Coba lagi."
        )
    return {"mode": "signed", **signed}


@router.post("/{assessment_id}/audio")
async def upload_audio(assessment_id: str, request: Request,
                       audio: UploadFile | None = File(None),
                       authorization: str | None = Header(None),
                       teacher: str = Depends(require_teacher),
                       repo: Repository = Depends(get_teacher_repository)):
    """POST /assessments/{id}/audio — jalankan pipeline penilaian.

    Dua bentuk (integrasi #6, Opsi A):
    - ``multipart/form-data`` (fallback) — field ``audio`` berisi berkas.
    - ``application/json { "audio_path": "..." }`` — objek sudah diunggah klien
      langsung ke Storage (via signed URL); backend mengunduhnya.
    """
    asmt = _owned_assessment(repo, assessment_id, teacher)
    
    reading = repo.get_reading(asmt["reading_id"])
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")

    # Ambil byte audio dari salah satu jalur. `pre_stored_path` di-set bila audio
    # SUDAH ada di Storage (jalur JSON) → tak perlu unggah ulang.
    pre_stored_path: str | None = None
    filename = "audio"
    if audio is not None:
        raw = await audio.read()
        filename = audio.filename or "audio"
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        audio_path = (payload or {}).get("audio_path")
        if not audio_path:
            raise HTTPException(
                status_code=422, detail="Audio tidak disertakan (audio atau audio_path)."
            )
        _validate_audio_path(audio_path, teacher, assessment_id)
        client = teacher_supabase_client(_bearer(authorization))
        if client is None:
            raise HTTPException(
                status_code=502, detail="Penyimpanan audio tidak dikonfigurasi."
            )
        raw = audio_storage.download(client, audio_path)
        if raw is None:
            raise HTTPException(
                status_code=502,
                detail="Gagal mengambil audio dari penyimpanan. Coba lagi.",
            )
        pre_stored_path = audio_path
        filename = audio_path.rsplit("/", 1)[-1]

    # Integrasi #3 (Fase C, D4): batas ukuran + format WAV/MP3 via magic bytes.
    head = raw[:12]
    try:
        fmt = validate_audio_bytes(head, len(raw))
    except AudioValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    # Integrasi #4 (D2): catat bila sample rate jauh di atas target (bukan tolak).
    warning = warn_if_oversampled(fmt, head, filename)
    if warning:
        print(warning)
    suffix = suffix_for_format(fmt)  # dari whitelist, bukan input klien
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        path = tmp.name

    try:
        # 1) Model #1 — framework: transkrip + alignment per kata + durasi aktual
        #     Integrasi #5 (C.2): batas waktu ASR — jangan biarkan request menggantung.
        try:
            transcript = await _transcribe_with_timeout(
                path,
                reading_id=asmt["reading_id"],
                reading_repository={asmt["reading_id"]: reading},
            )
        except (TimeoutError, asyncio.TimeoutError):
            raise HTTPException(
                status_code=504,
                detail=(
                    "Proses speech melebihi batas waktu. Coba rekaman lebih pendek "
                    "atau ulangi (Retry)."
                ),
            )
        except RuntimeError as e:
            # ASR gagal → 503 dengan pesan jelas (NFR-03, UI Retry)
            raise HTTPException(
                status_code=503,
                detail=f"Proses speech gagal: {str(e)}. Silakan coba lagi (Retry).",
            )

        # 1b) Batas durasi (integrasi #5, D4). Durasi hanya diketahui setelah probe/
        # transkripsi. Bila tersedia & melebihi batas → 422 (audio terlalu panjang).
        # Durasi None (tak tersedia) TIDAK ditolak — konsisten null != 0.
        try:
            validate_audio_duration(transcript.duration_seconds)
        except AudioValidationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)

        # 2) Model #2 — penilaian kata dari alignment framework
        proper_nouns = reading.get("proper_nouns", [])
        scored = score_alignment(transcript.alignment_words, proper_nouns=proper_nouns)
        
        # 3) WCPM & Accuracy (durasi aktual dari framework)
        wcpm = assessment.calculate_wcpm(scored.correct_words, transcript.duration_seconds)
        accuracy = assessment.calculate_accuracy(scored.correct_words, scored.total_words_read)

        # 3b) Supabase Storage (integrasi #4, D2/B.4): simpan audio untuk audit.
        # Gagal unggah TIDAK menggagalkan penilaian → audio_url dibiarkan null.
        # Integrasi #6 (Opsi A): bila audio SUDAH diunggah klien via signed URL,
        # jangan unggah ulang — cukup catat path-nya.
        if pre_stored_path is not None:
            audio_url = pre_stored_path
        else:
            audio_url = None
            client = teacher_supabase_client(_bearer(authorization))
            if client is not None:
                audio_url = audio_storage.store_audio(
                    client, teacher, assessment_id, raw, fmt, kind="normalized",
                )
        
        # Simpan hasil
        update: dict = {
            "wcpm": wcpm,
            "accuracy": accuracy,
            "correct_words": scored.correct_words,
            "incorrect_words": scored.incorrect_words,
            "total_words_read": scored.total_words_read,
            "reading_time_sec": transcript.duration_seconds,
            "transcript": transcript.raw_text,
            "framework_result": transcript.framework_result,  # JSON audit
            "is_demo_fallback": transcript.is_demo,
            "session_state": "COMPREHENSION",
        }
        if audio_url is not None:
            update["audio_url"] = audio_url
        repo.update_assessment(assessment_id, update)
        # word_scores disimpan di tabel relasional tersendiri (Fase 0).
        repo.save_word_scores(assessment_id, [
            {
                "position": w.position,
                "reference_word": w.reference_word,
                "transcript_word": w.transcript_word,
                "confidence": w.confidence,
                "attempted": w.attempted,
                "is_correct": w.is_correct,
                "is_proper_noun": w.is_proper_noun,
                "reason": w.reason,
                "review_reasons": w.review_reasons,
                "ts_start": w.start_seconds,
                "ts_end": w.end_seconds,
            }
            for w in scored.words
        ])

        return repo.get_assessment(assessment_id)
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


@router.post("/{assessment_id}/comprehension")
def submit_comprehension(assessment_id: str, req: ComprehensionRequest,
                         request: Request,
                         teacher: str = Depends(require_teacher),
                         repo: Repository = Depends(get_teacher_repository)):
    """POST /assessments/{id}/comprehension — jawaban → Retrieve/Interpret/Reflect."""
    asmt = _owned_assessment(repo, assessment_id, teacher)
    
    if asmt.get("session_state") not in ["COMPREHENSION", "COMPLETED"]:
        raise HTTPException(
            status_code=422,
            detail="Audio belum diproses. Upload audio terlebih dahulu.",
        )
    
    reading = repo.get_reading(asmt["reading_id"])
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    
    student = repo.get_student(asmt["student_id"])
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    questions = reading.get("questions", [])
    answers = req.answers

    # Fase C.7 (integrasi #2): tolak jawaban asing (bentrok #8). Hanya question_id
    # yang benar-benar ada di teks bacaan ini yang diterima; competency diambil dari
    # data pertanyaan (bukan dari klien), sehingga klien tak bisa memalsukan bucket.
    valid_ids = {q["id"] for q in questions}
    unknown = sorted(set(answers) - valid_ids)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=(
                "Jawaban memuat question_id yang tidak dikenal untuk bacaan ini: "
                f"{unknown}."
            ),
        )

    buckets = {"retrieve": [], "interpret": [], "reflect": []}
    for q in questions:
        given = answers.get(q["id"])
        correct = 1.0 if given == q["answer_id"] else 0.0
        buckets[q["competency"]].append(correct)
    
    def pct(lst: list[float]) -> float:
        return round((sum(lst) / len(lst)) * 100, 2) if lst else 0.0
    
    retrieve = pct(buckets["retrieve"])
    interpret = pct(buckets["interpret"])
    reflect = pct(buckets["reflect"])
    
    # Adaptive Engine (§19) — rule-based, deterministik
    # WCPM/Accuracy bisa None (durasi tak tersedia / penyebut 0). Bila tak dapat
    # dihitung, jangan mengarang 0 → tolak dengan pesan jelas (null ≠ 0).
    wcpm = asmt.get("wcpm")
    accuracy = asmt.get("accuracy")
    if wcpm is None or accuracy is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Skor membaca belum dapat dihitung (durasi audio atau jumlah kata "
                "tidak tersedia). Silakan proses audio terlebih dahulu."
            ),
        )
    grade = student.get("grade", 1)
    season = determine_season(datetime.now(timezone.utc))
    current_level = reading.get("complexity", 1)
    
    # Riwayat untuk BR-04 dan BR-07 (D3)
    history = [
        a for a in repo.list_student_assessments(asmt["student_id"])
        if a["id"] != assessment_id and a.get("session_state") == "COMPLETED"
    ]
    history.sort(key=lambda a: a.get("created_at", ""))  # lama → baru
    
    previous_status = history[-1].get("status") if history else None
    consecutive_drops, prev_wcpm, prev_accuracy = calculate_consecutive_drops(
        wcpm, accuracy, history
    )
    
    decision = make_decision(
        wcpm=wcpm,
        accuracy=accuracy,
        retrieve=retrieve, interpret=interpret, reflect=reflect,
        grade=grade,
        season=season,
        previous_status=previous_status,
        previous_wcpm=prev_wcpm,
        previous_accuracy=prev_accuracy,
        current_level=current_level,
        consecutive_drops=consecutive_drops,
    )
    
    repo.update_assessment(assessment_id, {
        "retrieve": retrieve,
        "interpret": interpret,
        "reflect": reflect,
        "status": decision.status,
        "recommendation": decision.recommendation,
        "next_reading_level": decision.next_reading_level,
        "rules_fired": decision.rules_fired,
        "previous_wcpm": prev_wcpm,
        "previous_accuracy": prev_accuracy,
        "consecutive_drops": consecutive_drops,
        "season": season,
        "session_state": "COMPLETED",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    
    return repo.get_assessment(assessment_id)


@router.get("/{assessment_id}")
def get_assessment(assessment_id: str, request: Request,
                   teacher: str = Depends(require_teacher),
                   repo: Repository = Depends(get_teacher_repository)):
    """GET /assessments/{id} — 404 bila bukan milik guru."""
    return _owned_assessment(repo, assessment_id, teacher)


@router.get("/{assessment_id}/audio-url")
def get_audio_url(assessment_id: str,
                  authorization: str | None = Header(None),
                  teacher: str = Depends(require_teacher),
                  repo: Repository = Depends(get_teacher_repository)):
    """GET /assessments/{id}/audio-url — signed URL berumur pendek (integrasi #5, D3).

    Hanya pemilik (guru) yang boleh. Guru lain → 404 (hindari bocor keberadaan).
    `audio_url` null → 404 (rekaman tidak tersedia; bukan error server).
    """
    asmt = _owned_assessment(repo, assessment_id, teacher)
    path = asmt.get("audio_url")
    if not path:
        raise HTTPException(
            status_code=404, detail="Rekaman tidak tersedia untuk asesmen ini."
        )
    client = teacher_supabase_client(_bearer(authorization))
    if client is None:
        raise HTTPException(
            status_code=502, detail="Penyimpanan audio tidak dikonfigurasi."
        )
    url = audio_storage.signed_url(client, path)
    if not url:
        raise HTTPException(
            status_code=502, detail="Gagal membuat tautan rekaman. Coba lagi."
        )
    return {"url": url, "expires_in": audio_storage.SIGNED_URL_TTL_SEC}
