"""Test Model #2 — Penilaian kata dari framework alignment (Fase 1B)."""
import pytest

from services.scoring import (
    CONFIDENCE_THRESHOLD,
    score_alignment,
    score_word,
)


def test_confidence_above_threshold_is_correct():
    """Match + confidence > 0.5 → Correct."""
    scored = score_word(
        position=0,
        reference_word="ibu",
        transcript_word="ibu",
        operation="match",
        model_probability=0.95,
        proper_nouns=[],
        review_reasons=[],
    )
    assert scored.attempted is True
    assert scored.is_correct is True
    assert "Correct" in scored.reason


def test_confidence_at_boundary_is_incorrect():
    """Match + confidence = 0.5 → Incorrect."""
    scored = score_word(
        position=0,
        reference_word="pergi",
        transcript_word="pergi",
        operation="match",
        model_probability=0.5,
        proper_nouns=[],
        review_reasons=[],
    )
    assert scored.attempted is True
    assert scored.is_correct is False
    assert "Incorrect" in scored.reason


def test_pasar_low_confidence_is_incorrect():
    """Kasus 'pasar' confidence 0.34 → Incorrect (acceptance criteria F-06)."""
    scored = score_word(
        position=3,
        reference_word="pasar",
        transcript_word="pasar",
        operation="match",
        model_probability=0.34,
        proper_nouns=[],
        review_reasons=["low_model_probability"],
    )
    assert scored.attempted is True
    assert scored.is_correct is False
    assert scored.confidence == 0.34
    assert "0.34" in scored.reason and "Incorrect" in scored.reason


def test_proper_noun_match_is_correct():
    """D5: Proper noun + match → Correct."""
    scored = score_word(
        position=0,
        reference_word="Boni",
        transcript_word="Boni",
        operation="match",
        model_probability=0.3,  # rendah tapi proper noun
        proper_nouns=["Boni"],
        review_reasons=[],
    )
    assert scored.attempted is True
    assert scored.is_correct is True
    assert scored.is_proper_noun is True
    assert "proper_noun" in scored.reason


def test_proper_noun_substitution_is_correct():
    """D5: 'boni' → 'bonnie' (substitution) + proper_nouns=['boni'] → Correct."""
    scored = score_word(
        position=0,
        reference_word="boni",
        transcript_word="bonnie",
        operation="substitution",
        model_probability=0.8,
        proper_nouns=["boni"],
        review_reasons=[],
    )
    assert scored.attempted is True
    assert scored.is_correct is True
    assert scored.is_proper_noun is True


def test_proper_noun_case_insensitive():
    """Proper noun normalisasi case-insensitive."""
    scored = score_word(
        position=0,
        reference_word="BONI",
        transcript_word="bonnie",
        operation="substitution",
        model_probability=0.8,
        proper_nouns=["boni"],  # lowercase
        review_reasons=[],
    )
    assert scored.is_correct is True
    assert scored.is_proper_noun is True


def test_substitution_without_proper_noun_is_incorrect():
    """Substitution tanpa proper noun → Incorrect."""
    scored = score_word(
        position=1,
        reference_word="pergi",
        transcript_word="pergo",
        operation="substitution",
        model_probability=0.7,
        proper_nouns=[],
        review_reasons=["reference_transcript_mismatch"],
    )
    assert scored.attempted is True
    assert scored.is_correct is False
    assert "substitution" in scored.reason


def test_deletion_not_attempted():
    """D1: Deletion (kata terlewat) → tidak dicoba, tidak masuk penyebut."""
    scored = score_word(
        position=2,
        reference_word="ke",
        transcript_word=None,
        operation="deletion",
        model_probability=None,
        proper_nouns=[],
        review_reasons=[],
    )
    assert scored.attempted is False
    assert scored.is_correct is False
    assert "deletion" in scored.reason


def test_insertion_ignored():
    """D1: Insertion → diabaikan (return None)."""
    scored = score_word(
        position=5,
        reference_word=None,
        transcript_word="tambahan",
        operation="insertion",
        model_probability=0.9,
        proper_nouns=[],
        review_reasons=[],
    )
    assert scored is None


