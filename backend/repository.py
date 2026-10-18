"""Repository pattern — dual implementation (in-memory + Supabase).

Default: in-memory (untuk test/demo).
Bila SUPABASE_URL dan SUPABASE_KEY tersedia → Supabase.

Fase 0/1 (integrasi Supabase):
- Nama tabel mengikuti skema kanonis: ``reading_texts`` (+ ``reading_questions``).
- ``word_scores`` disimpan di TABEL relasional, bukan JSON di assessments.
- ID memakai uuid di kedua implementasi (in-memory memakai uuid4 / uuid tetap seed).
"""
from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request


class Repository(ABC):
    """Interface repository."""

    # Students
    @abstractmethod
    def get_student(self, student_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_students(self, teacher_id: Optional[str] = None) -> list[dict]:
        pass

    @abstractmethod
    def create_student(self, name: str, grade: int, class_id: str,
                       teacher_id: Optional[str] = None) -> dict:
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
    def create_assessment(self, student_id: str, reading_id: str,
                          reading_level: Optional[int] = None,
                          teacher_id: Optional[str] = None) -> dict:
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
    def list_all_assessments(self, teacher_id: Optional[str] = None) -> list[dict]:
        pass

    # Word scores (Fase 0: tabel relasional)
    @abstractmethod
    def save_word_scores(self, assessment_id: str, words: list[dict]) -> None:
        pass

    @abstractmethod
    def list_word_scores(self, assessment_id: str) -> list[dict]:
        pass

    # Classes
    @abstractmethod
    def get_class(self, class_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_classes(self, teacher_id: Optional[str] = None) -> list[dict]:
        pass

    @abstractmethod
    def create_class(self, name: str, grade: int,
                     teacher_id: Optional[str] = None) -> dict:
        pass


#: Kolom tabel word_scores pada skema Supabase (source kanonis).
_WORD_SCORE_FIELDS = (
    "position", "reference_word", "transcript_word", "confidence",
    "attempted", "is_correct", "is_proper_noun", "reason",
    "review_reasons", "ts_start", "ts_end",
)


def _word_row(word: dict) -> dict:
    """Normalisasi satu WordScore dict → baris tabel ``word_scores``."""
    return {k: word.get(k) for k in _WORD_SCORE_FIELDS}


class InMemoryRepository(Repository):
    """In-memory repository (default, untuk test/demo). Memakai uuid."""

    def __init__(self):
        self.students = {}
        self.readings = {}
        self.assessments = {}
        self.classes = {}
        self.word_scores = {}  # assessment_id -> list[dict]
        self._seed_data()

    def _seed_data(self):
        """Seed data demo (uuid tetap, sesuai seed/reading_texts.py)."""
        from seed.reading_texts import SEED_CLASSES, SEED_STUDENTS

        for c in SEED_CLASSES:
            self.classes[c["id"]] = dict(c)
        for s in SEED_STUDENTS:
            self.students[s["id"]] = dict(s)

        # Readings dari seed
        try:
            from seed.reading_texts import READING_TEXTS
            for r in READING_TEXTS:
                self.readings[r["id"]] = dict(r)
        except ImportError:
            # Fallback minimal bila seed tidak tersedia
            fallback_id = "00000000-0000-0000-0000-000000000099"
            self.readings[fallback_id] = {
                "id": fallback_id,
                "title": "Ke Pasar Bersama Ibu",
                "content": "Ibu pergi ke pasar setiap pagi. Ibu membeli sayur dan buah. Dika ikut membantu ibu. Mereka pulang dengan gembira.",
                "grade": 2, "complexity": 2, "book_level": "B2", "word_count": 24,
                "theme": "Keluarga", "proper_nouns": ["Ibu", "Dika"], "questions": [],
            }

    def get_student(self, student_id: str) -> Optional[dict]:
        return self.students.get(student_id)

    def list_students(self, teacher_id: Optional[str] = None) -> list[dict]:
        students = list(self.students.values())
        if teacher_id is not None:
            students = [s for s in students if s.get("teacher_id") == teacher_id]
        return students

    def create_student(self, name: str, grade: int, class_id: str,
                       teacher_id: Optional[str] = None) -> dict:
        sid = str(uuid.uuid4())
        # D3: denormalisasi teacher_id dari kelas bila tidak diberikan.
        if teacher_id is None:
            cls = self.classes.get(class_id)
            teacher_id = (cls or {}).get("teacher_id")
        self.students[sid] = {"id": sid, "name": name, "grade": grade,
                              "class_id": class_id, "teacher_id": teacher_id}
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

    def create_assessment(self, student_id: str, reading_id: str,
                          reading_level: Optional[int] = None,
                          teacher_id: Optional[str] = None) -> dict:
        aid = str(uuid.uuid4())
        # reading_level NOT NULL di skema kanonis → simpan kompleksitas bacaan.
        if reading_level is None:
            reading = self.readings.get(reading_id)
            reading_level = (reading or {}).get("complexity", 1)
        # D3: denormalisasi teacher_id dari siswa.
        if teacher_id is None:
            student = self.students.get(student_id)
            teacher_id = (student or {}).get("teacher_id")
        self.assessments[aid] = {
            "id": aid,
            "student_id": student_id,
            "reading_id": reading_id,
            "reading_level": reading_level,
            "teacher_id": teacher_id,  # D3
            "status": None,  # D.1: status diisi saat COMPLETED (bukan "PENDING")
            "session_state": "DRAFT",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return self.assessments[aid]

    def get_assessment(self, assessment_id: str) -> Optional[dict]:
        asmt = self.assessments.get(assessment_id)
        if asmt is None:
            return None
        # Gabungkan word_scores dari tabel relasional → bentuk respons tak berubah.
        merged = dict(asmt)
        merged["word_scores"] = self.list_word_scores(assessment_id)
        return merged

    def update_assessment(self, assessment_id: str, data: dict) -> dict:
        if assessment_id not in self.assessments:
            raise ValueError(f"Assessment {assessment_id} not found")
        # word_scores bukan kolom assessments → buang bila ikut terkirim.
        data = {k: v for k, v in data.items() if k != "word_scores"}
        self.assessments[assessment_id].update(data)
        return self.get_assessment(assessment_id)

    def list_student_assessments(self, student_id: str) -> list[dict]:
        result = [a for a in self.assessments.values() if a.get("student_id") == student_id]
        # Sort by created_at descending
        result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return result

    def list_all_assessments(self, teacher_id: Optional[str] = None) -> list[dict]:
        result = list(self.assessments.values())
        if teacher_id is not None:
            result = [a for a in result if a.get("teacher_id") == teacher_id]
        result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return result

    def save_word_scores(self, assessment_id: str, words: list[dict]) -> None:
        self.word_scores[assessment_id] = [_word_row(w) for w in (words or [])]

    def list_word_scores(self, assessment_id: str) -> list[dict]:
        return list(self.word_scores.get(assessment_id, []))

    def get_class(self, class_id: str) -> Optional[dict]:
        return self.classes.get(class_id)

    def list_classes(self, teacher_id: Optional[str] = None) -> list[dict]:
        classes = list(self.classes.values())
        if teacher_id is not None:
            classes = [c for c in classes if c.get("teacher_id") == teacher_id]
        return classes

    def create_class(self, name: str, grade: int,
                     teacher_id: Optional[str] = None) -> dict:
        cid = str(uuid.uuid4())
        self.classes[cid] = {"id": cid, "name": name, "grade": grade,
                             "teacher_id": teacher_id}  # D3
        return self.classes[cid]


def _apply_teacher_token(client, access_token: str) -> None:
    """Tempelkan JWT guru ke klien Supabase (postgrest **dan** storage).

    Integrasi #6 (fix bug #3): `postgrest.auth()` hanya memperbarui header postgrest.
    Klien **Storage** di supabase-py dibuat *lazily* dari ``client.options.headers``,
    sehingga tanpa menyetel header di sana, permintaan Storage memakai anon key →
    RLS Storage menolak (403) walau endpoint sudah lolos verifikasi kepemilikan.

    Kita setel ``options.headers["Authorization"]`` (menjangkau kedua klien yang belum
    dibuat) **dan** panggil ``postgrest.auth()`` (bila klien postgrest sudah telanjur
    dibuat). Tahan-versi: setiap langkah best-effort.
    """
    auth = f"Bearer {access_token}"
    try:
        client.options.headers["Authorization"] = auth
    except Exception:
        pass
    try:
        client.postgrest.auth(access_token)
    except Exception:
        pass
    try:
        # Bila klien Storage sudah terlanjur dibuat, perbarui headernya langsung.
        storage = getattr(client, "_storage", None)
        if storage is not None:
            storage._headers["authorization"] = auth
            storage._headers["Authorization"] = auth
    except Exception:
        pass


def _is_uuid(value: object) -> bool:
    """True bila ``value`` berbentuk UUID.

    Semua kolom ``id`` di skema Supabase bertipe ``uuid`` (lihat ``supabase_schema.sql``).
    Mengirim string sembarang ke ``.eq("id", ...)`` membuat Postgres melempar
    "invalid input syntax for type uuid" → endpoint menjawab **500**, padahal arti
    sebenarnya adalah "tidak ditemukan" (**404**). Penjaga ini mengubahnya jadi
    "tidak ada baris yang cocok" tanpa perlu menebak isi pesan galat Postgres.

    Catatan: id yang sah tapi tidak ada di basis data tetap lewat (→ ``None``),
    jadi perilaku normal tidak berubah; hanya bentuk yang mustahil ada yang ditolak.
    """
    try:
        uuid.UUID(str(value))
    except (AttributeError, TypeError, ValueError):
        return False
    return True


class SupabaseRepository(Repository):
    """Supabase repository (bila env tersedia).

    Integrasi #3 (D1 hybrid): klien ini memakai **anon key** (RLS ditegakkan). Jalur
    admin/seed memakai klien terpisah dengan **service-role** (lihat get_admin_client()).
    Isolasi per-guru ditegakkan di dua lapis: (1) filter `teacher_id` di kueri (kode),
    (2) RLS policy (database).
    """

    def __init__(self, url: str, key: str, access_token: Optional[str] = None):
        try:
            from supabase import create_client, Client
            self.client: Client = create_client(url, key)
            # Bila ada token guru → pakai sesi tersebut agar RLS mengikuti auth.uid().
            # PENTING (integrasi #6, fix bug #3): setel `options.headers["Authorization"]`
            # SEBELUM klien postgrest/storage dibuat (keduanya lazily-init dari headers
            # ini). `postgrest.auth()` saja TIDAK cukup — klien Storage tetap memakai
            # anon key → RLS Storage menolak (403).
            if access_token:
                _apply_teacher_token(self.client, access_token)
        except Exception as e:
            raise RuntimeError(f"Supabase client initialization failed: {e}")

    def get_student(self, student_id: str) -> Optional[dict]:
        if not _is_uuid(student_id):   # bentuk mustahil → "tidak ditemukan", bukan 500
            return None
        resp = self.client.table("students").select("*").eq("id", student_id).execute()
        return resp.data[0] if resp.data else None

    def list_students(self, teacher_id: Optional[str] = None) -> list[dict]:
        query = self.client.table("students").select("*")
        if teacher_id is not None:
            query = query.eq("teacher_id", teacher_id)
        resp = query.execute()
        return resp.data

    def create_student(self, name: str, grade: int, class_id: str,
                       teacher_id: Optional[str] = None) -> dict:
        # D3: denormalisasi teacher_id dari kelas bila tidak diberikan.
        if teacher_id is None:
            cls = self.get_class(class_id) or {}
            teacher_id = cls.get("teacher_id")
        data = {"name": name, "grade": grade, "class_id": class_id,
                "teacher_id": teacher_id}
        resp = self.client.table("students").insert(data).execute()
        return resp.data[0]

    def get_reading(self, reading_id: str) -> Optional[dict]:
        if not _is_uuid(reading_id):   # bentuk mustahil → "tidak ditemukan", bukan 500
            return None
        resp = self.client.table("reading_texts").select("*").eq("id", reading_id).execute()
        if not resp.data:
            return None
        reading = dict(resp.data[0])
        reading["questions"] = self._questions_for(reading_id)
        return reading

    def _questions_for(self, reading_id: str) -> list[dict]:
        """Ambil reading_questions (skema memisahkan pertanyaan)."""
        resp = (
            self.client.table("reading_questions")
            .select("*").eq("reading_id", reading_id).order("position")
            .execute()
        )
        return resp.data or []

    def list_readings(self, grade: Optional[int] = None, complexity: Optional[int] = None) -> list[dict]:
        query = self.client.table("reading_texts").select("*")
        if grade:
            query = query.eq("grade", grade)
        if complexity:
            query = query.eq("complexity", complexity)
        resp = query.execute()
        return resp.data

    def create_assessment(self, student_id: str, reading_id: str,
                          reading_level: Optional[int] = None,
                          teacher_id: Optional[str] = None) -> dict:
        # reading_level NOT NULL di skema kanonis → wajib diisi.
        if reading_level is None:
            reading = self.get_reading(reading_id)
            reading_level = (reading or {}).get("complexity", 1)
        # D3: denormalisasi teacher_id dari siswa.
        if teacher_id is None:
            student = self.get_student(student_id) or {}
            teacher_id = student.get("teacher_id")
        data = {
            "student_id": student_id,
            "reading_id": reading_id,
            "reading_level": reading_level,
            "teacher_id": teacher_id,   # D3
            # D.1: status diisi saat COMPLETED. Skema hanya mengizinkan 4 nilai F-08;
            # jangan kirim "PENDING" (akan melanggar check constraint).
            "status": None,
        }
        resp = self.client.table("assessments").insert(data).execute()
        return resp.data[0]

    def get_assessment(self, assessment_id: str) -> Optional[dict]:
        if not _is_uuid(assessment_id):   # bentuk mustahil → "tidak ditemukan", bukan 500
            return None
        resp = self.client.table("assessments").select("*").eq("id", assessment_id).execute()
        if not resp.data:
            return None
        merged = dict(resp.data[0])
        # Gabungkan word_scores dari tabel relasional → bentuk respons tak berubah.
        merged["word_scores"] = self.list_word_scores(assessment_id)
        return merged

    def update_assessment(self, assessment_id: str, data: dict) -> dict:
        # word_scores bukan kolom assessments → buang bila ikut terkirim.
        data = {k: v for k, v in data.items() if k != "word_scores"}
        resp = self.client.table("assessments").update(data).eq("id", assessment_id).execute()
        return self.get_assessment(assessment_id)

    def list_student_assessments(self, student_id: str) -> list[dict]:
        if not _is_uuid(student_id):   # bentuk mustahil → daftar kosong, bukan 500
            return []
        resp = self.client.table("assessments").select("*").eq("student_id", student_id).order("created_at", desc=True).execute()
        return resp.data

    def list_all_assessments(self, teacher_id: Optional[str] = None) -> list[dict]:
        query = self.client.table("assessments").select("*")
        if teacher_id is not None:
            query = query.eq("teacher_id", teacher_id)
        resp = query.order("created_at", desc=True).execute()
        return resp.data

    def save_word_scores(self, assessment_id: str, words: list[dict]) -> None:
        """Ganti word_scores secara ATOMIK via RPC (integrasi #3, B.2).

        Memakai fungsi Postgres ``replace_word_scores`` (delete+insert dalam satu
        transaksi) sehingga kegagalan di tengah tidak menghapus data lama. Fallback
        ke jalur non-atomik bila RPC tidak tersedia (mis. Supabase lama/dev).
        """
        rows = [_word_row(w) for w in (words or [])]
        try:
            self.client.rpc(
                "replace_word_scores",
                {"p_assessment_id": assessment_id, "p_rows": rows},
            ).execute()
            return
        except Exception as e:
            print(f"[repository] RPC replace_word_scores gagal ({e}); fallback non-atomik")
        # Fallback: bersihkan lalu insert (bukan transaksi).
        self.client.table("word_scores").delete().eq("assessment_id", assessment_id).execute()
        if rows:
            payload = [{"assessment_id": assessment_id, **r} for r in rows]
            self.client.table("word_scores").insert(payload).execute()

    def list_word_scores(self, assessment_id: str) -> list[dict]:
        if not _is_uuid(assessment_id):   # bentuk mustahil → daftar kosong, bukan 500
            return []
        resp = (
            self.client.table("word_scores").select("*")
            .eq("assessment_id", assessment_id).order("position")
            .execute()
        )
        return resp.data or []

    def get_class(self, class_id: str) -> Optional[dict]:
        if not _is_uuid(class_id):   # bentuk mustahil → "tidak ditemukan", bukan 500
            return None
        resp = self.client.table("classes").select("*").eq("id", class_id).execute()
        return resp.data[0] if resp.data else None

    def list_classes(self, teacher_id: Optional[str] = None) -> list[dict]:
        query = self.client.table("classes").select("*")
        if teacher_id is not None:
            query = query.eq("teacher_id", teacher_id)
        resp = query.execute()
        return resp.data

    def create_class(self, name: str, grade: int,
                     teacher_id: Optional[str] = None) -> dict:
        data = {"name": name, "grade": grade, "teacher_id": teacher_id}  # D3
        resp = self.client.table("classes").insert(data).execute()
        return resp.data[0]


# Global repository instance
_repo: Optional[Repository] = None


def get_admin_repository() -> "SupabaseRepository":
    """Klien ADMIN (service-role) — BYPASS RLS. Server-only (seed/admin).

    Integrasi #3, D1 hybrid: jalur admin/seed memakai service-role. JANGAN dipakai
    untuk melayani permintaan guru (akan melewati RLS).
    """
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not (supabase_url and service_key):
        raise RuntimeError(
            "SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY wajib untuk klien admin."
        )
    return SupabaseRepository(supabase_url, service_key)


def get_repository() -> Repository:
    """Get repository instance (singleton).

    Integrasi #3, D1 hybrid: jalur guru memakai **anon key** (RLS ditegakkan).
    Service-role hanya lewat `get_admin_repository()` (server-only).

    Catatan (integrasi #6, fix bug #3): singleton ini TIDAK membawa sesi guru, jadi
    `auth.uid()` di RLS bernilai null. **Endpoint yang melayani guru harus memakai
    `get_teacher_repository` (dependency per-request)**, bukan fungsi ini. Fungsi ini
    tetap dipakai untuk health/ready (probe ringan) dan mode in-memory/demo.
    """
    global _repo
    if _repo is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if supabase_url and supabase_key:
            print("[repository] Using Supabase repository (anon key + RLS)")
            _repo = SupabaseRepository(supabase_url, supabase_key)
        else:
            print("[repository] Using in-memory repository (demo mode)")
            _repo = InMemoryRepository()

    return _repo


def _bearer_token(request: "Request") -> Optional[str]:
    """Ekstrak token dari header ``Authorization: Bearer <token>`` (tanpa dependensi api.auth)."""
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_teacher_repository(request: "Request") -> Repository:
    """Repository **per-request** untuk jalur guru — membawa JWT guru (RLS `auth.uid()`).

    Integrasi #6 (fix bug #3): `get_repository()` mengembalikan singleton anon-key
    TANPA sesi guru → RLS menolak semua baris (``auth.uid()`` null) → data guru
    (students/assessments/classes) tampak kosong → endpoint 404. Dependency ini
    membuat klien Supabase **per-request** dengan JWT guru sehingga RLS berjalan
    sesuai desain integrasi #3 (B.1: "repository menerima user context/JWT guru").

    - Mode in-memory/demo (tanpa Supabase) → singleton in-memory (perilaku lama).
    - Mode Supabase + JWT guru → `SupabaseRepository` baru dengan token guru.
    - Mode Supabase tanpa JWT (mis. AUTH_DISABLED) → singleton anon; endpoint tetap
      memfilter `teacher_id` (RLS jadi lapis kedua).
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not (supabase_url and supabase_key):
        return get_repository()  # in-memory/demo

    token = _bearer_token(request)
    if not token:
        return get_repository()
    return SupabaseRepository(supabase_url, supabase_key, access_token=token)


def teacher_supabase_client(access_token: Optional[str]):
    """Klien Supabase dengan sesi guru (untuk Supabase **Storage** ber-RLS).

    Integrasi #4 (B.4): policy Storage men-scope prefix folder = ``auth.uid()``. Untuk
    itu klien harus membawa JWT guru. Kembalikan ``None`` bila env/token tidak ada
    (mis. mode in-memory/demo) — pemanggil menangani sebagai "tidak tersedia".
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not (supabase_url and supabase_key and access_token):
        return None
    try:
        from supabase import create_client
        client = create_client(supabase_url, supabase_key)
        # Integrasi #6 (fix bug #3): JANGAN akses `client.storage` sebelum header
        # disetel — klien Storage lazily-init dari options.headers. Setel header dulu.
        _apply_teacher_token(client, access_token)
        return client
    except Exception as e:  # pragma: no cover
        print(f"[repository] peringatan: gagal membuat klien Storage guru: {e}")
        return None
