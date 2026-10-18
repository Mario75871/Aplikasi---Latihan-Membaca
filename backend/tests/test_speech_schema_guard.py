"""Test penjaga kontrak framework ↔ backend (integrasi #2, Fase B).

Memastikan update framework yang memutus kompatibilitas GAGAL CEPAT dengan pesan
jelas, bukan KeyError/None diam-diam. Penjaga: ``_check_framework_contract`` di
``services/speech.py``.
"""
import pytest

from services.speech import (
    EXPECTED_SCHEMA_VERSION,
    _check_framework_contract,
)


def _valid_result() -> dict:
    """Hasil minimal yang lolos kontrak."""
    return {
        "schema_version": EXPECTED_SCHEMA_VERSION,
        "transcript": {"raw_text": "ibu pergi"},
        "alignment": {"words": []},
        "audio": {"duration_seconds": 1.5},
    }


def test_expected_schema_version_is_framework_version():
    """Versi yang diharapkan sinkron dengan framework (bukan angka keras terpisah)."""
    from reading_framework.config import SCHEMA_VERSION

    assert EXPECTED_SCHEMA_VERSION == SCHEMA_VERSION == "1.0.0"


def test_valid_contract_passes():
    _check_framework_contract(_valid_result())  # tidak raise


def test_missing_schema_version_fails():
    result = _valid_result()
    del result["schema_version"]
    with pytest.raises(RuntimeError, match="schema_version"):
        _check_framework_contract(result)


def test_mismatched_schema_version_fails():
    result = _valid_result()
    result["schema_version"] = "9.9.9"
    with pytest.raises(RuntimeError, match="tidak cocok"):
        _check_framework_contract(result)


def test_missing_transcript_raw_text_fails():
    result = _valid_result()
    del result["transcript"]["raw_text"]
    with pytest.raises(RuntimeError, match="transcript.raw_text"):
        _check_framework_contract(result)


def test_missing_alignment_words_fails():
    result = _valid_result()
    del result["alignment"]["words"]
    with pytest.raises(RuntimeError, match="alignment.words"):
        _check_framework_contract(result)


def test_missing_audio_duration_fails():
    result = _valid_result()
    del result["audio"]["duration_seconds"]
    with pytest.raises(RuntimeError, match="audio.duration_seconds"):
        _check_framework_contract(result)


def test_non_dict_result_fails():
    with pytest.raises(RuntimeError, match="bukan dict"):
        _check_framework_contract(["not", "a", "dict"])
