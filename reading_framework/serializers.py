"""Serializers: membentuk JSON kontrak dari hasil pipeline NYATA.

Tidak pernah mengisi nilai contoh sebagai data nyata. Data yang belum
dihitung/tidak tersedia tetap ``null``.
"""

from __future__ import annotations

from typing import Any

from .alignment import (
    OPERATION_DELETION,
    OPERATION_INSERTION,
    OPERATION_MATCH,
    OPERATION_SUBSTITUTION,
)
from .config import SCHEMA_VERSION
from .schemas import (
    AlignmentItemSchema,
    AlignmentSchema,
    ASRInfo,
    AudioInfoSchema,
    AssessmentSchema,
    DecodingInfo,
    JobInfo,
    PerformanceSchema,
    ReadingResultSchema,
    ReferenceSchema,
    ReviewItemSchema,
    ReviewSchema,
    SegmentSchema,
    SpellingChangeSchema,
    TranscriptSchema,
    WordSchema,
)

_PROMPT_KEYS = ("initial_prompt", "hotwords", "prefix")


def _prompt_used(params: dict[str, Any], key: str) -> bool:
    return params.get(key) is not None


def build_decoding_info(applied_params: dict[str, Any]) -> DecodingInfo:
    return DecodingInfo(
        beam_size=applied_params.get("beam_size"),
        temperature=applied_params.get("temperature"),
        vad_filter=applied_params.get("vad_filter"),
        word_timestamps=applied_params.get("word_timestamps"),
        initial_prompt_used=_prompt_used(applied_params, "initial_prompt")
        or _prompt_used(applied_params, "prefix"),
        hotwords_used=_prompt_used(applied_params, "hotwords"),
    )


def build_segments_schema(segments: list) -> list[SegmentSchema]:
    out: list[SegmentSchema] = []
    for seg in segments or []:
        words = [
            WordSchema(
                word_index=idx,
                text=getattr(w, "word", ""),
                start_seconds=getattr(w, "start", None),
                end_seconds=getattr(w, "end", None),
                model_probability=getattr(w, "probability", None),
            )
            for idx, w in enumerate(getattr(seg, "words", []) or [])
        ]
        out.append(SegmentSchema(
            segment_id=int(getattr(seg, "id", 0)),
            start_seconds=getattr(seg, "start", None),
            end_seconds=getattr(seg, "end", None),
            text=getattr(seg, "text", ""),
            avg_logprob=getattr(seg, "avg_logprob", None),
            no_speech_prob=getattr(seg, "no_speech_prob", None),
            compression_ratio=getattr(seg, "compression_ratio", None),
            words=words,
        ))
    return out


def build_alignment_schema(alignment: dict[str, Any] | None) -> AlignmentSchema:
    """Bangun bagian alignment dari dict pipeline. Menghormati status."""
    if not alignment:
        return AlignmentSchema(status="not_computed", reason="not_computed")

    status = alignment.get("status", "not_computed")
    if status != "computed":
        return AlignmentSchema(
            status=status,
            reason=alignment.get("reason"),
            normalization_profile=alignment.get("normalization_profile",
                                                 "id_reading_v1"),
        )

    items = [
        AlignmentItemSchema(
            position=it["position"],
            reference_word=it.get("reference_word"),
            transcript_word=it.get("transcript_word"),
            operation=it["operation"],
            start_seconds=it.get("start_seconds"),
            end_seconds=it.get("end_seconds"),
            model_probability=it.get("model_probability"),
            segment_id=it.get("segment_id"),
            review_required=it.get("review_required", False),
            review_reasons=it.get("review_reasons", []),
            review_status=it.get("review_status", "none"),
        )
        for it in alignment.get("words", [])
    ]
    return AlignmentSchema(
        status="computed",
        reason=None,
        normalization_profile=alignment.get("normalization_profile",
                                             "id_reading_v1"),
        reference_word_count=alignment.get("reference_word_count"),
        transcript_word_count=alignment.get("transcript_word_count"),
        matches=alignment.get("matches"),
        substitutions=alignment.get("substitutions"),
        deletions=alignment.get("deletions"),
        insertions=alignment.get("insertions"),
        edit_distance=alignment.get("edit_distance"),
        wer=alignment.get("wer"),
        cer=alignment.get("cer"),
        words=items,
    )


