"""Harness uji Supabase LIVE (integrasi #4, Fase A / D1) — versi DEEP.

Dijalankan HANYA bila env staging tersedia; sebaliknya **di-skip**. JANGAN arahkan ke
produksi — gunakan project **staging** + akun/data uji.

Env (dapat diisi via `backend/.env.test`, lihat `.env.test.example`):
    SUPABASE_TEST_URL, SUPABASE_TEST_ANON_KEY, SUPABASE_TEST_SERVICE_ROLE_KEY

Yang diuji di **DB nyata** (bukan in-memory):
1. Skema terpasang (tabel, kolom teacher_id/audio_url/updated_at).
2. **Isolasi RLS lintas-guru**: guru A tidak melihat data guru B (klien anon + JWT guru).
3. **RPC `replace_word_scores`**: pemilik boleh; bukan pemilik ditolak (42501).
4. **Trigger konsistensi `teacher_id`**: nilai melenceng dikoreksi trigger.
4b. **`updated_at` otomatis** (integrasi #5, D1): naik saat update, per tabel mutable;
    ko-eksistensi dengan trigger `teacher_id`.
5. **Storage**: bucket private; policy ber-scope guru (guru lain tak bisa list objek).
5b. **Signed URL audio** (integrasi #5, D3): pemilik dapat mengakses objek; guru lain
    ditolak oleh RLS Storage.

Test membuat user/kelas/siswa/asesmen sementara lalu **membersihkannya** (idempotent).
"""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

import pytest


# ── Muat env dari backend/.env.test (tanpa dependency eksternal) ──

def _load_env_test() -> None:
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


_load_env_test()

URL = os.getenv("SUPABASE_TEST_URL")
ANON = os.getenv("SUPABASE_TEST_ANON_KEY")
SERVICE = os.getenv("SUPABASE_TEST_SERVICE_ROLE_KEY")

pytestmark = pytest.mark.skipif(
    not (URL and ANON and SERVICE),
    reason="butuh SUPABASE_TEST_URL/ANON_KEY/SERVICE_ROLE_KEY (staging) untuk uji live",
)

_PASSWORD = "TestPass123!"


def _admin():
    from supabase import create_client
    return create_client(URL, SERVICE)


def _anon_client():
    from supabase import create_client
    return create_client(URL, ANON)


def _teacher_client(email: str, password: str = _PASSWORD):
    """Klien anon dengan sesi guru (JWT) → RLS mengikuti auth.uid()."""
    c = _anon_client()
    c.auth.sign_in_with_password({"email": email, "password": password})
    return c


@pytest.fixture(scope="module")
def ctx():
    """Buat 2 guru uji + kelas + siswa. Dibersihkan setelah modul selesai."""
    admin = _admin()
    stamp = int(time.time())
    created_users: list[str] = []
    ids: dict[str, str] = {}

    def make_teacher(tag: str) -> str:
        email = f"bacalaras-test-{tag}-{stamp}@example.com"
        u = admin.auth.admin.create_user(
            {"email": email, "password": _PASSWORD, "email_confirm": True}
        )
        uid = u.user.id
        created_users.append(uid)
        admin.table("users").upsert(
            {"id": uid, "name": f"Test {tag}", "email": email}, on_conflict="id"
        ).execute()
        ids[f"teacher_{tag}"] = uid
        ids[f"email_{tag}"] = email
        return uid

    teacher_a = make_teacher("a")
    teacher_b = make_teacher("b")

    cls_a = admin.table("classes").insert(
        {"teacher_id": teacher_a, "name": "Kelas A", "grade": 2}
    ).execute().data[0]["id"]
    stu_a = admin.table("students").insert(
        {"class_id": cls_a, "teacher_id": teacher_a, "name": "Siswa A", "grade": 2}
    ).execute().data[0]["id"]
    ids["class_a"] = cls_a
    ids["student_a"] = stu_a

    cls_b = admin.table("classes").insert(
        {"teacher_id": teacher_b, "name": "Kelas B", "grade": 2}
    ).execute().data[0]["id"]
    stu_b = admin.table("students").insert(
        {"class_id": cls_b, "teacher_id": teacher_b, "name": "Siswa B", "grade": 2}
    ).execute().data[0]["id"]
    ids["class_b"] = cls_b
    ids["student_b"] = stu_b

    # Bacaan uji (global read-only) + asesmen guru A.
    reading = admin.table("reading_texts").insert({
        "title": "Test Reading", "content": "satu dua tiga", "grade": 2,
        "complexity": 1, "book_level": "B1", "word_count": 3,
    }).execute().data[0]["id"]
    ids["reading"] = reading
    asmt_a = admin.table("assessments").insert({
        "student_id": stu_a, "reading_id": reading, "teacher_id": teacher_a,
        "reading_level": 1,
    }).execute().data[0]["id"]
    ids["assessment_a"] = asmt_a

    ids["_admin"] = admin  # simpan untuk teardown
    yield ids

    # Teardown — idempotent; gagal cleanup tidak boleh menutupi hasil test.
    try:
        admin.table("assessments").delete().eq("teacher_id", teacher_a).execute()
        admin.table("reading_texts").delete().eq("id", reading).execute()
        admin.table("students").delete().in_("id", [stu_a, stu_b]).execute()
        admin.table("classes").delete().in_("id", [cls_a, cls_b]).execute()
        admin.table("users").delete().in_("id", created_users).execute()
    except Exception as e:  # noqa: BLE001
        print(f"[live-test] peringatan teardown tabel: {e}")
    # Hapus juga via daftar email (jaring pengaman bila id hilang).
    targets = {*(u for u in created_users), ids.get("teacher_a"), ids.get("teacher_b")}
    for uid in list(targets):
        if not uid:
            continue
        try:
            admin.auth.admin.delete_user(uid)
        except Exception:
            pass
    # Sapu sisa user uji yang mungkin tersisa dari run sebelumnya.
    try:
        for u in admin.auth.admin.list_users():
            if (u.email or "").startswith("bacalaras-test-"):
                admin.auth.admin.delete_user(u.id)
    except Exception:
        pass


