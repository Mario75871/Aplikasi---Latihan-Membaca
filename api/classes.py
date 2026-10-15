"""Classes API — manajemen kelas (F-02, v2.5)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from repository import get_repository

router = APIRouter(prefix="/classes", tags=["classes"])


class CreateClassRequest(BaseModel):
    name: str
    grade: int


@router.get("")
def list_classes():
    """GET /classes — daftar kelas."""
    repo = get_repository()
    return repo.list_classes()


@router.post("")
def create_class(req: CreateClassRequest):
    """POST /classes — buat kelas baru."""
    repo = get_repository()
    if not req.name:
        raise HTTPException(status_code=422, detail="Nama kelas wajib diisi")
    if req.grade < 1 or req.grade > 3:
        raise HTTPException(status_code=422, detail="Grade harus 1, 2, atau 3")
    return repo.create_class(req.name, req.grade)


@router.get("/{class_id}")
def get_class(class_id: str):
    """GET /classes/{id} — detail kelas."""
    repo = get_repository()
    cls = repo.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    return cls


@router.get("/{class_id}/students")
def class_students(class_id: str):
    """GET /classes/{id}/students — daftar siswa kelas."""
    repo = get_repository()
    cls = repo.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    students = [s for s in repo.list_students() if s.get("class_id") == class_id]
    return students
