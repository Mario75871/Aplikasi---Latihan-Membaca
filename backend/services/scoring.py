"""Model #2 — Penilaian Kata dari output Framework (Fase 1B).

Menerima alignment.words[] dari framework (Model #1), lalu menentukan per kata:
- Dicoba dibaca atau tidak (D1: attempted)
- Correct atau Incorrect (D5, D10, D11)
- Alasan (reason) untuk traceability

Aturan penilaian (PRD F-06 + KEPUTUSAN):

D1: Kata yang dicoba dibaca
  - operation = match atau substitution → dicoba (attempted=True)
  - operation = deletion (kata terlewat) → tidak dicoba (attempted=False)
  - operation = insertion (kata tambahan) → diabaikan
  - Total Words Read = jumlah kata reference yang dicoba

D10: Threshold confidence
  - match + model_probability > 0.5 → Correct
  - match + model_probability ≤ 0.5 → Incorrect (kasus "pasar" 0.34)
  - substitution → Incorrect (default)

D5: Proper noun exception
  - Bila reference_word ada di proper_nouns list (normalized, case-insensitive)
    DAN operation = match atau substitution → Correct
  - Contoh: "boni" → "bonnie" (substitution) + proper_nouns=["boni"] → Correct

D11: model_probability = null
  - Perlakukan sebagai Incorrect dengan reason="probability_unavailable"
  - Tandai review_required=True

D2 (integrasi #2): kata bertanda pergeseran (alignment_ambiguous)
  - Bila "alignment_ambiguous" ada di review_reasons → paksa is_correct=False
    (attempted tetap True). Konservatif: kata tak dipercaya tidak menaikkan skor.
    review_reasons tetap memuat penanda agar UI menampilkan "perlu diperiksa".

Output:
  - Correct Words = jumlah kata dengan is_correct=True
  - Incorrect Words = attempted - correct
  - Total Words Read = attempted
  - Accuracy = Correct / Total Words Read × 100 (0 bila penyebut 0)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Threshold confidence (D10)
CONFIDENCE_THRESHOLD = 0.5


def _normalize_for_proper_noun(word: str) -> str:
    """Normalisasi untuk pencocokan proper noun (case-insensitive, alphanumeric)."""
    return "".join(ch for ch in word.lower() if ch.isalnum())


@dataclass
class ScoredWord:
    """Skor per kata dengan traceability."""
    position: int
    reference_word: Optional[str]
    transcript_word: Optional[str]
    confidence: Optional[float]
    attempted: bool  # D1: dicoba dibaca
    is_correct: bool
    is_proper_noun: bool = False
    reason: str = ""  # D10: traceability
    review_reasons: list[str] = field(default_factory=list)
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None


@dataclass
class ScoringResult:
    """Hasil penilaian seluruh kata."""
    words: list[ScoredWord] = field(default_factory=list)

    @property
    def total_words_read(self) -> int:
        """D1: jumlah kata reference yang dicoba dibaca."""
        return sum(1 for w in self.words if w.attempted)

    @property
    def correct_words(self) -> int:
        return sum(1 for w in self.words if w.attempted and w.is_correct)

    @property
    def incorrect_words(self) -> int:
        return sum(1 for w in self.words if w.attempted and not w.is_correct)


def score_word(
    position: int,
    reference_word: Optional[str],
    transcript_word: Optional[str],
    operation: str,
    model_probability: Optional[float],
    proper_nouns: list[str],
    review_reasons: list[str],
    start_seconds: Optional[float] = None,
    end_seconds: Optional[float] = None,
) -> Optional[ScoredWord]:
    """Menilai satu kata berdasarkan aturan D1, D5, D10, D11.
    
    Args:
        position: urutan kata
        reference_word: kata di teks acuan (null untuk insertion)
        transcript_word: kata di transkrip (null untuk deletion)
        operation: match | substitution | deletion | insertion
        model_probability: confidence dari framework (bisa null)
        proper_nouns: daftar proper noun yang dinormalisasi
        review_reasons: flag review dari framework
        start_seconds, end_seconds: timestamp
    
    Returns:
        ScoredWord bila kata perlu dinilai (match/substitution/deletion),
        None bila insertion (diabaikan)
    """
    # Insertion diabaikan (D1)
    if operation == "insertion":
        return None
    
    # Deletion: tidak dicoba, tidak masuk penyebut (D1)
    if operation == "deletion":
        return ScoredWord(
            position=position,
            reference_word=reference_word,
            transcript_word=transcript_word,
            confidence=model_probability,
            attempted=False,
            is_correct=False,
            reason="deletion: kata terlewat, tidak dicoba",
            review_reasons=review_reasons,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )
    
    # Match atau substitution → dicoba (D1)
    attempted = True

    # D2 (integrasi #2, Fase C.8): kata bertanda pergeseran (alignment_ambiguous)
    # TIDAK dihitung Correct sampai ditinjau. Ini konservatif & disengaja: mencegah
    # kata yang tak dapat dipercaya menaikkan skor. Kata tetap dicoba (attempted=True)
    # sehingga masuk Total Words Read, tetapi TIDAK masuk Correct Words → Accuracy
    # turun (menunggu tinjauan manusia).
    if "alignment_ambiguous" in review_reasons:
        return ScoredWord(
            position=position,
            reference_word=reference_word,
            transcript_word=transcript_word,
            confidence=model_probability,
            attempted=True,
            is_correct=False,
            reason="alignment_ambiguous: menunggu tinjauan → tidak dihitung Correct (D2)",
            review_reasons=review_reasons,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )

    # Cek proper noun (D5)
    is_proper = False
    if reference_word:
        normalized_ref = _normalize_for_proper_noun(reference_word)
        normalized_proper = [_normalize_for_proper_noun(p) for p in proper_nouns]
        is_proper = normalized_ref in normalized_proper
    
    # Penilaian
    if is_proper:
        # D5: Proper noun selalu Correct (match atau substitution)
        return ScoredWord(
            position=position,
            reference_word=reference_word,
            transcript_word=transcript_word,
            confidence=model_probability,
            attempted=attempted,
            is_correct=True,
            is_proper_noun=True,
            reason="proper_noun: nama di daftar → Correct",
            review_reasons=review_reasons,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )
    
    if operation == "match":
        # D11: probability null → Incorrect
        if model_probability is None:
            return ScoredWord(
                position=position,
                reference_word=reference_word,
                transcript_word=transcript_word,
                confidence=model_probability,
                attempted=attempted,
                is_correct=False,
                reason="probability_unavailable: model_probability null → Incorrect",
                review_reasons=review_reasons + ["probability_unavailable"],
                start_seconds=start_seconds,
                end_seconds=end_seconds,
            )
        
        # D10: match + confidence > 0.5 → Correct
        if model_probability > CONFIDENCE_THRESHOLD:
            return ScoredWord(
                position=position,
                reference_word=reference_word,
                transcript_word=transcript_word,
                confidence=model_probability,
                attempted=attempted,
                is_correct=True,
                reason=f"match + confidence {model_probability:.2f} > {CONFIDENCE_THRESHOLD} → Correct",
                review_reasons=review_reasons,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
            )
        else:
            # D10: match + confidence ≤ 0.5 → Incorrect (kasus "pasar" 0.34)
            return ScoredWord(
                position=position,
                reference_word=reference_word,
                transcript_word=transcript_word,
                confidence=model_probability,
                attempted=attempted,
                is_correct=False,
                reason=f"match + confidence {model_probability:.2f} ≤ {CONFIDENCE_THRESHOLD} → Incorrect",
                review_reasons=review_reasons,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
            )
    
    if operation == "substitution":
        # Substitution → Incorrect (sudah dihandle proper noun di atas)
        return ScoredWord(
            position=position,
            reference_word=reference_word,
            transcript_word=transcript_word,
            confidence=model_probability,
            attempted=attempted,
            is_correct=False,
            reason="substitution: kata berbeda → Incorrect",
            review_reasons=review_reasons,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )
    
    # Fallback (seharusnya tidak tercapai)
    return ScoredWord(
        position=position,
        reference_word=reference_word,
        transcript_word=transcript_word,
        confidence=model_probability,
        attempted=attempted,
        is_correct=False,
        reason=f"unknown operation: {operation}",
        review_reasons=review_reasons,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    )


def score_alignment(
    alignment_words: list[dict],
    proper_nouns: list[str],
) -> ScoringResult:
    """Menilai seluruh kata dari framework alignment.
    
    Args:
        alignment_words: alignment.words[] dari framework
        proper_nouns: daftar proper noun untuk teks ini
    
    Returns:
        ScoringResult dengan total_words_read, correct_words, incorrect_words
    """
    result = ScoringResult()
    
    for item in alignment_words:
        scored = score_word(
            position=item.get("position", 0),
            reference_word=item.get("reference_word"),
            transcript_word=item.get("transcript_word"),
            operation=item.get("operation", ""),
            model_probability=item.get("model_probability"),
            proper_nouns=proper_nouns,
            review_reasons=item.get("review_reasons", []),
            start_seconds=item.get("start_seconds"),
            end_seconds=item.get("end_seconds"),
        )
        
        if scored:  # insertion diabaikan (None)
            result.words.append(scored)
    
    return result


# ponytail: LCS lama dihapus, alignment sekarang dari framework
