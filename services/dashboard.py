"""Dashboard status mapping (D6, F-10).

Pemetaan status dashboard dari keputusan Adaptive Engine:
- Need Support = INTERVENE
- Developing = STAY
- On Track = STAY dengan Accuracy ≥ 95% dan semua kompetensi ≥ 80%, atau PROMOTE
- Promotion = PROMOTION_CANDIDATE

Pemetaan ada di satu fungsi dengan test.
"""
from __future__ import annotations

# Ambang (D6)
ON_TRACK_ACCURACY_MIN = 95.0
ON_TRACK_COMPREHENSION_MIN = 80.0


def map_dashboard_status(
    adaptive_status: str,
    accuracy: float,
    retrieve: float,
    interpret: float,
    reflect: float,
) -> str:
    """Pemetaan status dashboard dari keputusan Adaptive Engine (D6).

    Args:
        adaptive_status: INTERVENE | STAY | PROMOTION_CANDIDATE | PROMOTE
        accuracy: 0..100
        retrieve, interpret, reflect: 0..100

    Returns:
        "Need Support" | "Developing" | "On Track" | "Promotion"
    """
    if adaptive_status == "INTERVENE":
        return "Need Support"
    
    if adaptive_status == "PROMOTION_CANDIDATE":
        return "Promotion"
    
    if adaptive_status == "PROMOTE":
        return "On Track"
    
    # STAY: On Track bila Accuracy ≥ 95% dan semua kompetensi ≥ 80%
    if adaptive_status == "STAY":
        all_comp_ok = (
            retrieve >= ON_TRACK_COMPREHENSION_MIN
            and interpret >= ON_TRACK_COMPREHENSION_MIN
            and reflect >= ON_TRACK_COMPREHENSION_MIN
        )
        if accuracy >= ON_TRACK_ACCURACY_MIN and all_comp_ok:
            return "On Track"
        return "Developing"
    
    # Fallback
    return "Developing"
