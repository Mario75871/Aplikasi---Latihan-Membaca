"""Pipeline tests using a MOCK model (no Whisper download/CPU).

Fokus pada invariants yang wajib dibuktikan:
- ASR tidak menerima target sebagai prompt;
- perubahan target tidak mengubah decoding;
- raw transcript tidak berubah karena alignment/review;
- WER=0 tidak mengubah assessment;
- ASR gagal -> status + error benar.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from reading_framework import pipeline
from reading_framework.config import FrameworkConfig

AUDIO = "audio/indo_1-1_correct.wav"


class _FakeWord(SimpleNamespace):
    pass


def _fake_segments(texts):
    """Bangun segmen tiruan seperti yang dikembalikan faster-whisper."""
    segments = []
    for i, (text, words) in enumerate(texts):
        segments.append(SimpleNamespace(
            id=i + 1, start=float(i), end=float(i + 1), text=text,
            avg_logprob=-0.3, no_speech_prob=0.1, compression_ratio=1.2,
            words=[_FakeWord(word=w, start=float(i) + 0.1 * k, end=float(i) + 0.1 * (k + 1),
                             probability=0.9)
                   for k, w in enumerate(words)],
        ))
    return segments


class MockModel:
    """Model palsu yang merekam kwargs transcribe() dan mengembalikan teks tetap."""

    def __init__(self, text="ibu pergi ke pasap", words=None):
        self.calls: list[dict] = []
        self.model_path = "mock"
        self._text = text
        self._words = words or text.split()

    def transcribe(self, audio, **kwargs):
        self.calls.append(kwargs)
        segs = _fake_segments([(self._text, [" " + w for w in self._words])])
        info = SimpleNamespace(language="id", language_probability=1.0)
        return iter(segs), info


class FailingModel:
    model_path = "mock-fail"

    def transcribe(self, audio, **kwargs):
        raise RuntimeError("decode boom")


def _cfg():
    return FrameworkConfig()


def test_asr_does_not_receive_target_as_prompt(tmp_path):
    model = MockModel()
    pipeline.transcribe_reading(
        AUDIO, reference_text="ibu pergi ke pasar", model=model, config=_cfg(),
        output_dir=tmp_path, persist=True,
    )
    assert model.calls, "transcribe should have been called"
    kwargs = model.calls[0]
    assert kwargs.get("initial_prompt") is None
    assert kwargs.get("hotwords") is None
    assert kwargs.get("prefix") is None
    assert "ibu pergi ke pasar" not in str(kwargs)


def test_changing_target_does_not_change_decoding(tmp_path):
    m1 = MockModel()
    pipeline.transcribe_reading(AUDIO, reference_text="ibu pergi ke pasar",
                                model=m1, config=_cfg(), output_dir=tmp_path / "a")
    m2 = MockModel()
    pipeline.transcribe_reading(AUDIO, reference_text="TOTALLY DIFFERENT TARGET",
                                model=m2, config=_cfg(), output_dir=tmp_path / "b")
    # kwargs decoding identik
    assert m1.calls[0] == m2.calls[0]


def test_raw_transcript_unchanged_by_alignment(tmp_path):
    model = MockModel()
    res = pipeline.transcribe_reading(AUDIO, reference_text="ibu pergi ke pasar",
                                      model=model, config=_cfg(), output_dir=tmp_path)
    # raw text harus persis keluaran model
    assert res.raw_text == "ibu pergi ke pasap"
    # raw transcript file juga persis
    raw_file = (tmp_path / pipeline.RAW_TRANSCRIPT_FILENAME).read_text(encoding="utf-8")
    assert raw_file.strip() == "ibu pergi ke pasap"


def test_alignment_uses_mock_transcript(tmp_path):
    model = MockModel()
    res = pipeline.transcribe_reading(AUDIO, reference_text="ibu pergi ke pasar",
                                      model=model, config=_cfg(), output_dir=tmp_path)
    al = res.result["alignment"]
    assert al["status"] == "computed"
    assert al["substitutions"] == 1
    assert al["wer"] == 0.25
    # substitution wajib punya probability + timestamp dari model
    sub = [w for w in al["words"] if w["operation"] == "substitution"][0]
    assert sub["model_probability"] == 0.9
    assert sub["start_seconds"] is not None


def test_wer_zero_does_not_confirm_reading(tmp_path):
    model = MockModel(text="ibu pergi ke pasar", words=["ibu", "pergi", "ke", "pasar"])
    res = pipeline.transcribe_reading(AUDIO, reference_text="ibu pergi ke pasar",
                                      model=model, config=_cfg(), output_dir=tmp_path)
    assert res.result["alignment"]["wer"] == 0.0
    a = res.result["assessment"]
    assert a["reading_correctness_confirmed"] is False
    assert a["pronunciation_verified"] is False
    assert a["human_reviewed"] is False


def test_target_not_provided_alignment_not_computed(tmp_path):
    model = MockModel()
    res = pipeline.transcribe_reading(AUDIO, reference_text=None, model=model,
                                      config=_cfg(), output_dir=tmp_path)
    al = res.result["alignment"]
    assert al["status"] == "not_computed"
    assert al["reason"] == "reference_not_provided"
    assert al["wer"] is None


def test_empty_target_not_computed(tmp_path):
    model = MockModel()
    res = pipeline.transcribe_reading(AUDIO, reference_text="   ", model=model,
                                      config=_cfg(), output_dir=tmp_path)
    assert res.result["alignment"]["status"] == "not_computed"
    assert res.result["alignment"]["reason"] == "reference_invalid"


def test_asr_failure_status_and_raw_transcript(tmp_path):
    res = pipeline.transcribe_reading(AUDIO, reference_text="x", model=FailingModel(),
                                      config=_cfg(), output_dir=tmp_path)
    assert res.asr_ok is False
    assert res.result["job"]["status"] == "failed"
    assert res.result["errors"]
    assert res.result["alignment"]["status"] == "not_computed"
    # raw transcript file menandai kegagalan, bukan transkrip palsu
    content = (tmp_path / pipeline.RAW_TRANSCRIPT_FILENAME).read_text(encoding="utf-8")
    assert "ASR FAILED" in content


def test_reference_metadata_source_id(tmp_path, question_bank_path):
    from reading_framework.repository import LocalQuestionRepository
    repo = LocalQuestionRepository.from_file(question_bank_path)
    model = MockModel()
    res = pipeline.transcribe_reading(AUDIO, question_id="indo_1-1_correct",
                                      repository=repo, model=model, config=_cfg(),
                                      output_dir=tmp_path)
    ref = res.result["reference"]
    assert ref["provided"] is True
    assert ref["source_id"] == "indo_1-1_correct"
    assert ref["source_type"] == "question_bank"
    assert ref["used_during_asr"] is False


def test_missing_question_transcribes_but_no_alignment(tmp_path, question_bank_path):
    from reading_framework.repository import LocalQuestionRepository
    repo = LocalQuestionRepository.from_file(question_bank_path)
    model = MockModel()
    res = pipeline.transcribe_reading(AUDIO, question_id="does-not-exist",
                                      repository=repo, model=model, config=_cfg(),
                                      output_dir=tmp_path)
    # transkripsi tetap boleh jalan
    assert res.raw_text == "ibu pergi ke pasap"
    assert res.result["alignment"]["status"] == "not_computed"
    assert any("not found" in e for e in res.result["errors"])


def test_no_absolute_path_in_serialized_result(tmp_path):
    model = MockModel()
    res = pipeline.transcribe_reading(AUDIO, reference_text="ibu pergi ke pasar",
                                      model=model, config=_cfg(), output_dir=tmp_path)
    import json
    blob = json.dumps(res.result)
    assert str(tmp_path) not in blob
    assert "/Users/" not in blob


# --- Kasus nyata: audio 'komputer' ditranskripsi 'computer' ----------------- #
# CATATAN: test di bawah memakai MOCK model (teks simulasi). Ia TIDAK menguji
# akurasi pengenalan audio. Regresi audio nyata ada di
# tests/test_integration_real_asr.py (ditandai 'integration').

COMPUTER_MODEL_TEXT = "Computer diperbaiki di Jakarta"


def test_raw_text_preserves_computer_from_asr(tmp_path):
    """ASR menghasilkan 'Computer' -> raw_text mempertahankannya apa adanya."""
    model = MockModel(text=COMPUTER_MODEL_TEXT,
                      words=["Computer", "diperbaiki", "di", "Jakarta"])
    res = pipeline.transcribe_reading(
        AUDIO, reference_text="komputer diperbaiki di jakarta",
        model=model, config=_cfg(), output_dir=tmp_path)
    assert res.raw_text == COMPUTER_MODEL_TEXT
    raw_file = (tmp_path / pipeline.RAW_TRANSCRIPT_FILENAME).read_text(encoding="utf-8")
    assert raw_file.strip() == COMPUTER_MODEL_TEXT


def test_normalization_disabled_by_default(tmp_path):
    model = MockModel(text=COMPUTER_MODEL_TEXT,
                      words=["Computer", "diperbaiki", "di", "Jakarta"])
    res = pipeline.transcribe_reading(
        AUDIO, reference_text="komputer diperbaiki di jakarta",
        model=model, config=_cfg(), output_dir=tmp_path)
    t = res.result["transcript"]
    assert t["spelling_normalization_enabled"] is False
    assert t["normalized_text"] is None
    assert t["spelling_changes"] is None
    assert t["raw_text"] == COMPUTER_MODEL_TEXT


def test_normalization_when_enabled_records_changes_separately(tmp_path):
    cfg = FrameworkConfig(spelling_normalization_enabled=True)
    model = MockModel(text=COMPUTER_MODEL_TEXT,
                      words=["Computer", "diperbaiki", "di", "Jakarta"])
    res = pipeline.transcribe_reading(
        AUDIO, reference_text="komputer diperbaiki di jakarta",
        model=model, config=cfg, output_dir=tmp_path)
    t = res.result["transcript"]
    # raw_text TETAP mentah
    assert t["raw_text"] == COMPUTER_MODEL_TEXT
    raw_file = (tmp_path / pipeline.RAW_TRANSCRIPT_FILENAME).read_text(encoding="utf-8")
    assert raw_file.strip() == COMPUTER_MODEL_TEXT
    # representasi pembanding terpisah, dengan jejak audit
    assert t["spelling_normalization_enabled"] is True
    assert t["normalized_text"] == "Komputer diperbaiki di Jakarta"
    assert t["spelling_changes"]
    change = t["spelling_changes"][0]
    assert change["original"] == "Computer"
    assert change["normalized"] == "Komputer"
    assert change["rule_id"] == "id_computer_komputer"
    assert change["source"]


def test_target_not_forwarded_even_with_normalization(tmp_path):
    cfg = FrameworkConfig(spelling_normalization_enabled=True)
    model = MockModel(text=COMPUTER_MODEL_TEXT,
                      words=["Computer", "diperbaiki", "di", "Jakarta"])
    pipeline.transcribe_reading(
        AUDIO, reference_text="komputer diperbaiki di jakarta",
        model=model, config=cfg, output_dir=tmp_path)
    kwargs = model.calls[0]
    assert kwargs.get("initial_prompt") is None
    assert kwargs.get("hotwords") is None
    assert kwargs.get("prefix") is None
    assert "komputer diperbaiki di jakarta" not in str(kwargs)
