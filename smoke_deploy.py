"""smoke_deploy.py — Smoke test end-to-end lintas-deploy (BacaLaras).

Menguji jalur PERSIS seperti browser sungguhan:
    Browser → Vercel (/api/proxy, same-origin) → Backend (server ini) → Supabase

Yang diverifikasi:
  1.  GET  {VFE}/api/proxy/health                    → 200 (proxy → backend)
  2.  POST {VFE}/api/proxy/auth/login                → JWT guru
  3.  POST {VFE}/api/session                         → cookie httpOnly + Secure
  4.  POST {VFE}/api/proxy/assessments               → buat asesmen
  5.  POST {VFE}/api/proxy/assessments/{id}/audio/upload-url → signed URL
  6.  PUT  <signed_url>                              → unggah LANGSUNG ke Supabase
  7.  POST {VFE}/api/proxy/assessments/{id}/audio {audio_path} → pipeline → hasil
  8.  PUT  >4.5 MB ke signed_url                     → bukti bypass batas body Vercel
  9.  PUT  ulang objek yang sama (upsert)            → sukses

Data uji sementara (guru/kelas/siswa/teks/asesmen) dibuat & dibersihkan sendiri
via service-role. Jalankan HANYA terhadap project Supabase yang benar.

--- CARA PAKAI ---
Butuh (via env atau file .env.test):
    SUPABASE_TEST_URL               (atau SUPABASE_URL)
    SUPABASE_TEST_SERVICE_ROLE_KEY  (atau SUPABASE_SERVICE_ROLE_KEY)
    VFE   = origin frontend Vercel  (default https://bacalaras-frontend.vercel.app)
    SMOKE_WAV = path file .wav kecil (opsional; default dibuat otomatis)

Contoh:
    set -a && source backend/.env.test && set +a
    VFE=https://bacalaras-frontend.vercel.app python smoke_deploy.py

Dependensi: pip install supabase   (sudah ada di requirements.txt backend)
"""
from __future__ import annotations

import json
import os
import struct
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

VFE = os.environ.get("VFE", "https://bacalaras-frontend.vercel.app").rstrip("/")
PASSWORD = os.environ.get("SMOKE_PASSWORD", "SmokeTest123!")


def _load_env_file() -> None:
    """Muat .env.test (opsional) agar tak perlu export manual."""
    for candidate in (
        os.environ.get("SMOKE_ENV_FILE"),
        "backend/.env.test",
        ".env.test",
        "/opt/bacalaras/backend/.env.test",
    ):
        if not candidate:
            continue
        p = Path(candidate)
        if p.is_file():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
            return


_load_env_file()

URL = os.environ.get("SUPABASE_TEST_URL") or os.environ.get("SUPABASE_URL")
SERVICE = (
    os.environ.get("SUPABASE_TEST_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)
if not URL or not SERVICE:
    raise SystemExit(
        "Butuh SUPABASE_TEST_URL & SUPABASE_TEST_SERVICE_ROLE_KEY "
        "(atau SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)."
    )

from supabase import create_client  # noqa: E402

admin = create_client(URL, SERVICE)

# Cookie jar → meniru browser (cookie sesi httpOnly ikut terkirim ke /api/proxy).
_jar = CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))


def _make_wav(seconds: float = 0.5, sr: int = 16000) -> bytes:
    """WAV PCM16 mono senyap — agar tidak bergantung file lokal."""
    n = int(sr * seconds)
    data = b"\x00\x00" * n
    header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16)
    header += b"data" + struct.pack("<I", len(data))
    return header + data


def http(method, path, *, token=None, data=None, headers=None, raw=None, timeout=300):
    """Panggil app Vercel (bukan backend langsung). Cookie jar ikut otomatis."""
    h = {"accept": "application/json"}
    if headers:
        h.update(headers)
    if token:
        h["authorization"] = f"Bearer {token}"
    body = None
    if raw is not None:
        body = raw
    elif data is not None:
        body = json.dumps(data).encode()
        h["content-type"] = "application/json"
    req = urllib.request.Request(f"{VFE}{path}", data=body, method=method, headers=h)
    try:
        with _opener.open(req, timeout=timeout) as r:
            txt = r.read()
            return r.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        txt = e.read()
        try:
            payload = json.loads(txt) if txt else None
        except Exception:
            payload = txt.decode(errors="replace")
        return e.code, payload


