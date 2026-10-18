"""Hasbrouck–Tindal Reference API (F-11, D9)."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query

from rules.adaptive_rules import determine_season
from services.hasbrouck import get_percentile_position

router = APIRouter(prefix="/hasbrouck", tags=["hasbrouck"])


@router.get("/reference")
def hasbrouck_reference(
    grade: int = Query(..., ge=1, le=3),
    season: Optional[str] = Query(None, pattern="^(fall|winter|spring)$"),
    wcpm: float = Query(..., ge=0),
):
    """GET /hasbrouck/reference — posisi WCPM terhadap persentil P25/P50 (F-11).

    Bila `season` tidak diberikan, musim dihitung dari tanggal server (D2/D9).
    """
    resolved_season = season or determine_season(datetime.now(timezone.utc))
    return get_percentile_position(grade, resolved_season, wcpm)
