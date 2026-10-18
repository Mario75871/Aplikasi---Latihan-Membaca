"""Review flagging tests: sinyal pemeriksaan, bukan vonis."""

from __future__ import annotations

from reading_framework.asr_engine import SegmentStamp, WordStamp
from reading_framework.config import ReviewThresholds
from reading_framework.review_flags import (
    REASON_LOW_MODEL_PROBABILITY,
    REASON_MISSING_WORD_TIMESTAMP,
    REASON_REFERENCE_TRANSCRIPT_MISMATCH,
    REASON_SUSPICIOUS_SEGMENT_METADATA,
    REASON_ZERO_DURATION_WORD,
    build_review_flags,
    detect_watermark,
)


def _seg(sid, words, logprob=None, nsp=None, cr=None):
    return SegmentStamp(id=sid, start=0.0, end=1.0, text="x",
                        avg_logprob=logprob, no_speech_prob=nsp, compression_ratio=cr,
                        words=words)


def test_low_probability_flagged():
    seg = _seg(1, [WordStamp(" pasap", 0.0, 0.5, 0.4)])
    review = build_review_flags(segments=[seg])
    assert any(i.reason == REASON_LOW_MODEL_PROBABILITY for i in review.items)


def test_missing_timestamp_flagged():
    seg = _seg(1, [WordStamp(" x", None, None, 0.9)])
    review = build_review_flags(segments=[seg])
    assert any(i.reason == REASON_MISSING_WORD_TIMESTAMP for i in review.items)


def test_zero_duration_word_flagged():
    seg = _seg(1, [WordStamp(" x", 1.0, 1.0, 0.9)])
    review = build_review_flags(segments=[seg])
    assert any(i.reason == REASON_ZERO_DURATION_WORD for i in review.items)


def test_suspicious_repeated_segment_metadata_flagged_not_modified():
    seg1 = _seg(1, [WordStamp(" a", 0.0, 0.5, 0.9)], logprob=-0.5, nsp=0.1, cr=1.2)
    seg2 = _seg(2, [WordStamp(" b", 0.6, 1.0, 0.9)], logprob=-0.5, nsp=0.1, cr=1.2)
    review = build_review_flags(segments=[seg1, seg2])
    assert any(i.reason == REASON_SUSPICIOUS_SEGMENT_METADATA for i in review.items)
    # bukti tidak diubah
    assert seg2.avg_logprob == -0.5


def test_mismatch_items_flagged():
    items = [{"operation": "substitution", "reference_word": "a",
              "transcript_word": "b", "segment_id": 1}]
    review = build_review_flags(segments=[], alignment_items=items)
    assert any(i.reason == REASON_REFERENCE_TRANSCRIPT_MISMATCH for i in review.items)


def test_no_flags_when_clean():
    seg = _seg(1, [WordStamp(" pasar", 0.0, 0.5, 0.99)])
    review = build_review_flags(segments=[seg])
    assert review.review_required is False
    assert review.items == []


def test_watermark_detected_but_not_removed():
    assert detect_watermark("... Terima kasih.") is True
    assert detect_watermark("ibu pergi ke pasar") is False


def test_configurable_threshold():
    seg = _seg(1, [WordStamp(" x", 0.0, 0.5, 0.6)])
    strict = build_review_flags(segments=[seg],
                                thresholds=ReviewThresholds(low_word_probability=0.8))
    assert any(i.reason == REASON_LOW_MODEL_PROBABILITY for i in strict.items)