def test_probability_null_is_incorrect():
    """D11: model_probability = null → Incorrect + review."""
    scored = score_word(
        position=1,
        reference_word="kata",
        transcript_word="kata",
        operation="match",
        model_probability=None,
        proper_nouns=[],
        review_reasons=[],
    )
    assert scored.attempted is True
    assert scored.is_correct is False
    assert "probability_unavailable" in scored.reason
    assert "probability_unavailable" in scored.review_reasons


def test_score_alignment_counts():
    """Test score_alignment menghitung total_words_read, correct, incorrect."""
    alignment_words = [
        {"position": 0, "reference_word": "ibu", "transcript_word": "ibu",
         "operation": "match", "model_probability": 0.95, "review_reasons": []},
        {"position": 1, "reference_word": "pergi", "transcript_word": "pergi",
         "operation": "match", "model_probability": 0.92, "review_reasons": []},
        {"position": 2, "reference_word": "ke", "transcript_word": None,
         "operation": "deletion", "model_probability": None, "review_reasons": []},
        {"position": 3, "reference_word": "pasar", "transcript_word": "pasar",
         "operation": "match", "model_probability": 0.34, "review_reasons": ["low_model_probability"]},
    ]
    
    result = score_alignment(alignment_words, proper_nouns=[])
    
    # Total Words Read = match (ibu, pergi, pasar) = 3 (ke tidak dicoba)
    assert result.total_words_read == 3
    # Correct = ibu (0.95), pergi (0.92) = 2
    assert result.correct_words == 2
    # Incorrect = pasar (0.34) = 1
    assert result.incorrect_words == 1


def test_accuracy_cannot_exceed_100_percent():
    """Property test: Accuracy selalu 0-100%."""
    alignment_words = [
        {"position": 0, "reference_word": "a", "transcript_word": "a",
         "operation": "match", "model_probability": 0.9, "review_reasons": []},
        {"position": 1, "reference_word": "b", "transcript_word": "b",
         "operation": "match", "model_probability": 0.8, "review_reasons": []},
    ]
    
    result = score_alignment(alignment_words, proper_nouns=[])
    
    # Correct = 2, Total = 2 → Accuracy = 100%
    accuracy = (result.correct_words / result.total_words_read) * 100 if result.total_words_read > 0 else 0
    assert 0 <= accuracy <= 100
    assert result.correct_words <= result.total_words_read


def test_insertion_not_in_counts():
    """Insertion tidak masuk correct maupun total."""
    alignment_words = [
        {"position": 0, "reference_word": "ibu", "transcript_word": "ibu",
         "operation": "match", "model_probability": 0.9, "review_reasons": []},
        {"position": 1, "reference_word": None, "transcript_word": "extra",
         "operation": "insertion", "model_probability": 0.8, "review_reasons": []},
        {"position": 2, "reference_word": "pergi", "transcript_word": "pergi",
         "operation": "match", "model_probability": 0.85, "review_reasons": []},
    ]
    
    result = score_alignment(alignment_words, proper_nouns=[])
    
    # Total = 2 (ibu, pergi), insertion diabaikan
    assert result.total_words_read == 2
    assert result.correct_words == 2


def test_deterministic_scoring():
    """Input yang sama menghasilkan hasil yang sama."""
    alignment_words = [
        {"position": 0, "reference_word": "test", "transcript_word": "test",
         "operation": "match", "model_probability": 0.7, "review_reasons": []},
    ]
    
    result1 = score_alignment(alignment_words, proper_nouns=[])
    result2 = score_alignment(alignment_words, proper_nouns=[])
    
    assert result1.total_words_read == result2.total_words_read
    assert result1.correct_words == result2.correct_words
    assert result1.incorrect_words == result2.incorrect_words


def test_threshold_constant():
    """CONFIDENCE_THRESHOLD harus bernama dan nilainya 0.5."""
    assert CONFIDENCE_THRESHOLD == 0.5
