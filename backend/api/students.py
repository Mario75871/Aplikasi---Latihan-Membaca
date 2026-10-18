"""Students API — v2.5.

Integrasi #3 (A.2): semua endpoint di-scope ke guru pemilik (teacher_id dari JWT).
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from api.auth import require_teacher
from repository import Repository, get_teacher_repository

router = APIRouter(prefix="/students", tags=["students"])

class CreateStudentRequest(BaseModel):
    name: str
    grade: int
    class_id: str

@router.get("")
def list_students(request: Request, teacher: str = Depends(require_teacher),
                  repo: Repository = Depends(get_teacher_repository)):
    """GET /students — hanya siswa milik guru."""
    return repo.list_students(teacher_id=teacher)

@router.post("")
def create_student(req: CreateStudentRequest, request: Request,
                   teacher: str = Depends(require_teacher),
                   repo: Repository = Depends(get_teacher_repository)):
    """POST /students — siswa baru dimiliki guru (teacher_id diturunkan dari kelas)."""
    if not req.name:
        raise HTTPException(status_code=422, detail="Name is required")
    if req.grade < 1 or req.grade > 3:
        raise HTTPException(status_code=422, detail="Grade must be 1, 2, or 3")
    # Validasi kelas milik guru (bila kelas ada).
    cls = repo.get_class(req.class_id)
    if cls and cls.get("teacher_id") and cls.get("teacher_id") != teacher:
        raise HTTPException(status_code=403, detail="Kelas bukan milik Anda")
    return repo.create_student(req.name, req.grade, req.class_id, teacher_id=teacher)

@router.get("/{student_id}")
def get_student(student_id: str, request: Request,
                teacher: str = Depends(require_teacher),
                repo: Repository = Depends(get_teacher_repository)):
    """GET /students/{id} — 404 bila bukan milik guru."""
    student = repo.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.get("teacher_id") not in (None, teacher):
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@router.get("/{student_id}/assessments")
def student_assessments(student_id: str, request: Request,
                        teacher: str = Depends(require_teacher),
                        repo: Repository = Depends(get_teacher_repository)):
    """GET /students/{id}/assessments — history terurut waktu (milik guru)."""
    student = repo.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.get("teacher_id") not in (None, teacher):
        raise HTTPException(status_code=404, detail="Student not found")
    return repo.list_student_assessments(student_id)
