"""Configuration: ASR decoding profiles and normalization profiles.

Semua parameter di sini berdiri sendiri (tanpa import faster-whisper), sehingga
dapat diuji tanpa model. Profil ASR divalidasi terhadap signature
``WhisperModel.transcribe`` pada saat runtime oleh ``asr_engine.filter_params``.

Prinsip: profil ``raw_reading`` mengutamakan pelaporan apa yang diucapkan,
bukan penafsiran. Tidak ada target text, prompt, hotwords, atau koreksi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = "1.0.0"

#: Nama profil ASR yang didukung.
PROFILE_RAW_READING = "raw_reading"
PROFILE_BASELINE = "baseline"


# --------------------------------------------------------------------------- #
# ASR decoding profiles
# --------------------------------------------------------------------------- #

#: Parameter kanonik untuk transkripsi mentah. Setiap kunci akan divalidasi
#: terhadap ``WhisperModel.transcribe`` sebelum dipakai (lihat filter_params),
#: sehingga versi faster-whisper yang berbeda tidak pernah crash karena kwarg
#: yang tidak dikenal.
RAW_READING_PARAMS: dict[str, Any] = {
    # ---- language / task -------------------------------------------------
    "language": "id",            # bahasa Indonesia eksplisit
    "task": "transcribe",        # tidak pernah "translate"
    # ---- decoding: greedy, deterministik, tanpa fallback -----------------
    "beam_size": 1,
    "best_of": 1,
    "temperature": 0.0,          # skalar -> satu lintasan, TANPA fallback
    "patience": 1.0,
    "length_penalty": 1.0,
    "repetition_penalty": 1.0,   # JANGAN hukum kata berulang
    "no_repeat_ngram_size": 0,   # 0 = izinkan pengulangan (setia pada audio)
    # ---- context / prompting: model TIDAK dipriming ----------------------
    "condition_on_previous_text": False,
    "initial_prompt": None,      # TIDAK ada priming teks target
    "hotwords": None,            # TIDAK ada bias kata kunci
    "prefix": None,
    # ---- penjaga halusinasi / senyap -------------------------------------
    # Tidak menulis ulang teks apa pun; hanya memutuskan kapan segmen
    # dianggap "tidak ada ucapan" lalu dilewati.
    "no_speech_threshold": 0.6,
    "log_prob_threshold": -1.0,
    "compression_ratio_threshold": 2.4,
    "suppress_blank": True,
    "suppress_tokens": [-1],
    "max_initial_timestamp": 1.0,
    # ---- timing ----------------------------------------------------------
    "word_timestamps": True,
    "without_timestamps": False,
    # ---- VAD baseline ----------------------------------------------------
    "vad_filter": False,
}

#: Profil pembanding untuk eksperimen/benchmark. Dipisahkan dari hasil tes
#: membaca resmi. Konfigurasi dipakai apa adanya, tidak diklaim "tercepat".
BASELINE_PARAMS: dict[str, Any] = {
    "language": None,            # auto-detect
    "task": "transcribe",
    "beam_size": 5,
    "best_of": 5,
    "temperature": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    "condition_on_previous_text": True,
    "initial_prompt": None,
    "hotwords": None,
    "vad_filter": False,
    "word_timestamps": False,
    "no_speech_threshold": 0.6,
    "log_prob_threshold": -1.0,
    "compression_ratio_threshold": 2.4,
}


def get_profile_params(profile: str = PROFILE_RAW_READING, **overrides: Any) -> dict[str, Any]:
    """Kembalikan salinan bersih parameter profil dengan override diterapkan.

    Nilai ``None`` pada *overrides* diabaikan agar pemanggil dapat melewatkan
    opsi opsional tanpa menimpa default.
    """
    if profile == PROFILE_RAW_READING:
        params = dict(RAW_READING_PARAMS)
    elif profile == PROFILE_BASELINE:
        params = dict(BASELINE_PARAMS)
    else:
        raise ValueError(f"unknown ASR profile: {profile!r}")
    for key, value in overrides.items():
        if value is None:
            continue
        params[key] = value
    return params


# Alias kompatibilitas dengan proyek lama.
raw_reading_params = get_profile_params


# --------------------------------------------------------------------------- #
# Normalization profile (deterministik, dipakai hanya untuk perbandingan)
# --------------------------------------------------------------------------- #

NORMALIZATION_PROFILE_ID = "id_reading_v1"


@dataclass(frozen=True)
class NormalizationProfile:
    """Aturan normalisasi deterministik untuk alignment & metrik.

    Teks mentah TIDAK pernah diubah; profil ini hanya menghasilkan representasi
    pembanding. Profil diberi id + versi agar hasil lama reproduksibel.
    """

    profile_id: str = NORMALIZATION_PROFILE_ID
    #: whether to fold to lowercase
    lowercase: bool = True
    #: whether to strip punctuation
    strip_punctuation: bool = True
    #: whether to collapse whitespace runs to a single space
    collapse_whitespace: bool = True
    #: whether to map curly apostrophes to straight ones
    normalize_apostrophes: bool = True
    #: whether to strip leading/trailing whitespace
    strip: bool = True
    #: extra characters to treat as punctuation (on top of the default set)
    extra_punctuation: str = ""


#: Default profile for Indonesian early-grade reading comparison.
DEFAULT_NORMALIZATION = NormalizationProfile()


# --------------------------------------------------------------------------- #
# Review thresholds (terkonfigurasi, TIDAK diklaim universal)
# --------------------------------------------------------------------------- #

@dataclass
class ReviewThresholds:
    """Ambang batas untuk review flagging.

    Threshold bukan vonis: ini hanya sinyal "perlu diperiksa". Nilai default
    bukan klaim yang berlaku untuk semua model/bahasa/usia/kondisi audio.
    """

    low_word_probability: float = 0.5
    low_segment_logprob: float = -1.0
    high_no_speech_prob: float = 0.6
    high_compression_ratio: float = 2.4
    zero_duration: float = 0.0
    watermark_phrases: tuple[str, ...] = ("terima kasih",)


@dataclass
class FrameworkConfig:
    """Konfigurasi runtime framework (default aman & terdokumentasi)."""

    asr_profile: str = PROFILE_RAW_READING
    model: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    cpu_threads: int = 4
    num_workers: int = 1
    language: str = "id"
    normalization: NormalizationProfile = field(default_factory=NormalizationProfile)
    thresholds: ReviewThresholds = field(default_factory=ReviewThresholds)
    #: true = tulis TXT/JSON; kegagalan file dicatat sebagai error, bukan silent
    write_files: bool = True
    #: OPSIONAL: normalisasi ejaan ID setelah ASR (default NONAKTIF).
    #: Tidak pernah mengubah ``raw_text``; hanya menambah representasi pembanding
    #: yang diaudit lewat ``transcript.normalized_text`` + ``spelling_changes``.
    spelling_normalization_enabled: bool = False
