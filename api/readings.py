"""Readings API — v2.5."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from repository import get_repository

router = APIRouter(prefix="/readings", tags=["readings"])


@router.get("")
def list_readings(grade: Optional[int] = None, complexity: Optional[int] = None):
    """GET /readings — daftar bacaan, filter opsional."""
    repo = get_repository()
    return repo.list_readings(grade=grade, complexity=complexity)


@router.get("/{reading_id}")
def get_reading(reading_id: str):
    """GET /readings/{id}."""
    repo = get_repository()
    reading = repo.get_reading(reading_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    return reading