# ── 1. Skema terpasang ──

def test_schema_columns_present(ctx):
    admin = _admin()
    admin.table("students").select("id, teacher_id").limit(1).execute()
    admin.table("assessments").select("id, teacher_id, audio_url").limit(1).execute()


def test_unique_word_scores_position(ctx):
    """Unique (assessment_id, position) mencegah duplikat posisi."""
    admin = _admin()
    asmt = ctx["assessment_a"]
    row = {
        "assessment_id": asmt, "position": 1, "reference_word": "satu",
        "attempted": True, "is_correct": True,
    }
    admin.table("word_scores").insert(row).execute()
    with pytest.raises(Exception):
        admin.table("word_scores").insert(row).execute()
    admin.table("word_scores").delete().eq("assessment_id", asmt).execute()


# ── 2. Isolasi RLS lintas-guru ──

def test_rls_isolates_teachers(ctx):
    a = _teacher_client(ctx["email_a"])
    b = _teacher_client(ctx["email_b"])

    a_students = {s["id"] for s in a.table("students").select("id").execute().data}
    b_students = {s["id"] for s in b.table("students").select("id").execute().data}

    assert ctx["student_a"] in a_students, "guru A tidak melihat siswanya sendiri"
    assert ctx["student_a"] not in b_students, "RLS bocor: guru B melihat siswa A"
    assert ctx["student_b"] not in a_students, "RLS bocor: guru A melihat siswa B"


def test_rls_blocks_assessment_read_across_teacher(ctx):
    b = _teacher_client(ctx["email_b"])
    rows = b.table("assessments").select("id").eq("id", ctx["assessment_a"]).execute().data
    assert rows == [], "RLS bocor: guru B membaca asesmen guru A"


# ── 3. RPC replace_word_scores + kepemilikan ──

def test_rpc_owner_can_replace(ctx):
    a = _teacher_client(ctx["email_a"])
    rows = [
        {"position": 1, "reference_word": "satu", "transcript_word": "satu",
         "confidence": 0.9, "attempted": True, "is_correct": True,
         "is_proper_noun": False, "reason": "match", "review_reasons": []},
        {"position": 2, "reference_word": "dua", "transcript_word": "dua",
         "confidence": 0.8, "attempted": True, "is_correct": True,
         "is_proper_noun": False, "reason": "match", "review_reasons": []},
    ]
    a.rpc("replace_word_scores",
          {"p_assessment_id": ctx["assessment_a"], "p_rows": rows}).execute()
    admin = _admin()
    saved = admin.table("word_scores").select("position").eq(
        "assessment_id", ctx["assessment_a"]).execute().data
    assert sorted(r["position"] for r in saved) == [1, 2]


