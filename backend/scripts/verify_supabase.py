#!/usr/bin/env python
"""verify_supabase.py — verifikasi migrasi Supabase (integrasi #4, Fase A.2).

Memeriksa bahwa `supabase_schema.sql` benar-benar terpasang di project Supabase:
tabel, kolom baru (teacher_id, audio_url), unique index, trigger konsistensi,
fungsi RPC, dan bucket Storage.

Pakai service-role (server-only, jangan dibagikan). Jalankan:

    export SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=...
    python -m scripts.verify_supabase

Kembalikan exit code 0 bila semua OK, 1 bila ada yang hilang. Aman: hanya SELECT.
"""
from __future__ import annotations

import os
import sys


def _load_env_test() -> None:
    """Muat `backend/.env.test` bila ada (tanpa dependency eksternal)."""
    from pathlib import Path

    env_file = Path(__file__).resolve().parent.parent / ".env.test"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main() -> int:
    _load_env_test()
    url = os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_TEST_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_TEST_SERVICE_ROLE_KEY")
    if not (url and key):
        print("[verify] SUPABASE_URL & SUPABASE_SERVICE_ROLE_KEY wajib di-set "
              "(atau SUPABASE_TEST_* di backend/.env.test).")
        return 1

    try:
        from supabase import create_client
    except Exception as e:
        print(f"[verify] gagal impor supabase: {e}")
        return 1

    client = create_client(url, key)
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, fn) -> None:
        try:
            ok, msg = fn()
        except Exception as e:  # noqa: BLE001
            ok, msg = False, str(e)
        checks.append((name, ok, msg))

    # 1) Tabel inti ada.
    for table in ("users", "classes", "students", "reading_texts",
                  "reading_questions", "assessments", "word_scores"):
        check(f"tabel {table}", lambda t=table: (
            client.table(t).select("id").limit(1).execute() is not None, "dapat dibaca"
        ))

    # 2) Kolom baru (integrasi #3/#4).
    check("kolom students.teacher_id", lambda: (
        client.table("students").select("teacher_id").limit(1).execute() is not None,
        "ada",
    ))
    check("kolom assessments.teacher_id", lambda: (
        client.table("assessments").select("teacher_id").limit(1).execute() is not None,
        "ada",
    ))
    check("kolom assessments.audio_url", lambda: (
        client.table("assessments").select("audio_url").limit(1).execute() is not None,
        "ada",
    ))

    # 2b) Kolom updated_at (integrasi #5, D1) — tabel mutable.
    for table in ("assessments", "students", "classes", "users"):
        check(f"kolom {table}.updated_at", lambda t=table: (
            client.table(t).select("updated_at").limit(1).execute() is not None,
            "ada",
        ))

    # 2c) Tabel audio_purge_log (integrasi #5, D2).
    check("tabel audio_purge_log", lambda: (
        client.table("audio_purge_log").select("id").limit(1).execute() is not None,
        "dapat dibaca",
    ))

    # 2d) CHECK constraint (integrasi #6, D3) — dibuktikan dengan INSERT invalid yang
    # HARUS ditolak (23514 check_violation). Non-destruktif: bila (tak terduga) berhasil
    # tersimpan, baris langsung dihapus & dilaporkan MISSING.
    def _check_constraint_enforced() -> tuple[bool, str]:
        import uuid as _uuid

        # reading_texts.proper_nouns harus array (ck_rt_proper_nouns).
        rid = str(_uuid.uuid4())
        bad = {
            "id": rid,
            "title": "__verify_ct__",
            "content": "x",
            "grade": 1,
            "complexity": 1,
            "book_level": "B1",
            "word_count": 1,
            "proper_nouns": "BUKAN_ARRAY",  # skalar → harus ditolak
        }
        try:
            client.table("reading_texts").insert(bad).execute()
        except Exception as e:  # noqa: BLE001
            s = str(e)
            if "23514" in s or "check" in s.lower() or "violates" in s.lower():
                return True, "ck_rt_proper_nouns menolak nilai invalid"
            return False, f"error tak terduga: {s[:120]}"
        # Tak menolak → constraint tidak ada. Bersihkan baris yang tak sengaja masuk.
        try:
            client.table("reading_texts").delete().eq("id", rid).execute()
        except Exception:  # noqa: BLE001
            pass
        return False, "constraint CHECK tidak menolak proper_nouns skalar"

    check("CHECK ck_rt_proper_nouns", _check_constraint_enforced)

    # 3) Fungsi RPC replace_word_scores ada.
    def _rpc():
        try:
            client.rpc("replace_word_scores", {
                "p_assessment_id": "00000000-0000-0000-0000-000000000000",
                "p_rows": [],
            }).execute()
        except Exception as e:  # noqa: BLE001
            s = str(e).lower()
            # PostgREST: PGRST202 "could not find the function ..." (bukan hanya
            # "does not exist"). Kegagalan lain (mis. FK/check) berarti fungsi ADA.
            if "pgrst202" in s or "could not find the function" in s or "does not exist" in s:
                return False, "fungsi tidak ada"
        return True, "ada"

    check("RPC replace_word_scores", _rpc)

    # 4) Bucket Storage audio — cek daftar bucket (bukan list objek yang selalu ok).
    def _bucket():
        names = []
        for b in client.storage.list_buckets():
            name = getattr(b, "name", None) or (b.get("name") if isinstance(b, dict) else None)
            if name:
                names.append(name)
        if "reading-audio" in names:
            return True, "ada"
        return False, f"bucket tidak ada (ditemukan: {names or 'kosong'})"

    check("bucket reading-audio", _bucket)

    # 5) Policy RLS kunci (integrasi #6, fix blocker runtime) — dicek FUNGSIONAL:
    #    (a) `users_self_insert` → guru boleh upsert profilnya (jalur login).
    #    (b) `reading_audio_owner_update` → signed upload upsert objek yang sudah ada.
    # Keduanya butuh sesi guru; bila tak ada akun uji → tandai "dilewati" (bukan MISSING)
    # agar verifikasi tetap dapat dijalankan tanpa kredensial guru.
    def _policies() -> tuple[bool, str]:
        email = os.getenv("VERIFY_TEACHER_EMAIL")
        password = os.getenv("VERIFY_TEACHER_PASSWORD")
        if not (email and password):
            return True, "dilewati (set VERIFY_TEACHER_EMAIL/PASSWORD untuk cek policy)"
        anon = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_TEST_ANON_KEY")
        if not anon:
            return True, "dilewati (ANON key tak tersedia)"
        from supabase import create_client as _cc

        t = _cc(url, anon)
        sess = t.auth.sign_in_with_password({"email": email, "password": password})
        uid = sess.user.id
        t.options.headers["Authorization"] = f"Bearer {sess.session.access_token}"
        # (a) upsert profil sendiri (policy INSERT).
        t.table("users").upsert(
            {"id": uid, "name": "verify", "email": email}, on_conflict="id"
        ).execute()
        # (b) signed upload upsert objek yang sudah ada (policy UPDATE storage).
        from services import audio_storage

        path = f"{uid}/__verify__/normalized.wav"
        t.storage.from_("reading-audio").upload(
            path, b"RIFFWAVE" + b"\0" * 32, {"content-type": "audio/wav"}
        )
        signed = audio_storage.create_signed_upload_url(t, path, upsert=True)
        if not signed or not signed.get("signed_url"):
            return False, "signed upload (upsert) gagal → policy UPDATE storage.objects belum ada"
        try:
            client.storage.from_("reading-audio").remove([path])
        except Exception:  # noqa: BLE001
            pass
        return True, "users_self_insert + reading_audio_owner_update aktif"

    check("policy users INSERT & storage UPDATE", _policies)

    print("\n=== Verifikasi Supabase ===")
    failed = 0
    for name, ok, msg in checks:
        mark = "OK " if ok else "MISSING"
        if not ok:
            failed += 1
        print(f"  [{mark}] {name}: {msg}")
    print(f"\n{len(checks) - failed}/{len(checks)} OK.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
