"""Metrik WER, CER, dan statistik edit.

Aturan wajib (dari spesifikasi):
- WER = (S + D + I) / N, N = jumlah kata referensi setelah normalisasi.
- Jangan menghitung WER/CER bila target tidak valid -> status ``not_computed``.
- Referensi kosong (tanpa token) BUKAN nol otomatis; dibedakan dari "tidak
  tersedia".
- Hindari pembagian dengan nol.
- Jangan membulatkan nilai internal sebelum perhitungan selesai.
"""

from __future__ import annotations

from dataclasses import dataclass

from .alignment import (
    align_words,
    edit_counts,
    normalize_chars,
    normalize_tokens,
)
from .config import DEFAULT_NORMALIZATION, NormalizationProfile

STATUS_COMPUTED = "computed"
STATUS_NOT_COMPUTED = "not_computed"
STATUS_FAILED = "failed"

REASON_REFERENCE_NOT_PROVIDED = "reference_not_provided"
REASON_REFERENCE_INVALID = "reference_invalid"


@dataclass
class MetricsResult:
    status: str
    reason: str | None
    wer: float | None = None
    cer: float | None = None
    substitutions: int | None = None
    deletions: int | None = None
    insertions: int | None = None
    matches: int | None = None
    edit_distance: int | None = None
    reference_word_count: int | None = None
    transcript_word_count: int | None = None
    reference_char_count: int | None = None
    transcript_char_count: int | None = None


def levenshtein(seq_a, seq_b) -> int:
    """Jarak edit Levenshtein standar (O(n*m) memori baris)."""
    if len(seq_a) < len(seq_b):
        seq_a, seq_b = seq_b, seq_a
    previous = list(range(len(seq_b) + 1))
    for i, item_a in enumerate(seq_a, start=1):
        current = [i]
        for j, item_b in enumerate(seq_b, start=1):
            cost = 0 if item_a == item_b else 1
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + cost))
        previous = current
    return previous[-1]


def is_reference_valid(reference: str | None,
                       profile: NormalizationProfile | None = None) -> bool:
    """True bila referensi punya >= 1 token setelah normalisasi."""
    return len(normalize_tokens(reference, profile)) > 0


def calculate_metrics(reference: str | None, hypothesis: str | None,
                      profile: NormalizationProfile | None = None) -> MetricsResult:
    """Hitung WER/CER/S-D-I. Menghormati status not_computed/failed."""
    profile = profile or DEFAULT_NORMALIZATION

    if reference is None:
        return MetricsResult(status=STATUS_NOT_COMPUTED,
                             reason=REASON_REFERENCE_NOT_PROVIDED)

    ref_tokens = normalize_tokens(reference, profile)
    hyp_tokens = normalize_tokens(hypothesis, profile)

    if not ref_tokens:
        # Referensi ada tapi kosong setelah normalisasi -> tidak valid untuk WER.
        return MetricsResult(
            status=STATUS_NOT_COMPUTED,
            reason=REASON_REFERENCE_INVALID,
            reference_word_count=0,
            transcript_word_count=len(hyp_tokens),
        )

    ops = align_words(reference, hypothesis, profile)
    counts = edit_counts(ops)
    s, d, i_ = counts["substitutions"], counts["deletions"], counts["insertions"]
    n_ref = len(ref_tokens)
    edit_distance = s + d + i_
    wer = edit_distance / n_ref

    ref_chars = normalize_chars(reference, profile)
    hyp_chars = normalize_chars(hypothesis, profile)
    cer = levenshtein(ref_chars, hyp_chars) / len(ref_chars) if ref_chars else None

    return MetricsResult(
        status=STATUS_COMPUTED,
        reason=None,
        wer=wer,
        cer=cer,
        substitutions=s,
        deletions=d,
        insertions=i_,
        matches=counts["matches"],
        edit_distance=edit_distance,
        reference_word_count=n_ref,
        transcript_word_count=len(hyp_tokens),
        reference_char_count=len(ref_chars),
        transcript_char_count=len(hyp_chars),
    )