def test_rpc_non_owner_rejected(ctx):
    b = _teacher_client(ctx["email_b"])
    with pytest.raises(Exception) as e:
        b.rpc("replace_word_scores",
              {"p_assessment_id": ctx["assessment_a"],
               "p_rows": [{"position": 9, "attempted": True, "is_correct": True}]}).execute()
    msg = str(e.value).lower()
    assert "42501" in msg or "insufficient" in msg or "bukan milik" in msg or "permission" in msg


# ── 4. Trigger konsistensi teacher_id ──

def test_trigger_forces_student_teacher_id(ctx):
    """INSERT siswa dengan teacher_id SALAH → dikoreksi trigger = teacher kelas."""
    admin = _admin()
    wrong_teacher = ctx["teacher_b"]  # sengaja salah (kelas milik A)
    row = admin.table("students").insert({
        "class_id": ctx["class_a"], "teacher_id": wrong_teacher,
        "name": "Siswa Trigger", "grade": 2,
    }).execute().data[0]
    assert row["teacher_id"] == ctx["teacher_a"], (
        f"trigger tidak mengoreksi teacher_id: {row['teacher_id']}"
    )
    admin.table("students").delete().eq("id", row["id"]).execute()


def test_trigger_forces_assessment_teacher_id(ctx):
    admin = _admin()
    wrong_teacher = ctx["teacher_b"]
    row = admin.table("assessments").insert({
        "student_id": ctx["student_a"], "reading_id": ctx["reading"],
        "teacher_id": wrong_teacher, "reading_level": 1,
    }).execute().data[0]
    assert row["teacher_id"] == ctx["teacher_a"], (
        f"trigger tidak mengoreksi teacher_id asesmen: {row['teacher_id']}"
    )
    admin.table("assessments").delete().eq("id", row["id"]).execute()


# ── 5. Storage ──

def test_storage_bucket_exists_and_private(ctx):
    admin = _admin()
    names = [getattr(b, "name", None) or (b.get("name") if isinstance(b, dict) else None)
             for b in admin.storage.list_buckets()]
    assert "reading-audio" in names, f"bucket tidak ada (ditemukan: {names})"


def test_storage_owner_isolated(ctx):
    """Guru A bisa unggah & lihat objeknya; guru B tidak melihat folder A."""
    a = _teacher_client(ctx["email_a"])
    path = f"{ctx['teacher_a']}/{ctx['assessment_a']}/normalized.wav"
    payload = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 64
    a.storage.from_("reading-audio").upload(
        path, payload, {"content-type": "audio/wav", "upsert": "true"}
    )
    a_objs = a.storage.from_("reading-audio").list(ctx["teacher_a"])
    assert any(o.get("name") == ctx["assessment_a"] for o in a_objs), "guru A tak lihat objeknya"

    b = _teacher_client(ctx["email_b"])
    b_objs = b.storage.from_("reading-audio").list(ctx["teacher_a"])
    assert b_objs == [], "RLS Storage bocor: guru B melihat folder guru A"

    # bersihkan objek uji.
    _admin().storage.from_("reading-audio").remove(
        [f"{ctx['teacher_a']}/{ctx['assessment_a']}/normalized.wav"]
    )


# ── 4b. updated_at otomatis (integrasi #5, D1) ──

def test_updated_at_bumps_on_update_per_table(ctx):
    """UPDATE baris → updated_at naik, untuk tiap tabel mutable."""
    admin = _admin()
    targets = [
        ("users",       {"id": ctx["teacher_a"]},    {"name": "Test A (ubah)"}),
        ("classes",     {"id": ctx["class_a"]},      {"name": "Kelas A (ubah)"}),
        ("students",    {"id": ctx["student_a"]},     {"name": "Siswa A (ubah)"}),
        ("assessments", {"id": ctx["assessment_a"]},  {"recommendation": "ubah"}),
    ]
    for table, match, patch in targets:
        before = (admin.table(table).select("updated_at").match(match)
                  .execute().data[0]["updated_at"])
        time.sleep(1.1)  # pastikan now() bergerak (resolusi detik aman)
        admin.table(table).update(patch).match(match).execute()
        after = (admin.table(table).select("updated_at").match(match)
                 .execute().data[0]["updated_at"])
        assert after and before and after > before, f"{table}: updated_at tidak naik"


