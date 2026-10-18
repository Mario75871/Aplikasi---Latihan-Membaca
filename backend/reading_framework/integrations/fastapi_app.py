"""FastAPI backend minimal-FUNGSIONAL untuk integrasi website.

Menghubungkan endpoint ke pipeline NYATA (bukan data statis). Storage lokal di
disk — BUKAN database produksi (didokumentasikan sebagai batasan).

Keamanan/privacy:
- job_id tanpa identitas pribadi (pseudonim acak);
- validasi ukuran & format upload; sanitasi nama file;
- tidak mengembalikan path absolut filesystem ke klien;
- cegah path traversal pada akses file;
- tidak menjalankan file audio sebagai perintah.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ..audio import sanitize_filename
from ..config import FrameworkConfig, PROFILE_RAW_READING
from ..pipeline import RAW_TRANSCRIPT_FILENAME, transcribe_reading
from ..repository import LocalQuestionRepository, QuestionNotFoundError

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXT = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac")

#: Direktori kerja storage lokal (relatif; tidak pernah diekspos ke klien).
_STORAGE_ROOT = Path("results") / "api_jobs"

#: Model di-cache agar tidak dimuat per request.
_MODEL_CACHE: dict[tuple, Any] = {}


# --------------------------------------------------------------------------- #
# Storage lokal sederhana
# --------------------------------------------------------------------------- #

class LocalJobStore:
    """Job store berbasis disk. BUKAN database produksi."""

    def __init__(self, root: Path = _STORAGE_ROOT):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def job_dir(self, job_id: str) -> Path:
        safe = sanitize_filename(job_id, fallback="job")
        return self.root / safe

    def create(self, job_id: str) -> Path:
        d = self.job_dir(job_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_status(self, job_id: str, status: dict) -> None:
        d = self.create(job_id)
        (d / "status.json").write_text(
            json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_status(self, job_id: str) -> dict | None:
        p = self.job_dir(job_id) / "status.json"
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def load_result(self, job_id: str) -> dict | None:
        p = self.job_dir(job_id) / "result.json"
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def store_review(self, job_id: str, payload: dict) -> None:
        d = self.create(job_id)
        (d / "human_review.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_job_id() -> str:
    return f"job-{uuid.uuid4().hex[:16]}"


# --------------------------------------------------------------------------- #
# Model API
# --------------------------------------------------------------------------- #

class CreateJobResponse(BaseModel):
    job_id: str
    status: str


class HealthResponse(BaseModel):
    status: str
    engine: str
    schema_version: str


class ReviewRequest(BaseModel):
    reviewer_id: str
    decisions: list[dict]
    notes: str | None = None


# --------------------------------------------------------------------------- #
# App factory (memudahkan test dengan storage sementara)
# --------------------------------------------------------------------------- #

def create_app(question_bank_path: str | Path | None = None,
               store: LocalJobStore | None = None) -> FastAPI:
    app = FastAPI(
        title="Reading Framework API",
        version="1.0.0",
        description="Raw ASR + target-based alignment untuk tes baca anak Indonesia. "
                    "Storage lokal — BUKAN deployment produksi.",
    )
    job_store = store or LocalJobStore()
    repo = LocalQuestionRepository.from_file(question_bank_path) if question_bank_path else None

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        from ..config import SCHEMA_VERSION
        return HealthResponse(status="ok", engine="faster-whisper",
                              schema_version=SCHEMA_VERSION)

    @app.post("/jobs", response_model=CreateJobResponse)
    def create_job(question_id: str | None = Form(default=None)) -> CreateJobResponse:
        if question_id and repo is None:
            raise HTTPException(status_code=400, detail="no question bank configured")
        if question_id and repo is not None:
            try:
                repo.get(question_id)
            except QuestionNotFoundError:
                raise HTTPException(status_code=404, detail=f"question not found: {question_id}")
        job_id = _new_job_id()
        job_store.create(job_id)
        job_store.save_status(job_id, {
            "job_id": job_id, "status": "created", "created_at": _now(),
            "question_id": question_id,
        })
        return CreateJobResponse(job_id=job_id, status="created")

    @app.post("/jobs/{job_id}/audio")
    async def upload_audio(job_id: str, file: UploadFile = File(...)) -> dict:
        status = job_store.load_status(job_id)
        if status is None:
            raise HTTPException(status_code=404, detail="job not found")

        filename = sanitize_filename(file.filename or "audio", fallback="audio.wav")
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(status_code=400, detail=f"unsupported extension: {ext}")

        data = await file.read()
        if len(data) == 0:
            raise HTTPException(status_code=400, detail="empty upload")
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="upload too large")

        d = job_store.job_dir(job_id)
        dest = d / f"source{ext}"
        dest.write_bytes(data)
        status.update({"status": "audio_uploaded", "source_filename": filename})
        job_store.save_status(job_id, status)
        return {"job_id": job_id, "status": "audio_uploaded", "filename": filename}

    @app.post("/jobs/{job_id}/transcribe")
    def run_transcribe(job_id: str) -> dict:
        status = job_store.load_status(job_id)
        if status is None:
            raise HTTPException(status_code=404, detail="job not found")
        d = job_store.job_dir(job_id)
        sources = list(d.glob("source.*"))
        if not sources:
            raise HTTPException(status_code=400, detail="no audio uploaded for job")

        question_id = status.get("question_id")
        job_store.save_status(job_id, {**status, "status": "processing"})

        cfg = FrameworkConfig(asr_profile=PROFILE_RAW_READING)
        key = (cfg.model, cfg.device, cfg.compute_type, cfg.cpu_threads)
        if key not in _MODEL_CACHE:
            from ..asr_engine import load_model
            model, _ = load_model(*key)
            _MODEL_CACHE[key] = model

        try:
            reading = transcribe_reading(
                sources[0],
                question_id=question_id,
                repository=repo,
                model=_MODEL_CACHE[key],
                config=cfg,
                output_dir=d,
                persist=True,
                overwrite=True,
            )
        except Exception as exc:  # noqa: BLE001
            job_store.save_status(job_id, {**status, "status": "failed",
                                           "error": f"{type(exc).__name__}: {exc}"})
            raise HTTPException(status_code=500, detail="transcription failed")

        job_store.save_status(job_id, {
            **status, "status": reading.result["job"]["status"],
            "completed_at": _now(),
        })
        return _public_result(job_id, reading.result)

    @app.get("/jobs/{job_id}")
    def get_status(job_id: str) -> dict:
        status = job_store.load_status(job_id)
        if status is None:
            raise HTTPException(status_code=404, detail="job not found")
        return status

    @app.get("/jobs/{job_id}/result")
    def get_result(job_id: str) -> dict:
        result = job_store.load_result(job_id)
        if result is None:
            status = job_store.load_status(job_id)
            if status is None:
                raise HTTPException(status_code=404, detail="job not found")
            raise HTTPException(status_code=409, detail="result not ready")
        return _public_result(job_id, result)

    @app.get("/jobs/{job_id}/transcript", response_class=PlainTextResponse)
    def get_transcript(job_id: str) -> str:
        p = job_store.job_dir(job_id) / RAW_TRANSCRIPT_FILENAME
        if not p.is_file():
            raise HTTPException(status_code=404, detail="transcript not available")
        return p.read_text(encoding="utf-8")

    @app.get("/jobs/{job_id}/alignment")
    def get_alignment(job_id: str) -> dict:
        result = job_store.load_result(job_id)
        if result is None:
            raise HTTPException(status_code=404, detail="result not available")
        return {"alignment": result["alignment"], "review": result["review"]}

    @app.post("/jobs/{job_id}/review")
    def save_review(job_id: str, payload: ReviewRequest) -> dict:
        if job_store.load_status(job_id) is None:
            raise HTTPException(status_code=404, detail="job not found")
        record = {
            "job_id": job_id,
            "reviewer_id": payload.reviewer_id,
            "reviewed_at": _now(),
            "decisions": payload.decisions,
            "notes": payload.notes,
        }
        # Simpan terpisah dari raw transcript (tidak menimpa bukti ASR).
        job_store.store_review(job_id, record)
        return {"job_id": job_id, "status": "review_saved"}

    return app


def _public_result(job_id: str, result: dict) -> dict:
    """Buang path/ref internal; hanya kembalikan kontrak publik + URL aman."""
    public = dict(result)
    # Ganti raw_text_file dengan URL endpoint, bukan path filesystem.
    public["transcript"] = dict(result["transcript"])
    public["transcript"]["raw_text_file"] = (
        f"/jobs/{job_id}/transcript" if result["transcript"].get("raw_text_file") else None
    )
    # Tidak ada field yang sengaja menyertakan path absolut.
    return public


#: App default (dipakai uvicorn). Question bank opsional via env.
def _default_app() -> FastAPI:
    import os
    qb = os.environ.get("READING_QUESTION_BANK")
    return create_app(question_bank_path=qb)


app = _default_app()
