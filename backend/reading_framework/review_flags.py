"""Review flagging: sinyal pemeriksaan, BUKAN vonis.

Membedakan dengan jelas: bukti ASR, sinyal "perlu diperiksa", hasil
perbandingan tekstual, keputusan manusia, dan penilaian yang sudah diverifikasi.

Review flags TIDAK menyimpulkan kesalahan membaca. Confidence bukan
probabilitas terkalibrasi bahwa anak membaca dengan benar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .alignment import (
    OPERATION_DELETION,
    OPERATION_INSERTION,
    OPERATION_SUBSTITUTION,
)
from .config import ReviewThresholds
from .metrics import MetricsResult

# --- kategori review_reasons (stabil & terdokumentasi) --------------------- #
REASON_LOW_MODEL_PROBABILITY = "low_model_probability"
REASON_REFERENCE_TRANSCRIPT_MISMATCH = "reference_transcript_mismatch"
REASON_MISSING_WORD_TIMESTAMP = "missing_word_timestamp"
REASON_INVALID_WORD_TIMESTAMP = "invalid_word_timestamp"
REASON_ZERO_DURATION_WORD = "zero_duration_word"
REASON_SUSPICIOUS_SEGMENT_METADATA = "suspicious_segment_metadata"
REASON_ASR_PROCESSING_WARNING = "asr_processing_warning"
REASON_ALIGNMENT_AMBIGUOUS = "alignment_ambiguous"
REASON_WATERMARK_SUSPECTED = "watermark_suspected"
REASON_MANUAL_REVIEW_REQUESTED = "manual_review_requested"

REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_NONE = "none"


@dataclass
class ReviewItem:
    reason: str
    detail: str = ""
    segment_id: int | None = None
    word_index: int | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None


@dataclass
class ReviewResult:
    review_required: bool = False
    items: list[ReviewItem] = field(default_factory=list)

    def add(self, reason: str, detail: str = "", **kw) -> None:
        self.items.append(ReviewItem(reason=reason, detail=detail, **kw))
        self.review_required = True


def build_review_flags(
    *,
    segments: list,
    alignment_items: list[dict] | None = None,
    metrics: MetricsResult | None = None,
    asr_warnings: list[str] | None = None,
    audio_seconds: float | None = None,
    thresholds: ReviewThresholds | None = None,
) -> ReviewResult:
    """Bangun daftar review flag dari bukti nyata (tanpa mengarang data)."""
    th = thresholds or ReviewThresholds()
    review = ReviewResult()

    # --- sinyal tingkat kata: probability rendah / timestamp hilang/aneh --- #
    for seg in segments or []:
        for w_idx, w in enumerate(getattr(seg, "words", []) or []):
            start = getattr(w, "start", None)
            end = getattr(w, "end", None)
            prob = getattr(w, "probability", None)

            if start is None or end is None:
                review.add(REASON_MISSING_WORD_TIMESTAMP,
                           f"word {getattr(w, 'word', '')!r} has no timestamp",
                           segment_id=getattr(seg, "id", None), word_index=w_idx)
                continue

            if start < 0 or (audio_seconds is not None and start > audio_seconds + 0.5):
                review.add(REASON_INVALID_WORD_TIMESTAMP,
                           f"word start {start} outside [0, {audio_seconds}]",
                           segment_id=getattr(seg, "id", None), word_index=w_idx,
                           start_seconds=start, end_seconds=end)

            if (end - start) <= th.zero_duration:
                review.add(REASON_ZERO_DURATION_WORD,
                           f"word {getattr(w, 'word', '')!r} has zero/non-positive duration",
                           segment_id=getattr(seg, "id", None), word_index=w_idx,
                           start_seconds=start, end_seconds=end)

            if prob is not None and prob < th.low_word_probability:
                review.add(REASON_LOW_MODEL_PROBABILITY,
                           f"word {getattr(w, 'word', '')!r} probability {prob:.3f}"
                           f" < {th.low_word_probability}",
                           segment_id=getattr(seg, "id", None), word_index=w_idx,
                           start_seconds=start, end_seconds=end)

    # --- sinyal tingkat segmen: metadata mencurigakan ---------------------- #
    _flag_suspicious_segment_metadata(segments or [], review, th)

    # --- mismatch alignment ------------------------------------------------ #
    for item in alignment_items or []:
        if item.get("operation") in (OPERATION_SUBSTITUTION, OPERATION_DELETION,
                                     OPERATION_INSERTION):
            review.add(REASON_REFERENCE_TRANSCRIPT_MISMATCH,
                       f"{item.get('operation')}: ref={item.get('reference_word')!r} "
                       f"hyp={item.get('transcript_word')!r}",
                       segment_id=item.get("segment_id"),
                       start_seconds=item.get("start_seconds"),
                       end_seconds=item.get("end_seconds"))

    # --- warning dari proses ASR ------------------------------------------ #
    for warning in asr_warnings or []:
        review.add(REASON_ASR_PROCESSING_WARNING, warning)

    return review


def _flag_suspicious_segment_metadata(segments: list, review: ReviewResult,
                                      th: ReviewThresholds) -> None:
    """Tandai segmen dengan metadata identik berulang (temuan audit lama).

    faster-whisper dapat meng-copy avg_logprob/no_speech_prob/compression_ratio
    dari window pertama ke beberapa segmen. Ini bukan bukti bug di kode kita,
    tetapi layak diperiksa -> flag, jangan ubah data.
    """
    seen: dict[tuple, int] = {}
    for seg in segments:
        key = (
            getattr(seg, "avg_logprob", None),
            getattr(seg, "no_speech_prob", None),
            getattr(seg, "compression_ratio", None),
        )
        if all(v is None for v in key):
            continue
        if key in seen:
            review.add(REASON_SUSPICIOUS_SEGMENT_METADATA,
                       f"segment metadata identical to segment id {seen[key]} "
                       "(possibly copied by the engine; verify)",
                       segment_id=getattr(seg, "id", None))
        else:
            seen[key] = getattr(seg, "id", None)


def detect_watermark(text: str | None, thresholds: ReviewThresholds | None = None) -> bool:
    """Deteksi dugaan watermark TTS (mis. 'terima kasih').

    Hanya MENANDAI; tidak menghapus apa pun dari transkrip.
    """
    th = thresholds or ReviewThresholds()
    if not text:
        return False
    low = text.casefold()
    return any(p.casefold() in low for p in th.watermark_phrases)
