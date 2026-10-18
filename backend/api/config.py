"""Config API — ambang batas untuk presentasi (integrasi #3, Fase F / aturan #9).

Menyediakan ambang yang dipakai backend agar frontend tidak menyalin nilai secara
manual. Frontend tetap HANYA presentasi; keputusan tetap di backend.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.auth import require_teacher
from rules.adaptive_rules import (
    ACCURACY_HIGH,
    ACCURACY_LOW,
    COMPREHENSION_MIN,
)
from services.audio_validation import (
    max_audio_bytes,
    max_audio_duration_sec,
    target_sample_rate,
)

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/thresholds")
def get_thresholds(request: Request, teacher: str = Depends(require_teacher)):
    """GET /config/thresholds — ambang resmi dari backend (satu sumber kebenaran)."""
    return {
        "accuracy_low": ACCURACY_LOW,
        "accuracy_high": ACCURACY_HIGH,
        "comprehension_min": COMPREHENSION_MIN,
    }


@router.get("/audio")
def get_audio_config(request: Request, teacher: str = Depends(require_teacher)):
    """GET /config/audio — konvensi audio dari satu sumber backend (integrasi #5, A.3).

    Dipakai untuk anti-drift: frontend (atau test) membandingkan nilai ini dengan
    konstanta di `frontend/lib/audio-wav.ts` (TARGET_SAMPLE_RATE/MAX_AUDIO_BYTES).
    """
    return {
        "target_sample_rate": target_sample_rate(),
        "max_audio_bytes": max_audio_bytes(),
        "max_audio_duration_sec": max_audio_duration_sec(),
    }
