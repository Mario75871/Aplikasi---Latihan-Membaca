"""Reading Framework — ASR mentah + alignment berbasis target untuk tes baca anak.

Prinsip: RAW-FIRST, TARGET-BASED ALIGNMENT, CONFIDENCE-ASSISTED REVIEW.

Contoh::

    from reading_framework import transcribe_reading, FrameworkConfig

    result = transcribe_reading(
        "audio/indo_1-1_correct.wav",
        reference_text="ibu pergi ke pasar",
        output_dir="results/job-001",
    )
    print(result.result["alignment"]["wer"])
"""

from __future__ import annotations

from .config import (
    SCHEMA_VERSION,
    FrameworkConfig,
    NormalizationProfile,
    PROFILE_BASELINE,
    PROFILE_RAW_READING,
    RAW_READING_PARAMS,
    ReviewThresholds,
    get_profile_params,
)
from .metrics import calculate_metrics
from .pipeline import ReadingResult, align_transcript, transcribe_reading
from .repository import LocalQuestionRepository, Question, QuestionRepository

__version__ = "1.0.0"

__all__ = [
    "SCHEMA_VERSION",
    "FrameworkConfig",
    "NormalizationProfile",
    "ReviewThresholds",
    "PROFILE_RAW_READING",
    "PROFILE_BASELINE",
    "RAW_READING_PARAMS",
    "get_profile_params",
    "calculate_metrics",
    "transcribe_reading",
    "align_transcript",
    "ReadingResult",
    "LocalQuestionRepository",
    "Question",
    "QuestionRepository",
    "__version__",
]
