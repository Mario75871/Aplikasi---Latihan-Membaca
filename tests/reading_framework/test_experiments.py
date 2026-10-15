"""Tests untuk harness eksperimen decoding (prompt/hotwords), default nonaktif.

Memakai MOCK model: merekam kwargs dan mengembalikan teks berbeda bergantung
ada/tidaknya petunjuk. Ini TIDAK menguji akurasi audio; hanya menguji logika
perbandingan + perhitungan WER/CER.
"""

from __future__ import annotations

from types import SimpleNamespace

from reading_framework.experiments import compare_with_and_without_hint


class _HintAwareModel:
    """Mengembalikan 'komputer...' bila ada petunjuk, 'Computer...' bila tidak."""

    model_path = "mock"

    def __init__(self):
        self.calls: list[dict] = []

    def transcribe(self, audio, language=None, task=None, beam_size=None,
                   best_of=None, temperature=None, patience=None,
                   length_penalty=None, repetition_penalty=None,
                   no_repeat_ngram_size=None, condition_on_previous_text=None,
                   initial_prompt=None, hotwords=None, prefix=None,
                   no_speech_threshold=None, log_prob_threshold=None,
                   compression_ratio_threshold=None, suppress_blank=None,
                   suppress_tokens=None, max_initial_timestamp=None,
                   word_timestamps=None, without_timestamps=None,
                   vad_filter=None, **kwargs):
        self.calls.append(dict(
            language=language, initial_prompt=initial_prompt,
            hotwords=hotwords, prefix=prefix))
        has_hint = initial_prompt or hotwords
        text = "komputer diperbaiki di jakarta" if has_hint else "Computer diperbaiki di jakarta"
        words = text.split()
        seg = SimpleNamespace(
            id=1, start=0.0, end=4.0, text=text,
            avg_logprob=-0.4, no_speech_prob=0.1, compression_ratio=0.8,
            words=[SimpleNamespace(word=" " + w, start=float(i), end=float(i) + 1,
                                   probability=0.9)
                   for i, w in enumerate(words)],
        )
        info = SimpleNamespace(language="id", language_probability=1.0)
        return iter([seg]), info


def test_compare_runs_twice_and_reports_wer_delta():
    model = _HintAwareModel()
    cmp = compare_with_and_without_hint(
        model, "audio/tes_14_10_26_6.wav",
        reference_text="komputer diperbaiki di jakarta",
        hint={"initial_prompt": "komputer diperbaiki di jakarta"},
    )
    # dua kali panggilan: tanpa petunjuk lalu dengan petunjuk
    assert len(model.calls) == 2
    assert model.calls[0].get("initial_prompt") is None
    assert model.calls[1].get("initial_prompt") is not None

    assert "Computer" in cmp.without_hint_raw_text
    assert "komputer" in cmp.with_hint_raw_text
    assert cmp.without_hint_wer == 0.25
    assert cmp.with_hint_wer == 0.0
    assert cmp.wer_delta is not None and cmp.wer_delta < 0


def test_compare_without_reference_reports_none():
    model = _HintAwareModel()
    cmp = compare_with_and_without_hint(model, "x.wav", reference_text=None,
                                        hint={"hotwords": ["komputer"]})
    assert cmp.without_hint_wer is None
    assert cmp.with_hint_wer is None
    assert any("not computed" in n for n in cmp.notes)


def test_compare_notes_do_not_claim_pronunciation():
    model = _HintAwareModel()
    cmp = compare_with_and_without_hint(
        model, "x.wav", reference_text="komputer", hint={"hotwords": ["komputer"]})
    assert any("does NOT prove" in n for n in cmp.notes)
