"""Classes API — manajemen kelas (F-02, v2.5).

Integrasi #3 (A.2): semua endpoint di-scope ke guru pemilik.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from api.auth import require_teacher
from repository import Repository, get_teacher_repository

router = APIRouter(prefix="/classes", tags=["classes"])

class CreateClassRequest(BaseModel):
    name: str
    grade: int

@router.get("")
def list_classes(request: Request, teacher: str = Depends(require_teacher),
                 repo: Repository = Depends(get_teacher_repository)):
    """GET /classes — hanya kelas milik guru."""
    return repo.list_classes(teacher_id=teacher)

@router.post("")
def create_class(req: CreateClassRequest, request: Request,
                 teacher: str = Depends(require_teacher),
                 repo: Repository = Depends(get_teacher_repository)):
    """POST /classes — kelas baru dimiliki guru."""
    if not req.name:
        raise HTTPException(status_code=422, detail="Nama kelas wajib diisi")
    if req.grade < 1 or req.grade > 3:
        raise HTTPException(status_code=422, detail="Grade harus 1, 2, atau 3")
    return repo.create_class(req.name, req.grade, teacher_id=teacher)

@router.get("/{class_id}")
def get_class(class_id: str, request: Request,
              teacher: str = Depends(require_teacher),
              repo: Repository = Depends(get_teacher_repository)):
    """GET /classes/{id} — 404 bila bukan milik guru."""
    cls = repo.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls.get("teacher_id") not in (None, teacher):
        raise HTTPException(status_code=404, detail="Class not found")
    return cls

@router.get("/{class_id}/students")
def class_students(class_id: str, request: Request,
                   teacher: str = Depends(require_teacher),
                   repo: Repository = Depends(get_teacher_repository)):
    """GET /classes/{id}/students — daftar siswa kelas (milik guru)."""
    cls = repo.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls.get("teacher_id") not in (None, teacher):
        raise HTTPException(status_code=404, detail="Class not found")
    students = [s for s in repo.list_students(teacher_id=teacher)
                if s.get("class_id") == class_id]
    return students
