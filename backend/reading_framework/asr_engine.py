"""ASR engine: faster-whisper wrapper that preserves raw model evidence.

Refactor dari ``OLD-PROJECT/raw_reading_asr.py`` (bagian yang masih benar
dipertahankan): profil ``raw_reading``, ``filter_params`` lintas-versi, dan
``transcribe_file`` yang TIDAK pernah memfabrikasi transkrip saat error.

Perbedaan penting dari versi lama:
- Mengembalikan struktur mentah (segments/words + timestamp + probability)
  tanpa mencampur metrik evaluasi atau teks target.
- Tidak menulis file; penulisan TXT/JSON dilakukan modul lain.
- ``language_used`` dicatat terpisah dari ``language_requested``.
- Target text TIDAK PERNAH diteruskan ke ``model.transcribe``.
"""

from __future__ import annotations

import inspect
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .audio import probe_audio
from .config import PROFILE_RAW_READING, get_profile_params

#: Kwarg yang HARAM diteruskan ke decoding karena berpotensi membocorkan target.
_FORBIDDEN_DECODE_KEYS = ("initial_prompt", "hotwords", "prefix")
#: Nilai yang menandai prompt/hotwords memang dipakai (None = tidak dipakai).
_PROMPT_KEYS = ("initial_prompt", "hotwords", "prefix")

_WARNED_UNSUPPORTED: set[tuple] = set()


@dataclass
class WordStamp:
    word: str
    start: float
    end: float
    probability: float | None = None


@dataclass
class SegmentStamp:
    id: int
    start: float
    end: float
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    compression_ratio: float | None = None
    words: list[WordStamp] = field(default_factory=list)


@dataclass
class ASRResult:
    """Bukti ASR mentah + diagnostik. Tanpa metrik evaluasi, tanpa target."""

    audio_path: str
    audio_seconds: float | None
    language_requested: str | None
    language: str | None
    language_probability: float | None
    segments: list[SegmentStamp]
    raw_text: str
    applied_params: dict[str, Any]
    profile: str = PROFILE_RAW_READING
    model: str = ""
    device: str = "cpu"
    compute_type: str = ""
    cpu_threads: int = 0
    engine: str = "faster-whisper"
    engine_version: str | None = None
    elapsed_seconds: float | None = None
    load_seconds: float | None = None
    peak_rss_mb: float | None = None
    error: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.error

    @property
    def word_count(self) -> int:
        return len(self.raw_text.split()) if self.raw_text else 0


