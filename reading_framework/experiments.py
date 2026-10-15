"""Eksperimen decoding: pengaruh prompt/hotwords (NONAKTIF secara default).

Modul ini TERPISAH dari jalur produksi. Tujuannya mengukur secara jujur apakah
memberi petunjuk decoding (``initial_prompt``/``hotwords``) mengubah hasil ASR —
tanpa pernah mengaktifkannya diam-diam di pipeline normal.

Aturan yang ditegakkan:

- ``compare_with_and_without_hint`` menjalankan audio yang SAMA dua kali: sekali
  tanpa petunjuk, sekali dengan petunjuk, lalu menghitung WER/CER memakai aturan
  normalisasi evaluasi yang terdokumentasi (``DEFAULT_NORMALIZATION``).
- Petunjuk TIDAK PERNAH berasal dari bank soal secara implisit; pemanggil harus
  memberikannya eksplisit (mis. saat eksperimen terkontrol).
- Hasil dilaporkan sebagai perbandingan metrik, BUKAN kesimpulan bahwa ejaan
  yang "diperbaiki" berarti pengucapan anak benar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .asr_engine import transcribe_audio
from .config import DEFAULT_NORMALIZATION, PROFILE_BASELINE, get_profile_params
from .metrics import STATUS_COMPUTED, calculate_metrics


@dataclass
class HintComparison:
    """Hasil perbandingan decoding dengan vs tanpa petunjuk untuk satu audio."""

    audio_path: str
    hint: dict[str, Any]
    without_hint_raw_text: str
    with_hint_raw_text: str
    without_hint_wer: float | None
    with_hint_wer: float | None
    without_hint_cer: float | None
    with_hint_cer: float | None
    reference_text: str | None
    normalization_profile: str = DEFAULT_NORMALIZATION.profile_id
    notes: list[str] = field(default_factory=list)

    @property
    def wer_delta(self) -> float | None:
        if self.without_hint_wer is None or self.with_hint_wer is None:
            return None
        return self.with_hint_wer - self.without_hint_wer

    @property
    def cer_delta(self) -> float | None:
        if self.without_hint_cer is None or self.with_hint_cer is None:
            return None
        return self.with_hint_cer - self.without_hint_cer


def compare_with_and_without_hint(
    model: Any,
    audio_path: str,
    *,
    reference_text: str | None = None,
    hint: dict[str, Any] | None = None,
    baseline_params: dict[str, Any] | None = None,
    language: str = "id",
) -> HintComparison:
    """Jalankan ASR audio yang sama dengan & tanpa petunjuk decoding.

    ``hint`` mis. ``{"initial_prompt": "komputer diperbaiki di jakarta"}`` atau
    ``{"hotwords": ["komputer"]}``. Pemanggil bertanggung jawab memastikan ini
    eksperimen terkontrol, bukan jalur produksi.

    Bila ``reference_text`` diberikan, WER/CER dihitung dengan normalisasi
    evaluasi terdokumentasi; jika tidak, metrik bernilai ``None``.
    """
    hint = hint or {}
    base = baseline_params or get_profile_params(PROFILE_BASELINE)
    # Profil baseline -> paksa decoding mentah-deterministik untuk perbandingan.
    common = {k: v for k, v in base.items() if k not in ("initial_prompt", "hotwords", "prefix")}

    without = transcribe_audio(model, audio_path, params=common, language=language)
    with_hint = transcribe_audio(model, audio_path, params={**common, **hint},
                                 language=language, allow_hint=True)

    notes: list[str] = []
    if without.error:
        notes.append(f"without_hint error: {without.error}")
    if with_hint.error:
        notes.append(f"with_hint error: {with_hint.error}")

    wo_wer = wo_cer = wi_wer = wi_cer = None
    if reference_text is not None:
        m_wo = calculate_metrics(reference_text, without.raw_text, DEFAULT_NORMALIZATION)
        m_wi = calculate_metrics(reference_text, with_hint.raw_text, DEFAULT_NORMALIZATION)
        if m_wo.status == STATUS_COMPUTED:
            wo_wer, wo_cer = m_wo.wer, m_wo.cer
        if m_wi.status == STATUS_COMPUTED:
            wi_wer, wi_cer = m_wi.wer, m_wi.cer
    else:
        notes.append("reference not provided: WER/CER not computed")

    notes.append(
        "hint experiment only: improved spelling via hint does NOT prove correct pronunciation"
    )

    return HintComparison(
        audio_path=str(audio_path),
        hint=dict(hint),
        without_hint_raw_text=without.raw_text,
        with_hint_raw_text=with_hint.raw_text,
        without_hint_wer=wo_wer,
        with_hint_wer=wi_wer,
        without_hint_cer=wo_cer,
        with_hint_cer=wi_cer,
        reference_text=reference_text,
        notes=notes,
    )
