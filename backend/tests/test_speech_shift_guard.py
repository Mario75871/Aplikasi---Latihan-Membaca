"""Test penjaga pergeseran `model_probability` (Fase 1B).

Prompt Fase 1B meminta uji risiko: `align_transcript` memasangkan probability ke
kata transkrip BERURUTAN, sedangkan token alignment berasal dari raw_text yang
dinormalisasi. Bila satu kata ASR pecah jadi dua token (mis. tanda hubung),
probability bisa bergeser ke kata yang salah.

Keputusan (aturan keras): framework TIDAK diubah. Bila terbukti bergeser, adapter
(`services/speech.py`) menandai kata berisiko sebagai perlu diperiksa
(`alignment_ambiguous`) dan temuan dicatat di INTEGRATION_NOTES.md.
"""
from reading_framework.alignment import normalize_tokens
from reading_framework.asr_engine import ASRResult, SegmentStamp, WordStamp
from reading_framework.pipeline import align_transcript

from services.speech import apply_alignment_shift_guard, _count_segment_words


def _make_asr(raw_text: str, seg_words: list[str], probs: list[float]) -> ASRResult:
    stamps = [
        WordStamp(word=f" {w}", start=i * 0.3, end=(i + 1) * 0.3, probability=probs[i])
        for i, w in enumerate(seg_words)
    ]
    return ASRResult(
        audio_path="demo",
        audio_seconds=len(seg_words) * 0.3,
        language_requested="id",
        language="id",
        language_probability=1.0,
        segments=[
            SegmentStamp(id=1, start=0.0, end=len(seg_words) * 0.3,
                         text=raw_text, words=stamps)
        ],
        raw_text=raw_text,
        applied_params={},
    )


def _framework_result(alignment: dict, asr: ASRResult) -> dict:
    """Bentuk minimal seperti result.result framework (untuk penjaga)."""
    return {
        "transcript": {
            "raw_text": asr.raw_text,
            "segments": [
                {"segment_id": s.id, "words": [{"text": w.word} for w in s.words]}
                for s in asr.segments
            ],
        },
        "alignment": alignment,
    }


def test_shift_is_real_when_asr_word_splits_into_two_tokens():
    """Bukti risiko: 'ke-pasar' (1 kata ASR) → 2 token → probability bergeser.

    Ini mendokumentasikan PERILAKU FRAMEWORK yang tidak kita ubah.
    """
    target = "adik pergi ke pasar itu"
    asr = _make_asr(
        raw_text="adik pergi ke-pasar itu",
        seg_words=["adik", "pergi", "ke-pasar", "itu"],
        probs=[0.91, 0.95, 0.20, 0.99],
    )
    # Token transkrip setelah normalisasi = 5, kata segmen = 4 → tidak cocok.
    assert len(normalize_tokens(asr.raw_text)) == 5
    assert _count_segment_words(_framework_result({}, asr)) == 4

    alignment = align_transcript(target_text=target, asr_result=asr)
    probs = [w["model_probability"] for w in alignment["words"]]
    # 0.99 (dari 'itu') salah terpasang ke 'pasar', dan 'itu' kehilangan probability.
    assert probs[3] == 0.99, "Pergeseran tidak terjadi — perbarui catatan bila framework berubah."
    assert probs[4] is None


def test_guard_marks_words_when_counts_mismatch():
    """Penjaga menandai kata berisiko 'alignment_ambiguous' saat jumlah tidak cocok."""
    target = "adik pergi ke pasar itu"
    asr = _make_asr(
        raw_text="adik pergi ke-pasar itu",
        seg_words=["adik", "pergi", "ke-pasar", "itu"],
        probs=[0.91, 0.95, 0.20, 0.99],
    )
    alignment = align_transcript(target_text=target, asr_result=asr)
    guarded = apply_alignment_shift_guard(alignment["words"], _framework_result(alignment, asr))

    flagged = [w for w in guarded if "alignment_ambiguous" in (w.get("review_reasons") or [])]
    assert len(flagged) >= 1
    assert all(w.get("review_required") is True for w in flagged)
    # framework_result tidak diubah: item asli tanpa flag
    assert not any("alignment_ambiguous" in (w.get("review_reasons") or []) for w in alignment["words"])


def test_guard_is_noop_when_counts_match():
    """Tanpa pecahan token, penjaga tidak menandai apa pun (hindari false positive)."""
    target = "ibu pergi ke pasar"
    asr = _make_asr(
        raw_text="ibu pergi ke pasar",
        seg_words=["ibu", "pergi", "ke", "pasar"],
        probs=[0.9, 0.9, 0.9, 0.34],
    )
    alignment = align_transcript(target_text=target, asr_result=asr)
    guarded = apply_alignment_shift_guard(alignment["words"], _framework_result(alignment, asr))
    assert guarded == alignment["words"]
    assert not any(w.get("review_reasons") for w in guarded)