def _nan_to_none(value: Any) -> float | None:
    """Konversi NaN/None/non-numerik menjadi ``None`` (data hilang != angka)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def import_faster_whisper():
    """Impor WhisperModel dengan pesan error yang menuntun ke env tes-baca."""
    try:
        from faster_whisper import WhisperModel  # noqa: WPS433
        return WhisperModel
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "faster-whisper is not importable in this interpreter.\n"
            f"  error: {exc}\n"
            "  hint : run inside the 'tes-baca' conda env, e.g.\n"
            "         conda run -n tes-baca python -m reading_framework <cmd>"
        ) from exc


def engine_version() -> str | None:
    try:  # pragma: no cover - environment dependent
        import faster_whisper

        return getattr(faster_whisper, "__version__", None)
    except Exception:
        return None


def filter_params(model: Any, params: dict[str, Any], warn: bool = False) -> dict[str, Any]:
    """Buang param yang tidak diterima signature ``transcribe()`` versi terpasang.

    Menjaga engine tetap kompatibel lintas versi faster-whisper tanpa pernah
    melewatkan kwarg yang tidak dikenal.
    """
    valid = set(inspect.signature(model.transcribe).parameters)
    unknown = sorted(set(params) - valid)
    if unknown and warn:
        key = (id(type(model)), tuple(unknown))
        if key not in _WARNED_UNSUPPORTED:
            _WARNED_UNSUPPORTED.add(key)
            print(f"  [warn] unsupported params ignored on this faster-whisper: {unknown}")
    return {k: v for k, v in params.items() if k in valid}


def assert_no_target_leak(params: dict[str, Any]) -> None:
    """Pastikan tidak ada target/prompt yang membocorkan teks acuan ke decoding.

    Dianggap bocor bila kunci prompt/hotwords bernilai non-None.
    """
    for key in _PROMPT_KEYS:
        if params.get(key) is not None:
            raise ValueError(
                f"refusing to run ASR: decoding param {key!r} must be None in raw mode "
                "(target text must not leak into ASR)"
            )


def load_model(model_id: str = "base", device: str = "cpu",
               compute_type: str = "int8", cpu_threads: int = 4,
               num_workers: int = 1) -> tuple[Any, float]:
    """Muat model sekali; pakai ulang untuk banyak file."""
    WhisperModel = import_faster_whisper()
    t0 = time.perf_counter()
    model = WhisperModel(
        model_id, device=device, compute_type=compute_type,
        cpu_threads=cpu_threads, num_workers=num_workers,
    )
    return model, time.perf_counter() - t0


def transcribe_audio(
    model: Any,
    audio_path: str | Path,
    *,
    profile: str = PROFILE_RAW_READING,
    params: dict[str, Any] | None = None,
    language: str | None = None,
    peak_rss_reader=None,
    allow_hint: bool = False,
) -> ASRResult:
    """Transkripsi satu audio dengan profil mentah. TIDAK menggunakan target.

    Pada kegagalan, hasil membawa ``error`` dan ``raw_text`` kosong — engine
    tidak pernah menyusun transkrip pengganti.

    ``allow_hint`` default ``False``: jalur produksi MENOLAK prompt/hotwords.
    Hanya harness eksperimen terkontrol yang boleh menyalakannya.
    """
    path = Path(audio_path)
    applied = get_profile_params(profile, **(params or {}))
    if language is not None:
        applied["language"] = language

    # Lindungi proses ASR dari kebocoran target SEBELUM filter/drop.
    if not allow_hint:
        assert_no_target_leak(applied)
    applied = filter_params(model, applied, warn=False)

    audio_info = probe_audio(path) if path.is_file() else None
    duration = audio_info.duration_seconds if audio_info else None

    result = ASRResult(
        audio_path=str(path),
        audio_seconds=duration,
        language_requested=applied.get("language"),
        language=None,
        language_probability=None,
        segments=[],
        raw_text="",
        applied_params=applied,
        profile=profile,
        model=str(getattr(model, "model_path", "") or ""),
        engine_version=engine_version(),
    )

    if not path.is_file():
        result.error = f"audio file not found: {path}"
        return result

    try:
        t0 = time.perf_counter()
        segments, info = model.transcribe(str(path), **applied)
        seg_list = list(segments)  # generator -> eager; kerja nyata di sini
        result.elapsed_seconds = time.perf_counter() - t0
    except Exception as exc:  # noqa: BLE001 - dilaporkan apa adanya
        result.error = f"{type(exc).__name__}: {exc}"
        return result

    stamps: list[SegmentStamp] = []
    texts: list[str] = []
    for seg in seg_list:
        words = [
            WordStamp(
                word=str(getattr(w, "word", "")),
                start=_nan_to_none(getattr(w, "start", None)) or 0.0,
                end=_nan_to_none(getattr(w, "end", None)) or 0.0,
                probability=_nan_to_none(getattr(w, "probability", None)),
            )
            for w in (getattr(seg, "words", None) or [])
        ]
        stamps.append(SegmentStamp(
            id=int(getattr(seg, "id", len(stamps))),
            start=_nan_to_none(getattr(seg, "start", None)) or 0.0,
            end=_nan_to_none(getattr(seg, "end", None)) or 0.0,
            text=str(getattr(seg, "text", "")).strip(),
            avg_logprob=_nan_to_none(getattr(seg, "avg_logprob", None)),
            no_speech_prob=_nan_to_none(getattr(seg, "no_speech_prob", None)),
            compression_ratio=_nan_to_none(getattr(seg, "compression_ratio", None)),
            words=words,
        ))
        texts.append(str(getattr(seg, "text", "")).strip())

    result.segments = stamps
    result.language = getattr(info, "language", None) or None
    result.language_probability = _nan_to_none(
        getattr(info, "language_probability", None)
    )
    # Raw concatenation — TANPA pembersihan, dedup, atau perbaikan tata bahasa.
    result.raw_text = " ".join(t for t in texts if t).strip()
    if callable(peak_rss_reader):
        result.peak_rss_mb = peak_rss_reader()
    return result