def test_updated_at_coexists_with_teacher_trigger(ctx):
    """UPDATE students.class_id → teacher_id terkoreksi (trigger) DAN updated_at naik."""
    admin = _admin()
    before = (admin.table("students").select("updated_at").eq("id", ctx["student_a"])
              .execute().data[0]["updated_at"])
    time.sleep(1.1)
    # pindah siswa A ke kelas B (milik guru B) → trigger harus mengoreksi teacher_id ke B.
    admin.table("students").update({"class_id": ctx["class_b"]}).eq("id", ctx["student_a"]).execute()
    row = admin.table("students").select("teacher_id, updated_at").eq(
        "id", ctx["student_a"]).execute().data[0]
    assert row["teacher_id"] == ctx["teacher_b"], "trigger teacher_id tidak mengoreksi"
    assert row["updated_at"] > before, "updated_at tidak naik saat trigger lain aktif"
    # kembalikan ke kelas A agar test lain (RLS) tetap konsisten.
    admin.table("students").update({"class_id": ctx["class_a"]}).eq("id", ctx["student_a"]).execute()


# ── 5b. audio-url: signed URL ber-scope guru (integrasi #5, D3) ──

def test_signed_url_owner_can_access_object(ctx):
    a = _teacher_client(ctx["email_a"])
    path = f"{ctx['teacher_a']}/{ctx['assessment_a']}/normalized.wav"
    a.storage.from_("reading-audio").upload(
        path, b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 64,
        {"content-type": "audio/wav", "upsert": "true"},
    )
    signed = a.storage.from_("reading-audio").create_signed_url(path, 60)
    if isinstance(signed, dict):
        url = signed.get("signedURL") or signed.get("signed_url")
    else:
        url = getattr(signed, "signed_url", None)
    assert url, "pemilik gagal membuat signed URL"

    import urllib.request

    with urllib.request.urlopen(url) as resp:  # signed URL dapat diakses tanpa JWT
        assert resp.status == 200

    _admin().storage.from_("reading-audio").remove([path])  # bersihkan objek uji


def test_signed_url_non_owner_cannot_access(ctx):
    """Guru B tidak boleh membuat signed URL atas objek guru A (RLS Storage)."""
    a = _teacher_client(ctx["email_a"])
    path = f"{ctx['teacher_a']}/{ctx['assessment_a']}/normalized.wav"
    a.storage.from_("reading-audio").upload(
        path, b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 64,
        {"content-type": "audio/wav", "upsert": "true"},
    )
    b = _teacher_client(ctx["email_b"])
    with pytest.raises(Exception):
        b.storage.from_("reading-audio").create_signed_url(path, 60)
    _admin().storage.from_("reading-audio").remove([path])


# ── 5c. Signed UPLOAD URL (integrasi #6, Fase D, Opsi A) ──

