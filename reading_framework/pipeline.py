"""Pipeline: orkestrasi end-to-end.

Urutan WAJIB:
    Audio -> ASR mentah -> simpan raw transcript -> alignment pakai target
    -> evaluasi (metrik) -> review -> serialize.

Target HANYA dipakai setelah ASR selesai. Fungsi yang melakukan decoding
(``asr_engine.transcribe_audio``) tidak pernah menerima teks target.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import asr_engine
from .alignment import (
    OPERATION_DELETION,
    OPERATION_INSERTION,
    OPERATION_MATCH,
    OPERATION_SUBSTITUTION,
    align_words,
    normalize_for_alignment,
)
from .audio import probe_audio, sanitize_filename
from .config import (
    DEFAULT_NORMALIZATION,
    FrameworkConfig,
    PROFILE_RAW_READING,
)
from .metrics import STATUS_COMPUTED, calculate_metrics
from .repository import QuestionNotFoundError, QuestionRepository
from .review_flags import (
    REASON_REFERENCE_TRANSCRIPT_MISMATCH,
    build_review_flags,
    detect_watermark,
)
from .serializers import build_result_schema
from .spelling_normalization import normalize_spelling
from .transcript_writer import write_json, write_raw_transcript_text

RAW_TRANSCRIPT_FILENAME = "transcript_raw.txt"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _job_id() -> str:
    return f"job-{uuid.uuid4().hex[:16]}"


@dataclass
class ReadingResult:
    """Hasil pipeline terstruktur: kontrak + artefak + status."""

    result: dict[str, Any]              # kontrak JSON (schema_version 1.0.0)
    output_dir: str | None = None
    raw_text_path: str | None = None
    json_path: str | None = None
    asr_ok: bool = True

    @property
    def job_id(self) -> str:
        return self.result["job"]["job_id"]

    @property
    def raw_text(self) -> str | None:
        return self.result["transcript"]["raw_text"]


def align_transcript(
    *,
    target_text: str | None,
    asr_result,
    thresholds=None,
) -> dict[str, Any]:
    """Align target <-> transkrip dengan timestamp & probability dari model.

    Mengembalikan dict mentah untuk serializer. Tidak pernah mengubah transkrip.
    """
    if target_text is None:
        return {"status": "not_computed", "reason": "reference_not_provided",
                "normalization_profile": DEFAULT_NORMALIZATION.profile_id}

    normalized_target = normalize_for_alignment(target_text, DEFAULT_NORMALIZATION)
    if not normalized_target:
        # Referensi ADA tapi kosong/hanya tanda baca setelah normalisasi.
        return {"status": "not_computed", "reason": "reference_invalid",
                "normalization_profile": DEFAULT_NORMALIZATION.profile_id}

    # Bangun daftar kata transkrip berurutan beserta sumber (segmen/timestamp/prob).
    flat_words: list[dict[str, Any]] = []
    for seg in asr_result.segments:
        for w in seg.words:
            flat_words.append({
                "word": w.word,
                "start": w.start,
                "end": w.end,
                "probability": w.probability,
                "segment_id": seg.id,
            })

    ops = align_words(target_text, asr_result.raw_text, DEFAULT_NORMALIZATION)
    metrics = calculate_metrics(target_text, asr_result.raw_text, DEFAULT_NORMALIZATION)

    # Map hasil operasi ke sumber kata transkrip secara berurutan.
    items: list[dict[str, Any]] = []
    hyp_cursor = 0
    for position, (operation, ref_word, hyp_word) in enumerate(ops):
        item: dict[str, Any] = {
            "position": position,
            "reference_word": ref_word,
            "transcript_word": hyp_word,
            "operation": operation,
            "start_seconds": None,
            "end_seconds": None,
            "model_probability": None,
            "segment_id": None,
            "review_required": False,
            "review_reasons": [],
            "review_status": "none",
        }
        if operation in (OPERATION_MATCH, OPERATION_SUBSTITUTION, OPERATION_INSERTION):
            # konsumsi satu kata transkrip berikutnya
            if hyp_cursor < len(flat_words):
                src = flat_words[hyp_cursor]
                item["start_seconds"] = src["start"]
                item["end_seconds"] = src["end"]
                item["model_probability"] = src["probability"]
                item["segment_id"] = src["segment_id"]
            hyp_cursor += 1
        # deletion: tidak ada kata transkrip -> timestamp/probability biarkan null

        if operation != OPERATION_MATCH:
            item["review_required"] = True
            item["review_reasons"] = [REASON_REFERENCE_TRANSCRIPT_MISMATCH]
            item["review_status"] = "pending"
        items.append(item)

    return {
        "status": "computed",
        "reason": None,
        "normalization_profile": DEFAULT_NORMALIZATION.profile_id,
        "reference_word_count": metrics.reference_word_count,
        "transcript_word_count": metrics.transcript_word_count,
        "matches": metrics.matches,
        "substitutions": metrics.substitutions,
        "deletions": metrics.deletions,
        "insertions": metrics.insertions,
        "edit_distance": metrics.edit_distance,
        "wer": metrics.wer,
        "cer": metrics.cer,
        "words": items,
    }


def transcribe_reading(
    audio_path: str | Path,
    *,
    reference_text: str | None = None,
    question_id: str | None = None,
    repository: QuestionRepository | None = None,
    model: Any | None = None,
    config: FrameworkConfig | None = None,
    output_dir: str | Path | None = None,
    persist: bool = True,
    overwrite: bool = False,
    peak_rss_reader=None,
) -> ReadingResult:
    """Library interface stabil untuk backend website.

    - ``question_id`` + ``repository``: target diambil dari bank soal resmi.
    - ``reference_text``: mode eksplisit (CLI/dev); dipisah dari mode produksi.
    - ``model``: model yang sudah dimuat (reuse); bila ``None`` dimuat sekali.
    """
    cfg = config or FrameworkConfig()
    started = time.perf_counter()

    audio = Path(audio_path)
    audio_info = probe_audio(audio)

    job_id = _job_id()
    created_at = _utc_now()

    reference: dict[str, Any] = {"provided": False}
    warnings: list[str] = []
    errors: list[str] = []

    # --- Sumber target: repository (produksi) atau teks eksplisit (dev) ---- #
    target_text: str | None = None
    if question_id is not None:
        if repository is None:
            errors.append("question_id given but no repository configured")
        else:
            try:
                question = repository.get(question_id)
                target_text = question.target_text
                reference = {
                    "provided": bool(target_text and target_text.strip()),
                    "target_text": target_text,
                    "normalized_text": normalize_for_alignment(target_text) or None,
                    "source_id": question.question_id,
                    "source_type": question.source_type,
                    "source_version": question.version,
                }
                if not target_text or not target_text.strip():
                    warnings.append("reference target_text is empty")
            except QuestionNotFoundError as exc:
                errors.append(str(exc))
    elif reference_text is not None:
        target_text = reference_text
        reference = {
            "provided": bool(reference_text.strip()),
            "target_text": reference_text,
            "normalized_text": normalize_for_alignment(reference_text) or None,
            "source_id": None,
            "source_type": "file",
            "source_version": None,
        }

    # --- ASR mentah (target TIDAK diteruskan) ------------------------------ #
    if model is None:
        model, load_seconds = asr_engine.load_model(
            cfg.model, cfg.device, cfg.compute_type, cfg.cpu_threads, cfg.num_workers,
        )
    else:
        load_seconds = None

    asr_result = asr_engine.transcribe_audio(
        model, audio, profile=cfg.asr_profile, language=cfg.language,
        peak_rss_reader=peak_rss_reader,
    )
    asr_result.load_seconds = load_seconds
    asr_result.device = cfg.device
    asr_result.compute_type = cfg.compute_type
    asr_result.cpu_threads = cfg.cpu_threads
    asr_result.model = cfg.model

    asr_ok = asr_result.ok
    if not asr_ok:
        errors.append(asr_result.error)
    warnings.extend(asr_result.warnings)

    if detect_watermark(asr_result.raw_text, cfg.thresholds):
        warnings.append("watermark_suspected: transcript contains a TTS watermark-like phrase")

    # --- Normalisasi ejaan OPSIONAL (setelah ASR; raw_text TIDAK diubah) --- #
    spelling_normalization: dict[str, Any] | None = None
    if cfg.spelling_normalization_enabled and asr_ok:
        spel = normalize_spelling(asr_result.raw_text, enabled=True)
        spelling_normalization = {
            "enabled": True,
            "profile_id": spel.profile_id,
            "normalized_text": spel.text,
            "changes": [
                {
                    "original": c.original,
                    "normalized": c.normalized,
                    "rule_id": c.rule_id,
                    "reason": c.reason,
                    "source": c.source,
                    "position": c.position,
                }
                for c in spel.changes
            ],
        }

    # --- Persist raw transcript (immutable) ------------------------------- #
    raw_text_path = None
    json_path = None
    out_dir: Path | None = None
    if persist and output_dir is not None:
        out_dir = Path(output_dir)
        raw_text_path = write_raw_transcript_text(
            asr_result.raw_text, out_dir / RAW_TRANSCRIPT_FILENAME,
            overwrite=overwrite, failed_error=(asr_result.error or None),
        )

    # --- Alignment + metrik + review (target dipakai SETELAH ASR) ---------- #
    alignment = {"status": "not_computed", "reason": "asr_failed"} if not asr_ok \
        else align_transcript(target_text=target_text, asr_result=asr_result,
                              thresholds=cfg.thresholds)

    review = build_review_flags(
        segments=asr_result.segments,
        alignment_items=alignment.get("words", []) if asr_ok else [],
        asr_warnings=warnings,
        audio_seconds=asr_result.audio_seconds,
        thresholds=cfg.thresholds,
    )
    review_dict = {
        "review_required": review.review_required,
        "items": [
            {"reason": it.reason, "detail": it.detail, "segment_id": it.segment_id,
             "word_index": it.word_index, "start_seconds": it.start_seconds,
             "end_seconds": it.end_seconds}
            for it in review.items
        ],
    }

    elapsed = time.perf_counter() - started
    duration = asr_result.audio_seconds
    text_match = alignment.get("wer") if alignment.get("status") == STATUS_COMPUTED else None

    audio_dict = {
        "source_filename": sanitize_filename(audio.name) if audio.name else None,
        "duration_seconds": audio_info.duration_seconds,
        "sample_rate_hz": audio_info.sample_rate_hz,
        "channels": audio_info.channels,
        "format": audio_info.format,
        "size_bytes": audio_info.size_bytes,
        "storage_ref": None,
        "compute_type": cfg.compute_type,
    }

    result_schema = build_result_schema(
        job_id=job_id,
        job_status="completed" if asr_ok else "failed",
        created_at=created_at,
        question_id=question_id,
        audio=audio_dict,
        asr_result=asr_result,
        applied_params=asr_result.applied_params,
        profile=cfg.asr_profile,
        raw_text_file=RAW_TRANSCRIPT_FILENAME if raw_text_path else None,
        reference=reference,
        alignment=alignment if asr_ok else {"status": "not_computed", "reason": "asr_failed"},
        review=review_dict if asr_ok else None,
        performance={
            "elapsed_seconds": elapsed,
            "audio_seconds": duration,
            "real_time_factor": (elapsed / duration) if duration else None,
            "peak_rss_mb": asr_result.peak_rss_mb,
        },
        errors=errors,
        warnings=warnings,
        text_match=text_match,
        spelling_normalization=spelling_normalization,
    )
    result_dict = result_schema.model_dump()

    if persist and out_dir is not None:
        json_path = write_json(result_dict, out_dir / "result.json", overwrite=overwrite)

    return ReadingResult(
        result=result_dict,
        output_dir=str(out_dir) if out_dir else None,
        raw_text_path=str(raw_text_path) if raw_text_path else None,
        json_path=str(json_path) if json_path else None,
        asr_ok=asr_ok,
    )
