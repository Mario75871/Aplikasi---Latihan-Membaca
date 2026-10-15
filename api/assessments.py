"""Assessment API — end-to-end pipeline (v2.5).

Alur: audio → Model #1 (framework) → alignment per kata → Model #2 (scoring)
      → WCPM/Accuracy → comprehension → Adaptive Engine → hasil.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from repository import get_repository
from rules.adaptive_rules import (
    calculate_consecutive_drops,
    determine_season,
)
from services import assessment, speech
from services.adaptive import make_decision
from services.scoring import score_alignment

router = APIRouter(prefix="/assessments", tags=["assessments"])


class CreateAssessmentRequest(BaseModel):
    student_id: str
    reading_id: str


class ComprehensionRequest(BaseModel):
    answers: dict[str, str]


@router.get("")
def list_assessments(student_id: str | None = None):
    """GET /assessments — riwayat asesmen (semua, atau filter per siswa)."""
    repo = get_repository()
    if student_id:
        return repo.list_student_assessments(student_id)
    return repo.list_all_assessments()


@router.post("")
def create_assessment(req: CreateAssessmentRequest):
    """POST /assessments — buat sesi asesmen."""
    repo = get_repository()
    
    student = repo.get_student(req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    reading = repo.get_reading(req.reading_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    
    asmt = repo.create_assessment(req.student_id, req.reading_id)
    return asmt


@router.post("/{assessment_id}/audio")
async def upload_audio(assessment_id: str, audio: UploadFile = File(...)):
    """POST /assessments/{id}/audio — jalankan pipeline penilaian."""
    repo = get_repository()
    asmt = repo.get_assessment(assessment_id)
    if not asmt:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    reading = repo.get_reading(asmt["reading_id"])
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    
    # Simpan audio sementara
    suffix = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        path = tmp.name
    
    try:
        # 1) Model #1 — framework: transkrip + alignment per kata + durasi aktual
        try:
            transcript = speech.transcribe(
                path,
                reading_id=asmt["reading_id"],
                reading_repository={asmt["reading_id"]: reading},
            )
        except RuntimeError as e:
            # ASR gagal → 503 dengan pesan jelas (NFR-03, UI Retry)
            raise HTTPException(
                status_code=503,
                detail=f"Proses speech gagal: {str(e)}. Silakan coba lagi (Retry).",
            )
        
        # 2) Model #2 — penilaian kata dari alignment framework
        proper_nouns = reading.get("proper_nouns", [])
        scored = score_alignment(transcript.alignment_words, proper_nouns=proper_nouns)
        
        # 3) WCPM & Accuracy (durasi aktual dari framework)
        wcpm = assessment.calculate_wcpm(scored.correct_words, transcript.duration_seconds)
        accuracy = assessment.calculate_accuracy(scored.correct_words, scored.total_words_read)
        
        # Simpan hasil
        repo.update_assessment(assessment_id, {
            "wcpm": wcpm,
            "accuracy": accuracy,
            "correct_words": scored.correct_words,
            "incorrect_words": scored.incorrect_words,
            "total_words_read": scored.total_words_read,
            "reading_time_sec": transcript.duration_seconds,
            "transcript": transcript.raw_text,
            "word_scores": [
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
            ],
            "framework_result": transcript.framework_result,  # JSON audit
            "is_demo_fallback": transcript.is_demo,
            "session_state": "COMPREHENSION",
        })
        
        return repo.get_assessment(assessment_id)
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


@router.post("/{assessment_id}/comprehension")
def submit_comprehension(assessment_id: str, req: ComprehensionRequest):
    """POST /assessments/{id}/comprehension — jawaban → Retrieve/Interpret/Reflect."""
    repo = get_repository()
    asmt = repo.get_assessment(assessment_id)
    if not asmt:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
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
    wcpm = asmt.get("wcpm", 0)
    accuracy = asmt.get("accuracy", 0)
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
def get_assessment(assessment_id: str):
    """GET /assessments/{id}."""
    repo = get_repository()
    asmt = repo.get_assessment(assessment_id)
    if not asmt:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return asmt