def build_review_schema(review: dict[str, Any] | None) -> ReviewSchema:
    if not review:
        return ReviewSchema(status="not_reviewed", review_required=False)
    items = [
        ReviewItemSchema(
            reason=it["reason"],
            detail=it.get("detail", ""),
            segment_id=it.get("segment_id"),
            word_index=it.get("word_index"),
            start_seconds=it.get("start_seconds"),
            end_seconds=it.get("end_seconds"),
        )
        for it in review.get("items", [])
    ]
    return ReviewSchema(
        status="pending" if items else "not_reviewed",
        review_required=bool(items),
        items=items,
    )


def build_result_schema(
    *,
    job_id: str,
    job_status: str = "completed",
    created_at: str | None = None,
    question_id: str | None = None,
    audio: dict[str, Any] | None = None,
    asr_result=None,
    applied_params: dict[str, Any] | None = None,
    profile: str = "raw_reading",
    raw_text_file: str | None = None,
    reference: dict[str, Any] | None = None,
    alignment: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
    performance: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    text_match: float | None = None,
    spelling_normalization: dict[str, Any] | None = None,
) -> ReadingResultSchema:
    """Rakit kontrak lengkap dari hasil pipeline nyata.

    ``spelling_normalization`` opsional (default ``None``): bila diisi, memuat
    ``normalized_text``/``profile_id``/``changes`` hasil tahap normalisasi ejaan
    yang TERPISAH dari ``raw_text``.
    """
    audio = audio or {}
    applied = applied_params or (getattr(asr_result, "applied_params", {}) or {})

    spel = spelling_normalization or {}
    spel_changes = spel.get("changes")
    spel_schema = (
        [
            SpellingChangeSchema(
                original=c["original"],
                normalized=c["normalized"],
                rule_id=c["rule_id"],
                reason=c["reason"],
                source=c["source"],
                position=c["position"],
            )
            for c in spel_changes
        ]
        if spel_changes is not None
        else None
    )

    return ReadingResultSchema(
        schema_version=SCHEMA_VERSION,
        job=JobInfo(job_id=job_id, status=job_status, created_at=created_at,
                    question_id=question_id),
        audio=AudioInfoSchema(
            source_filename=audio.get("source_filename"),
            duration_seconds=audio.get("duration_seconds"),
            sample_rate_hz=audio.get("sample_rate_hz"),
            channels=audio.get("channels"),
            format=audio.get("format"),
            size_bytes=audio.get("size_bytes"),
            storage_ref=audio.get("storage_ref"),
        ),
        asr=ASRInfo(
            engine=getattr(asr_result, "engine", "faster-whisper") if asr_result else "faster-whisper",
            engine_version=getattr(asr_result, "engine_version", None) if asr_result else None,
            model=getattr(asr_result, "model", None) if asr_result else None,
            compute_type=audio.get("compute_type") or (getattr(asr_result, "compute_type", None) if asr_result else None),
            profile=profile,
            language_requested=getattr(asr_result, "language_requested", None) if asr_result else None,
            language_detected=getattr(asr_result, "language", None) if asr_result else None,
            decoding=build_decoding_info(applied),
        ),
        transcript=TranscriptSchema(
            raw_text=getattr(asr_result, "raw_text", None) if asr_result else None,
            raw_text_file=raw_text_file,
            normalized_text=spel.get("normalized_text"),
            spelling_normalization_enabled=bool(spel.get("enabled", False)),
            spelling_normalization_profile=spel.get("profile_id"),
            spelling_changes=spel_schema,
            segments=build_segments_schema(getattr(asr_result, "segments", []) if asr_result else []),
        ),
        reference=ReferenceSchema(
            provided=bool(reference and reference.get("provided")),
            target_text=(reference or {}).get("target_text"),
            normalized_text=(reference or {}).get("normalized_text"),
            source_id=(reference or {}).get("source_id"),
            source_type=(reference or {}).get("source_type"),
            source_version=(reference or {}).get("source_version"),
            used_during_asr=False,
        ),
        alignment=build_alignment_schema(alignment),
        review=build_review_schema(review),
        assessment=AssessmentSchema(
            status="not_assessed",
            text_match=text_match,
            reading_correctness_confirmed=False,
            pronunciation_verified=False,
            human_reviewed=False,
        ),
        performance=PerformanceSchema(
            elapsed_seconds=(performance or {}).get("elapsed_seconds"),
            audio_seconds=(performance or {}).get("audio_seconds"),
            real_time_factor=(performance or {}).get("real_time_factor"),
            peak_rss_mb=(performance or {}).get("peak_rss_mb"),
        ),
        errors=errors or [],
        warnings=warnings or [],
    )
