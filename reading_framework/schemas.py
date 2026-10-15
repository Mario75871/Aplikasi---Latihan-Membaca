"""Kontrak JSON aplikasi (schema_version "1.0.0") sebagai model Pydantic.

Kelompok field: job, audio, asr, transcript, reference, alignment, review,
assessment, performance, errors, warnings.

Aturan penting:
- ``null`` = data belum tersedia/tidak dapat dihitung; BUKAN ``0``/``[]``.
- ``reference.used_during_asr`` selalu ``False`` untuk raw ASR.
- ``transcript.raw_text`` immutable setelah alignment.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import SCHEMA_VERSION

AlignmentStatus = Literal["computed", "not_computed", "failed"]
ReviewStatus = Literal["not_reviewed", "pending", "reviewed"]
AssessmentStatus = Literal["not_assessed", "assessed"]
Operation = Literal["match", "substitution", "deletion", "insertion"]


class JobInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    status: Literal["created", "processing", "completed", "failed"]
    created_at: str | None = None
    question_id: str | None = None


class AudioInfoSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_filename: str | None = None
    duration_seconds: float | None = None
    sample_rate_hz: int | None = None
    channels: int | None = None
    format: str | None = None
    size_bytes: int | None = None
    storage_ref: str | None = None


class DecodingInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    beam_size: int | None = None
    temperature: float | list[float] | None = None
    vad_filter: bool | None = None
    word_timestamps: bool | None = None
    initial_prompt_used: bool = False
    hotwords_used: bool = False


class ASRInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    engine: str = "faster-whisper"
    engine_version: str | None = None
    model: str | None = None
    compute_type: str | None = None
    profile: str = "raw_reading"
    language_requested: str | None = None
    language_detected: str | None = None
    decoding: DecodingInfo = Field(default_factory=DecodingInfo)


class WordSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    word_index: int
    text: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    model_probability: float | None = None


class SegmentSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    segment_id: int
    start_seconds: float | None = None
    end_seconds: float | None = None
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    compression_ratio: float | None = None
    words: list[WordSchema] = Field(default_factory=list)


class SpellingChangeSchema(BaseModel):
    """Satu perubahan ejaan hasil tahap normalisasi (audit trail)."""

    model_config = ConfigDict(extra="forbid")
    original: str
    normalized: str
    rule_id: str
    reason: str
    source: str
    position: int


class TranscriptSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_text: str | None = None
    raw_text_file: str | None = None
    #: OPSIONAL: representasi pembanding hasil normalisasi ejaan. BUKAN transkrip
    #: mentah dan BUKAN bukti bacaan benar. ``None`` bila tahap tidak dijalankan.
    normalized_text: str | None = None
    spelling_normalization_enabled: bool = False
    spelling_normalization_profile: str | None = None
    spelling_changes: list[SpellingChangeSchema] | None = None
    segments: list[SegmentSchema] = Field(default_factory=list)


class ReferenceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provided: bool = False
    target_text: str | None = None
    normalized_text: str | None = None
    source_id: str | None = None
    source_type: str | None = None
    source_version: str | None = None
    used_during_asr: bool = False


class AlignmentItemSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    position: int
    reference_word: str | None = None
    transcript_word: str | None = None
    operation: Operation
    start_seconds: float | None = None
    end_seconds: float | None = None
    model_probability: float | None = None
    segment_id: int | None = None
    review_required: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    review_status: Literal["none", "pending", "reviewed"] = "none"


class AlignmentSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: AlignmentStatus = "not_computed"
    reason: str | None = None
    normalization_profile: str = "id_reading_v1"
    reference_word_count: int | None = None
    transcript_word_count: int | None = None
    matches: int | None = None
    substitutions: int | None = None
    deletions: int | None = None
    insertions: int | None = None
    edit_distance: int | None = None
    wer: float | None = None
    cer: float | None = None
    words: list[AlignmentItemSchema] = Field(default_factory=list)


class ReviewItemSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str
    detail: str = ""
    segment_id: int | None = None
    word_index: int | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None


class ReviewSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ReviewStatus = "not_reviewed"
    review_required: bool = False
    items: list[ReviewItemSchema] = Field(default_factory=list)


class AssessmentSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: AssessmentStatus = "not_assessed"
    text_match: float | None = None
    reading_correctness_confirmed: bool = False
    pronunciation_verified: bool = False
    human_reviewed: bool = False


class PerformanceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    elapsed_seconds: float | None = None
    audio_seconds: float | None = None
    real_time_factor: float | None = None
    peak_rss_mb: float | None = None


class ReadingResultSchema(BaseModel):
    """Kontrak lengkap hasil satu pekerjaan tes membaca."""

    model_config = ConfigDict(extra="forbid")
    schema_version: str = SCHEMA_VERSION
    job: JobInfo
    audio: AudioInfoSchema = Field(default_factory=AudioInfoSchema)
    asr: ASRInfo = Field(default_factory=ASRInfo)
    transcript: TranscriptSchema = Field(default_factory=TranscriptSchema)
    reference: ReferenceSchema = Field(default_factory=ReferenceSchema)
    alignment: AlignmentSchema = Field(default_factory=AlignmentSchema)
    review: ReviewSchema = Field(default_factory=ReviewSchema)
    assessment: AssessmentSchema = Field(default_factory=AssessmentSchema)
    performance: PerformanceSchema = Field(default_factory=PerformanceSchema)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def json_schema() -> dict[str, Any]:
    """JSON Schema (draft 2020-12) untuk dokumentasi & validasi eksternal."""
    return ReadingResultSchema.model_json_schema()
