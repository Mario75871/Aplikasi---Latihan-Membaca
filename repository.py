"""Repository pattern — dual implementation (in-memory + Supabase).

Default: in-memory (untuk test/demo).
Bila SUPABASE_URL dan SUPABASE_KEY tersedia → Supabase.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from models.assessment import (
    AssessmentResult,
    ComprehensionResult,
    ReadingText,
    Student,
    WordScore,
)


class Repository(ABC):
    """Interface repository."""

    # Students
    @abstractmethod
    def get_student(self, student_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_students(self) -> list[dict]:
        pass

    @abstractmethod
    def create_student(self, name: str, grade: int, class_id: str) -> dict:
        pass

    # Readings
    @abstractmethod
    def get_reading(self, reading_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_readings(self, grade: Optional[int] = None, complexity: Optional[int] = None) -> list[dict]:
        pass

    # Assessments
    @abstractmethod
    def create_assessment(self, student_id: str, reading_id: str) -> dict:
        pass

    @abstractmethod
    def get_assessment(self, assessment_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def update_assessment(self, assessment_id: str, data: dict) -> dict:
        pass

    @abstractmethod
    def list_student_assessments(self, student_id: str) -> list[dict]:
        pass

    @abstractmethod
    def list_all_assessments(self) -> list[dict]:
        pass

    # Classes
    @abstractmethod
    def get_class(self, class_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_classes(self) -> list[dict]:
        pass

    @abstractmethod
    def create_class(self, name: str, grade: int) -> dict:
        pass


class InMemoryRepository(Repository):
    """In-memory repository (default, untuk test/demo)."""

    def __init__(self):
        self.students = {}
        self.readings = {}
        self.assessments = {}
        self.classes = {}
        self._seed_data()

    def _seed_data(self):
        """Seed data demo."""
        # Classes
        self.classes["cls-2a"] = {"id": "cls-2a", "name": "Kelas 2A", "grade": 2}
        self.classes["cls-1a"] = {"id": "cls-1a", "name": "Kelas 1A", "grade": 1}
        self.classes["cls-3a"] = {"id": "cls-3a", "name": "Kelas 3A", "grade": 3}

        # Students
        self.students["std-001"] = {"id": "std-001", "name": "Dika Pratama", "grade": 2, "class_id": "cls-2a"}
        self.students["std-002"] = {"id": "std-002", "name": "Sari Anggraini", "grade": 2, "class_id": "cls-2a"}
        self.students["std-003"] = {"id": "std-003", "name": "Boni Santoso", "grade": 3, "class_id": "cls-3a"}
        self.students["std-004"] = {"id": "std-004", "name": "Rani Wulandari", "grade": 1, "class_id": "cls-1a"}

        # Readings dari seed
        try:
            from seed.reading_texts import READING_TEXTS
            for r in READING_TEXTS:
                self.readings[r["id"]] = dict(r)
        except ImportError:
            # Fallback minimal bila seed tidak tersedia
            self.readings["rd-001"] = {
                "id": "rd-001",
                "title": "Ke Pasar Bersama Ibu",
                "content": "Ibu pergi ke pasar setiap pagi. Ibu membeli sayur dan buah. Dika ikut membantu ibu. Mereka pulang dengan gembira.",
                "grade": 2, "complexity": 2, "book_level": "B2", "word_count": 24,
                "theme": "Keluarga", "proper_nouns": ["Ibu", "Dika"], "questions": [],
            }

    def get_student(self, student_id: str) -> Optional[dict]:
        return self.students.get(student_id)

    def list_students(self) -> list[dict]:
        return list(self.students.values())

    def create_student(self, name: str, grade: int, class_id: str) -> dict:
        sid = f"std-{len(self.students) + 1:03d}"
        self.students[sid] = {"id": sid, "name": name, "grade": grade, "class_id": class_id}
        return self.students[sid]

    def get_reading(self, reading_id: str) -> Optional[dict]:
        return self.readings.get(reading_id)

    def list_readings(self, grade: Optional[int] = None, complexity: Optional[int] = None) -> list[dict]:
        result = list(self.readings.values())
        if grade:
            result = [r for r in result if r.get("grade") == grade]
        if complexity:
            result = [r for r in result if r.get("complexity") == complexity]
        return result

    def create_assessment(self, student_id: str, reading_id: str) -> dict:
        aid = f"asmt-{len(self.assessments) + 1:03d}"
        self.assessments[aid] = {
            "id": aid,
            "student_id": student_id,
            "reading_id": reading_id,
            "status": "PENDING",
            "session_state": "DRAFT",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return self.assessments[aid]

    def get_assessment(self, assessment_id: str) -> Optional[dict]:
        return self.assessments.get(assessment_id)

    def update_assessment(self, assessment_id: str, data: dict) -> dict:
        if assessment_id not in self.assessments:
            raise ValueError(f"Assessment {assessment_id} not found")
        self.assessments[assessment_id].update(data)
        return self.assessments[assessment_id]

    def list_student_assessments(self, student_id: str) -> list[dict]:
        result = [a for a in self.assessments.values() if a.get("student_id") == student_id]
        # Sort by created_at descending
        result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return result

    def list_all_assessments(self) -> list[dict]:
        result = list(self.assessments.values())
        result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return result

    def get_class(self, class_id: str) -> Optional[dict]:
        return self.classes.get(class_id)

    def list_classes(self) -> list[dict]:
        return list(self.classes.values())

    def create_class(self, name: str, grade: int) -> dict:
        cid = f"cls-{len(self.classes) + 1:03d}"
        self.classes[cid] = {"id": cid, "name": name, "grade": grade}
        return self.classes[cid]


class SupabaseRepository(Repository):
    """Supabase repository (bila env tersedia)."""

    def __init__(self, url: str, key: str):
        try:
            from supabase import create_client, Client
            self.client: Client = create_client(url, key)
        except Exception as e:
            raise RuntimeError(f"Supabase client initialization failed: {e}")

    def get_student(self, student_id: str) -> Optional[dict]:
        resp = self.client.table("students").select("*").eq("id", student_id).execute()
        return resp.data[0] if resp.data else None

    def list_students(self) -> list[dict]:
        resp = self.client.table("students").select("*").execute()
        return resp.data

    def create_student(self, name: str, grade: int, class_id: str) -> dict:
        data = {"name": name, "grade": grade, "class_id": class_id}
        resp = self.client.table("students").insert(data).execute()
        return resp.data[0]

    def get_reading(self, reading_id: str) -> Optional[dict]:
        resp = self.client.table("readings").select("*").eq("id", reading_id).execute()
        return resp.data[0] if resp.data else None

    def list_readings(self, grade: Optional[int] = None, complexity: Optional[int] = None) -> list[dict]:
        query = self.client.table("readings").select("*")
        if grade:
            query = query.eq("grade", grade)
        if complexity:
            query = query.eq("complexity", complexity)
        resp = query.execute()
        return resp.data

    def create_assessment(self, student_id: str, reading_id: str) -> dict:
        data = {"student_id": student_id, "reading_id": reading_id, "status": "PENDING"}
        resp = self.client.table("assessments").insert(data).execute()
        return resp.data[0]

    def get_assessment(self, assessment_id: str) -> Optional[dict]:
        resp = self.client.table("assessments").select("*").eq("id", assessment_id).execute()
        return resp.data[0] if resp.data else None

    def update_assessment(self, assessment_id: str, data: dict) -> dict:
        resp = self.client.table("assessments").update(data).eq("id", assessment_id).execute()
        return resp.data[0]

    def list_student_assessments(self, student_id: str) -> list[dict]:
        resp = self.client.table("assessments").select("*").eq("student_id", student_id).order("created_at", desc=True).execute()
        return resp.data

    def list_all_assessments(self) -> list[dict]:
        resp = self.client.table("assessments").select("*").order("created_at", desc=True).execute()
        return resp.data

    def get_class(self, class_id: str) -> Optional[dict]:
        resp = self.client.table("classes").select("*").eq("id", class_id).execute()
        return resp.data[0] if resp.data else None

    def list_classes(self) -> list[dict]:
        resp = self.client.table("classes").select("*").execute()
        return resp.data

    def create_class(self, name: str, grade: int) -> dict:
        data = {"name": name, "grade": grade}
        resp = self.client.table("classes").insert(data).execute()
        return resp.data[0]


# Global repository instance
_repo: Optional[Repository] = None


def get_repository() -> Repository:
    """Get repository instance (singleton)."""
    global _repo
    if _repo is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if supabase_url and supabase_key:
            print("[repository] Using Supabase repository")
            _repo = SupabaseRepository(supabase_url, supabase_key)
        else:
            print("[repository] Using in-memory repository (demo mode)")
            _repo = InMemoryRepository()
    
    return _repo
