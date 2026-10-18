"""Normalisasi teks deterministik untuk perbandingan (alignment & metrik).

PENTING: modul ini TIDAK pernah mengubah teks mentah yang disimpan. Ia hanya
menghasilkan representasi pembanding. Profil normalisasi diberi id + versi agar
hasil lama dapat direproduksi.
"""

from __future__ import annotations

import re
import unicodedata

from .config import DEFAULT_NORMALIZATION, NormalizationProfile

#: Tanda baca default yang dibuang. Apostrof SENGAJA tidak dimasukkan agar
#: bentuk seperti "don't" tidak pecah menjadi "don t".
_DEFAULT_PUNCT = "!\"#$%&()*+,-./:;<=>?@[\\]^_`{|}~"
_APOSTROPHES = "\u2018\u2019\u02bc\u2032"  # ' ' ʼ ′


def _punct_class(profile: NormalizationProfile) -> str:
    chars = _DEFAULT_PUNCT + profile.extra_punctuation
    return re.escape(chars)


def normalize_for_alignment(text: str | None,
                            profile: NormalizationProfile | None = None) -> str:
    """Normalisasi teks untuk pembanding. Deterministik & terdokumentasi."""
    profile = profile or DEFAULT_NORMALIZATION
    if text is None:
        return ""

    out = text

    if profile.normalize_apostrophes:
        for ap in _APOSTROPHES:
            out = out.replace(ap, "'")

    # Unicode NFKC menyatukan bentuk kompatibel (mis. ligatur, lebar penuh).
    out = unicodedata.normalize("NFKC", out)

    if profile.lowercase:
        out = out.casefold()

    if profile.strip_punctuation:
        # Buang tanda baca; pertahankan apostrof internal kata (mis. "don't").
        out = re.sub(rf"[{_punct_class(profile)}]", " ", out)

    # Buang karakter kontrol / tak terlihat.
    out = "".join(ch if ch.isprintable() or ch.isspace() else " " for ch in out)

    if profile.collapse_whitespace:
        out = re.sub(r"\s+", " ", out)

    return out.strip() if profile.strip else out


def normalize_tokens(text: str | None,
                     profile: NormalizationProfile | None = None) -> list[str]:
    """Normalisasi lalu tokenisasi per kata (spasi-based)."""
    normalized = normalize_for_alignment(text, profile)
    return normalized.split() if normalized else []


def normalize_chars(text: str | None,
                    profile: NormalizationProfile | None = None) -> str:
    """Normalisasi untuk CER: tanpa spasi (perbandingan karakter)."""
    return normalize_for_alignment(text, profile).replace(" ", "")


# --------------------------------------------------------------------------- #
# Per-kata alignment (dynamic programming / Levenshtein)
# --------------------------------------------------------------------------- #

OPERATION_MATCH = "match"
OPERATION_SUBSTITUTION = "substitution"
OPERATION_DELETION = "deletion"
OPERATION_INSERTION = "insertion"

VALID_OPERATIONS = (
    OPERATION_MATCH, OPERATION_SUBSTITUTION,
    OPERATION_DELETION, OPERATION_INSERTION,
)


def _dp_table(ref: list[str], hyp: list[str]) -> list[list[int]]:
    n, m = len(ref), len(hyp)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i
    for j in range(1, m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,          # deletion
                dp[i][j - 1] + 1,          # insertion
                dp[i - 1][j - 1] + cost,   # match / substitution
            )
    return dp


def align_words(reference: str, hypothesis: str,
                profile: NormalizationProfile | None = None) -> list[tuple[str, str | None, str | None]]:
    """Align target <-> transkrip per kata.

    Mengembalikan daftar operasi ``(operation, reference_word|None,
    transcript_word|None)`` dengan urutan terjaga. Ties diselesaikan dengan
    prioritas substitution > deletion > insertion agar deterministik.
    """
    profile = profile or DEFAULT_NORMALIZATION
    ref = normalize_tokens(reference, profile)
    hyp = normalize_tokens(hypothesis, profile)
    n, m = len(ref), len(hyp)
    dp = _dp_table(ref, hyp)

    ops: list[tuple[str, str | None, str | None]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref[i - 1] == hyp[j - 1] and dp[i][j] == dp[i - 1][j - 1]:
            ops.append((OPERATION_MATCH, ref[i - 1], hyp[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            ops.append((OPERATION_SUBSTITUTION, ref[i - 1], hyp[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append((OPERATION_DELETION, ref[i - 1], None))
            i -= 1
        else:
            ops.append((OPERATION_INSERTION, None, hyp[j - 1]))
            j -= 1
    ops.reverse()
    return ops


def edit_counts(ops: list[tuple[str, str | None, str | None]]) -> dict[str, int]:
    """Hitung ringkasan operasi dari hasil ``align_words``."""
    counts = {"matches": 0, "substitutions": 0, "deletions": 0, "insertions": 0}
    key_map = {
        OPERATION_MATCH: "matches",
        OPERATION_SUBSTITUTION: "substitutions",
        OPERATION_DELETION: "deletions",
        OPERATION_INSERTION: "insertions",
    }
    for op, _ref, _hyp in ops:
        counts[key_map[op]] += 1
    return counts