def test_signed_upload_url_roundtrip(ctx):
    """Pemilik terbitkan signed upload URL → PUT langsung → objek tersimpan.

    Ini mekanisme inti Opsi A: browser mengunggah **langsung ke Supabase** (bypass
    batas body Vercel 4.5 MB). Kita buktikan helper produksi
    (`services.audio_storage.create_signed_upload_url`) menghasilkan URL yang dapat
    dipakai PUT tanpa JWT, lalu objeknya benar-benar ada (dibaca via service-role).
    """
    import urllib.request

    from services import audio_storage

    a = _teacher_client(ctx["email_a"])
    path = f"{ctx['teacher_a']}/{ctx['assessment_a']}/normalized.wav"
    payload = b"RIFF\x00\x00\x00\x00WAVE" + b"\xAA" * 128

    signed = audio_storage.create_signed_upload_url(a, path, upsert=True)
    assert signed and signed.get("signed_url"), f"signed upload URL tidak terbit: {signed}"
    url = signed["signed_url"]

    req = urllib.request.Request(
        url, data=payload, method="PUT",
        headers={"content-type": "audio/wav", "x-upsert": "true"},
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status in (200, 201), f"PUT gagal: {resp.status}"

    stored = _admin().storage.from_("reading-audio").download(path)
    assert stored == payload, "objek hasil PUT tidak sesuai"

    _admin().storage.from_("reading-audio").remove([path])  # bersihkan


def test_signed_upload_url_non_owner_rejected(ctx):
    """Guru B tidak boleh menerbitkan signed upload URL atas path guru A (RLS)."""
    from services import audio_storage

    b = _teacher_client(ctx["email_b"])
    path = f"{ctx['teacher_a']}/{ctx['assessment_a']}/normalized.wav"
    # Helper menelan error → None (bukan raise). Inti: TIDAK ada URL terbit.
    assert audio_storage.create_signed_upload_url(b, path, upsert=True) is None


def test_signed_upload_url_upsert_existing_object(ctx):
    """Rekam ulang/retry: terbitkan signed upload untuk objek yang SUDAH ada (upsert).

    Regresi blocker: signed upload dibuat dengan `upsert=true` → saat objek sudah ada,
    Supabase Storage melakukan **UPDATE** → butuh policy `UPDATE` pada `storage.objects`.
    Tanpa policy itu, `create_signed_upload_url` mengembalikan **None** (endpoint 502).
    """
    from services import audio_storage

    a = _teacher_client(ctx["email_a"])
    path = f"{ctx['teacher_a']}/{ctx['assessment_a']}/normalized.wav"
    a.storage.from_("reading-audio").upload(
        path, b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 64,
        {"content-type": "audio/wav", "upsert": "true"},
    )
    try:
        signed = audio_storage.create_signed_upload_url(a, path, upsert=True)
        assert signed and signed.get("signed_url"), (
            "signed upload (upsert objek yang sudah ada) gagal → policy UPDATE "
            "`storage.objects` belum di-apply (endpoint upload-url akan 502)"
        )
    finally:
        _admin().storage.from_("reading-audio").remove([path])



# ── 6. FIX login (integrasi #6, Fase D): policy INSERT `users` ──

def test_teacher_can_upsert_own_profile(ctx):
    """Guru dapat meng-upsert baris `public.users` MILIKNYA (jalur login `_sync_public_user`).

    Regresi blocker: tanpa policy `users_self_insert`, upsert PostgREST
    (INSERT ... ON CONFLICT) ditolak RLS → **login guru selalu 503**. Test ini meniru
    persis panggilan login; ia GAGAL bila policy INSERT belum di-apply.
    """
    a = _teacher_client(ctx["email_a"])
    a.table("users").upsert(
        {"id": ctx["teacher_a"], "name": "Test A", "email": ctx["email_a"]},
        on_conflict="id",
    ).execute()
    row = a.table("users").select("id").eq("id", ctx["teacher_a"]).execute().data
    assert row, "guru tidak dapat meng-upsert profilnya sendiri (login akan 503)"


def test_teacher_cannot_insert_other_profile(ctx):
    """Guru TIDAK boleh membuat baris profil guru lain (batas RLS tetap terjaga)."""
    b = _teacher_client(ctx["email_b"])
    with pytest.raises(Exception):
        b.table("users").insert(
            {"id": ctx["teacher_a"], "name": "Spam", "email": "spam@example.com"}
        ).execute()


# ── 7. Repository per-request JWT (integrasi #6, FIX bug #3) ──

def test_teacher_repository_carries_jwt(ctx, monkeypatch):
    """Regresi bug #3: `get_teacher_repository` membawa JWT guru → RLS `auth.uid()` terisi.

    Tanpa ini, endpoint guru memakai singleton anon-key (tanpa sesi) → RLS memblok
    SEMUA baris → data guru tampak kosong → 404. Bukti di DB nyata:
    - repo per-request (JWT guru) MELIHAT siswa miliknya;
    - singleton anon (kontrol negatif) TIDAK melihat (RLS blok).
    """
    from starlette.requests import Request

    import repository as repo_mod

    monkeypatch.setenv("SUPABASE_URL", URL)
    monkeypatch.setenv("SUPABASE_KEY", ANON)

    c = _anon_client()
    resp = c.auth.sign_in_with_password({"email": ctx["email_a"], "password": _PASSWORD})
    token = resp.session.access_token

    scope = {
        "type": "http", "method": "GET", "path": "/students",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }
    req = Request(scope)

    repo_mod._repo = None
    try:
        teacher_repo = repo_mod.get_teacher_repository(req)
        own = {s["id"] for s in teacher_repo.list_students(teacher_id=ctx["teacher_a"])}
        assert ctx["student_a"] in own, (
            "repo guru (dengan JWT) tidak melihat siswanya sendiri → RLS blok (bug #3)"
        )
        # Isolasi tetap: repo guru A tak melihat siswa guru B.
        assert ctx["student_b"] not in own, "RLS bocor: repo guru A melihat siswa B"

        # Kontrol negatif: singleton anon tanpa JWT → RLS blok → kosong.
        anon_repo = repo_mod.get_repository()
        anon = {s["id"] for s in anon_repo.list_students(teacher_id=ctx["teacher_a"])}
        assert ctx["student_a"] not in anon, "singleton anon seharusnya diblok RLS"
    finally:
        repo_mod._repo = None  # jangan bocorkan singleton ke test lain

