"""Readings API — v2.5."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from repository import Repository, get_teacher_repository

router = APIRouter(prefix="/readings", tags=["readings"])


@router.get("")
def list_readings(request: Request, grade: Optional[int] = None,
                  complexity: Optional[int] = None,
                  repo: Repository = Depends(get_teacher_repository)):
    """GET /readings — daftar bacaan, filter opsional."""
    return repo.list_readings(grade=grade, complexity=complexity)


@router.get("/{reading_id}")
def get_reading(reading_id: str, request: Request,
                repo: Repository = Depends(get_teacher_repository)):
    """GET /readings/{id}."""
    reading = repo.get_reading(reading_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    return reading
