"""Students API — v2.5."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from repository import get_repository

router = APIRouter(prefix="/students", tags=["students"])


class CreateStudentRequest(BaseModel):
    name: str
    grade: int
    class_id: str


@router.get("")
def list_students():
    """GET /students."""
    repo = get_repository()
    return repo.list_students()


@router.post("")
def create_student(req: CreateStudentRequest):
    """POST /students."""
    repo = get_repository()
    if not req.name:
        raise HTTPException(status_code=422, detail="Name is required")
    if req.grade < 1 or req.grade > 3:
        raise HTTPException(status_code=422, detail="Grade must be 1, 2, or 3")
    return repo.create_student(req.name, req.grade, req.class_id)


@router.get("/{student_id}")
def get_student(student_id: str):
    """GET /students/{id}."""
    repo = get_repository()
    student = repo.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/{student_id}/assessments")
def student_assessments(student_id: str):
    """GET /students/{id}/assessments — history terurut waktu."""
    repo = get_repository()
    # Verify student exists
    student = repo.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return repo.list_student_assessments(student_id)
