"""Integration tests: memuat model Whisper NYATA + audio Indonesia nyata.

Hanya dijalankan bila ``RAW_READING_INTEGRATION=1`` (lihat conftest). Membuktikan
pipeline end-to-end benar-benar berjalan pada env tes-baca.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from reading_framework.config import FrameworkConfig
from reading_framework.pipeline import transcribe_reading
from reading_framework.repository import LocalQuestionRepository

# Fase A (integrasi #2): fixture lokal di dalam backend (tanpa folder luar).
ROOT = Path(__file__).resolve().parent / "fixtures"
AUDIO = ROOT / "audio"
BANK = ROOT / "examples" / "question_bank" / "questions.json"

pytestmark = pytest.mark.integration


def _cfg():
    return FrameworkConfig(model="base", compute_type="int8", cpu_threads=4)


def test_integration_correct_reading_wer_zero(tmp_path):
    audio = AUDIO / "indo_1-1_correct.wav"
    if not audio.is_file():
        pytest.skip(f"missing audio {audio}")
    res = transcribe_reading(audio, reference_text="ibu pergi ke pasar",
                             config=_cfg(), output_dir=tmp_path)
    assert res.asr_ok, res.result["errors"]
    assert res.raw_text
    assert res.result["alignment"]["status"] == "computed"
    assert res.result["alignment"]["wer"] == 0.0
    assert res.result["assessment"]["reading_correctness_confirmed"] is False


def test_integration_typo_reading_flags_mismatch(tmp_path):
    audio = AUDIO / "indo_1-1_typo.wav"
    if not audio.is_file():
        pytest.skip(f"missing audio {audio}")
    res = transcribe_reading(audio, reference_text="ibu pergi ke pasar",
                             config=_cfg(), output_dir=tmp_path)
    assert res.asr_ok, res.result["errors"]
    al = res.result["alignment"]
    assert al["status"] == "computed"
    assert al["wer"] > 0.0
    assert res.result["review"]["review_required"] is True


def test_integration_question_repository_source_id(tmp_path):
    audio = AUDIO / "indo_1-1_correct.wav"
    if not audio.is_file():
        pytest.skip(f"missing audio {audio}")
    repo = LocalQuestionRepository.from_file(BANK)
    res = transcribe_reading(audio, question_id="indo_1-1_correct", repository=repo,
                             config=_cfg(), output_dir=tmp_path)
    assert res.result["reference"]["source_id"] == "indo_1-1_correct"
    assert res.result["reference"]["used_during_asr"] is False


def test_integration_raw_transcript_persisted(tmp_path):
    audio = AUDIO / "indo_1-1_correct.wav"
    if not audio.is_file():
        pytest.skip(f"missing audio {audio}")
    res = transcribe_reading(audio, reference_text="ibu pergi ke pasar",
                             config=_cfg(), output_dir=tmp_path)
    raw_file = tmp_path / "transcript_raw.txt"
    assert raw_file.is_file()
    assert raw_file.read_text(encoding="utf-8").strip() == res.raw_text
    # JSON valid & schema version benar
    result_json = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert result_json["schema_version"] == "1.0.0"


def test_integration_computer_audio_raw_and_normalization(tmp_path):
    """REGRESI AUDIO NYATA: audio mengucapkan 'komputer', ASR -> 'Computer'.

    Ini satu-satunya test yang benar-benar menguji akurasi pengenalan audio
    untuk kasus ini. Test mock di test_pipeline.py hanya menguji alur data.
    """
    audio = AUDIO / "tes_14_10_26_6.wav"
    if not audio.is_file():
        pytest.skip(f"missing audio {audio}")
    target = "komputer diperbaiki di jakarta"

    # 1) default: raw_text mempertahankan 'Computer' (bukan 'komputer')
    res = transcribe_reading(audio, reference_text=target, config=_cfg(),
                             output_dir=tmp_path / "raw")
    assert res.asr_ok, res.result["errors"]
    assert "computer" in res.raw_text.lower()
    assert res.result["transcript"]["raw_text"] == res.raw_text
    assert res.result["transcript"]["normalized_text"] is None

    # 2) dengan normalisasi: raw_text TETAP 'Computer'; normalized terpisah
    cfg = FrameworkConfig(model="base", compute_type="int8", cpu_threads=4,
                          spelling_normalization_enabled=True)
    res2 = transcribe_reading(audio, reference_text=target, config=cfg,
                              output_dir=tmp_path / "norm")
    assert res2.asr_ok, res2.result["errors"]
    t = res2.result["transcript"]
    assert "Computer" in t["raw_text"]
    assert "komputer" in t["normalized_text"].lower()
    assert t["spelling_changes"]
    assert t["spelling_changes"][0]["original"].lower() == "computer"