def put_direct(url, payload, ctype="audio/wav"):
    req = urllib.request.Request(
        url, data=payload, method="PUT",
        headers={"content-type": ctype, "x-upsert": "true"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main() -> int:
    stamp = int(time.time())
    email = f"bacalaras-smoke-{stamp}@example.com"
    created = {"users": [], "classes": [], "students": [], "readings": [], "assessments": []}
    results = []

    def check(name, cond, extra=""):
        results.append((name, bool(cond), extra))
        print(f"[{'PASS' if cond else 'FAIL'}] {name} {extra}")

    try:
        # --- Setup via service-role ---
        u = admin.auth.admin.create_user(
            {"email": email, "password": PASSWORD, "email_confirm": True}
        )
        uid = u.user.id
        created["users"].append(uid)
        admin.table("users").upsert(
            {"id": uid, "name": "Smoke", "email": email}, on_conflict="id"
        ).execute()
        cls = admin.table("classes").insert(
            {"teacher_id": uid, "name": "Kelas Smoke", "grade": 2}
        ).execute().data[0]["id"]
        created["classes"].append(cls)
        stu = admin.table("students").insert(
            {"class_id": cls, "teacher_id": uid, "name": "Siswa Smoke", "grade": 2}
        ).execute().data[0]["id"]
        created["students"].append(stu)
        rd = admin.table("reading_texts").insert({
            "title": "Smoke Reading", "content": "satu dua tiga", "grade": 2,
            "complexity": 1, "book_level": "B1", "word_count": 3,
        }).execute().data[0]["id"]
        created["readings"].append(rd)

        # --- 1. proxy health ---
        st, h = http("GET", "/api/proxy/health")
        check("proxy → backend /health 200",
              st == 200 and (h or {}).get("status") == "ok", f"(status={st})")

        # --- 2. login guru lewat proxy ---
        st, lg = http("POST", "/api/proxy/auth/login",
                      data={"username": email, "password": PASSWORD})
        token = (lg or {}).get("token")
        check("login guru via proxy 200 + JWT", st == 200 and bool(token), f"(status={st})")

        # --- 3. set cookie sesi (httpOnly, Secure) ---
        st, _ = http("POST", "/api/session", data={"token": token})
        tok_cookie = {c.name: c for c in _jar}.get("bacalaras_token")
        check("cookie sesi ter-set (httpOnly+Secure)",
              st == 200 and tok_cookie is not None and bool(tok_cookie.secure),
              f"(status={st}, secure={getattr(tok_cookie, 'secure', None)})")

        # --- 4. buat asesmen ---
        st, asmt = http("POST", "/api/proxy/assessments",
                        data={"student_id": stu, "reading_id": rd})
        ok = st == 200 and isinstance(asmt, dict) and asmt.get("id")
        check("create assessment via proxy 200", ok, f"(status={st})")
        aid = asmt["id"]
        created["assessments"].append(aid)

        # --- 5. upload-url ---
        st, up = http("POST", f"/api/proxy/assessments/{aid}/audio/upload-url")
        ok_signed = st == 200 and (up or {}).get("mode") == "signed" and up.get("signed_url")
        check("upload-url → mode=signed", ok_signed,
              f"(status={st}, mode={(up or {}).get('mode')})")
        path = (up or {}).get("path", "")
        check("path berprefix {teacher}/{assessment}/",
              path.startswith(f"{uid}/{aid}/"), f"(path={path})")

        # --- 6. PUT LANGSUNG ke Supabase ---
        wav_path = os.environ.get("SMOKE_WAV")
        payload = Path(wav_path).read_bytes() if wav_path and Path(wav_path).is_file() else _make_wav()
        st = put_direct(up["signed_url"], payload)
        check("PUT langsung ke Supabase 200/201", st in (200, 201), f"(status={st})")
        stored = admin.storage.from_("reading-audio").download(path)
        check("objek tersimpan di Storage", stored == payload,
              f"(len={len(stored) if stored else 0})")

        # --- 7. POST /audio {audio_path} → pipeline ---
        st, res = http("POST", f"/api/proxy/assessments/{aid}/audio",
                       data={"audio_path": path}, timeout=300)
        ok_pipe = st == 200 and isinstance(res, dict) and res.get("session_state")
        check("pipeline via audio_path 200", ok_pipe,
              f"(status={st}, state={(res or {}).get('session_state')})")
        if isinstance(res, dict):
            check("audio_url = path (tak diunggah ulang)", res.get("audio_url") == path)
            check("hasil punya wcpm/accuracy",
                  res.get("wcpm") is not None and res.get("accuracy") is not None,
                  f"(wcpm={res.get('wcpm')}, acc={res.get('accuracy')})")

        # --- 8. PUT >4.5 MB (bukti bypass batas body Vercel) ---
        st, asmt2 = http("POST", "/api/proxy/assessments",
                         data={"student_id": stu, "reading_id": rd})
        check("create assessment #2 200", st == 200 and (asmt2 or {}).get("id"),
              f"(status={st})")
        aid2 = asmt2["id"]
        created["assessments"].append(aid2)
        st, up2 = http("POST", f"/api/proxy/assessments/{aid2}/audio/upload-url")
        big = b"RIFF\x00\x00\x00\x00WAVE" + os.urandom(5 * 1024 * 1024)
        st2 = put_direct(up2["signed_url"], big)
        check("PUT >4.5 MB via signed URL sukses",
              st2 in (200, 201) and len(big) > 4_500_000,
              f"(status={st2}, size={len(big)})")

        # --- 9. rekam ulang (upsert objek yang sudah ada) ---
        st, up3 = http("POST", f"/api/proxy/assessments/{aid2}/audio/upload-url")
        if st == 200 and (up3 or {}).get("signed_url"):
            st3 = put_direct(up3["signed_url"], big)
            check("rekam ulang (upsert) objek sama sukses", st3 in (200, 201),
                  f"(status={st3})")
        else:
            check("rekam ulang (upsert) objek sama sukses", False, f"(status={st})")

    finally:
        try:
            for aid in created["assessments"]:
                admin.table("assessments").delete().eq("id", aid).execute()
            for rd in created["readings"]:
                admin.table("reading_texts").delete().eq("id", rd).execute()
            if created["students"]:
                admin.table("students").delete().in_("id", created["students"]).execute()
            if created["classes"]:
                admin.table("classes").delete().in_("id", created["classes"]).execute()
            for u in created["users"]:
                admin.table("users").delete().eq("id", u).execute()
        except Exception as e:
            print(f"[cleanup] tabel: {e}")
        try:
            for u in created["users"]:
                for aid in created["assessments"]:
                    admin.storage.from_("reading-audio").remove([f"{u}/{aid}/normalized.wav"])
        except Exception as e:
            print(f"[cleanup] storage: {e}")
        for u in created["users"]:
            try:
                admin.auth.admin.delete_user(u)
            except Exception:
                pass

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n==== SMOKE: {passed}/{len(results)} PASS ====")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
