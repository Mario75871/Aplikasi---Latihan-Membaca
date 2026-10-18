"""Seed runner — muat data ke Supabase (Fase 1.4).

TERPISAH dari ``seed/validate.py`` (yang hanya memvalidasi). Skrip ini menulis
seed ke tabel Supabase (kanonis): ``reading_texts``, ``reading_questions``,
``classes``, ``students``.

Karakteristik:
- Idempotent: memakai ``upsert`` (on_conflict="id") sehingga aman dijalankan
  berulang tanpa menghasilkan duplikat.
- ``classes.teacher_id`` & ``students.teacher_id`` diisi guru demo tetap (D3,
  integrasi #3) — lihat ``load_users``. Ganti/arahkan ke guru sungguhan di produksi.
- Pertanyaan reading di-``delete`` lalu insert ulang agar konsisten dengan
  konten terbaru (reading_questions tidak punya unique constraint).

Jalankan::

    python -m seed.load_supabase

Butuh env ``SUPABASE_URL`` dan (disarankan) ``SUPABASE_SERVICE_ROLE_KEY`` (klien
admin, bypass RLS). Fallback: ``SUPABASE_KEY`` untuk dev/lokal tanpa RLS.
"""
from __future__ import annotations

import os
import sys

from seed.reading_texts import (
    READING_TEXTS,
    SEED_CLASSES,
    SEED_STUDENTS,
)
from seed.validator import validate_all


def _client():
    """Klien ADMIN (service-role) untuk seed — bypass RLS (D1 hybrid, integrasi #3).

    Memprioritaskan SUPABASE_SERVICE_ROLE_KEY; fallback ke SUPABASE_KEY (dev/lokal,
    bila RLS belum aktif).
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not (url and key):
        raise RuntimeError(
            "SUPABASE_URL dan (SUPABASE_SERVICE_ROLE_KEY atau SUPABASE_KEY) wajib "
            "diisi untuk load seed."
        )
    from supabase import create_client
    return create_client(url, key)


def _reading_row(reading: dict) -> dict:
    """Baris untuk tabel reading_texts (kolom sesuai skema kanonis)."""
    return {
        "id": reading["id"],
        "title": reading["title"],
        "content": reading["content"],
        "grade": reading["grade"],
        "complexity": reading["complexity"],
        "book_level": reading["book_level"],
        "word_count": len(reading["content"].split()),
        "theme": reading.get("theme"),
        "proper_nouns": reading.get("proper_nouns", []),
        "version": reading.get("version", "v1"),
    }


def _question_rows(reading: dict) -> list[dict]:
    return [
        {
            "reading_id": reading["id"],
            "competency": q["competency"],
            "prompt": q["prompt"],
            "options": q["options"],
            "answer_id": q["answer_id"],
            "position": i,
        }
        for i, q in enumerate(reading.get("questions", []))
    ]


def load_readings(client) -> int:
    """Upsert reading_texts + sinkronkan reading_questions. Kembalikan jumlah teks."""
    for reading in READING_TEXTS:
        client.table("reading_texts").upsert(
            _reading_row(reading), on_conflict="id"
        ).execute()
        # reading_questions: bersihkan lalu insert ulang (idempotent).
        client.table("reading_questions").delete().eq("reading_id", reading["id"]).execute()
        rows = _question_rows(reading)
        if rows:
            client.table("reading_questions").insert(rows).execute()
    return len(READING_TEXTS)


def load_users(client) -> int:
    """Upsert guru demo ke public.users (kepemilikan data seed — D3, integrasi #3).

    Catatan: baris ini BUKAN auth.users nyata; hanya pemilik data seed agar
    kelas/siswa demo punya teacher_id konsisten. Hilangkan di produksi bila tidak
    diinginkan (atau arahkan ke guru sungguhan).
    """
    from seed.reading_texts import SEED_IDS
    teacher_id = SEED_IDS["teacher_demo"]
    client.table("users").upsert(
        {"id": teacher_id, "name": "Guru Demo", "email": "guru@demo.com"},
        on_conflict="id",
    ).execute()
    return 1


def load_classes(client) -> int:
    """Upsert classes (teacher_id dari seed — D3, integrasi #3)."""
    for c in SEED_CLASSES:
        client.table("classes").upsert(
            {"id": c["id"], "name": c["name"], "grade": c["grade"],
             "teacher_id": c.get("teacher_id")},
            on_conflict="id",
        ).execute()
    return len(SEED_CLASSES)


def load_students(client) -> int:
    """Upsert students (termasuk teacher_id — D3, integrasi #3)."""
    for s in SEED_STUDENTS:
        client.table("students").upsert(
            {"id": s["id"], "name": s["name"], "grade": s["grade"],
             "class_id": s["class_id"], "teacher_id": s.get("teacher_id")},
            on_conflict="id",
        ).execute()
    return len(SEED_STUDENTS)


def main() -> int:
    # Validasi dulu — jangan muat data yang melanggar batas level.
    errors = validate_all(READING_TEXTS)
    if errors:
        print(f"[GAGAL] Validasi seed: {len(errors)} error:")
        for e in errors:
            print(f"  - {e}")
        return 1

    try:
        client = _client()
    except RuntimeError as e:
        print(f"[GAGAL] {e}")
        return 1

    print(f"Memuat seed ke Supabase...")
    n_readings = load_readings(client)
    n_users = load_users(client)
    n_classes = load_classes(client)
    n_students = load_students(client)
    print(
        f"[OK] Seed dimuat: {n_readings} bacaan, {n_users} guru, {n_classes} kelas, "
        f"{n_students} siswa (idempotent — aman dijalankan ulang)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
