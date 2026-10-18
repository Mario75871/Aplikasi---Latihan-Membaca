"""Sign Up API — pendaftaran akun guru secara mandiri (integrasi #7).

Alur tiga langkah, dan **urutannya mengikat**:

1. ``POST /auth/signup/start``   — ``{email, name}``: kirim kode OTP ke email itu.
2. ``POST /auth/signup/verify``  — ``{email, code}``: cocokkan kode → terbitkan **tiket**.
3. ``POST /auth/signup/complete``— ``{ticket, password}``: baru di sini akun dibuat.

Pengguna **belum login** setelah langkah 2. Tiket yang dikembalikan hanya membuktikan
"surel ini sudah diverifikasi" — ia bukan JWT Supabase, tidak dikenali `verify_token`,
dan tidak membuka satu pun endpoint guru. Akun baru lahir di langkah 3, saat password
ada. Rancangan ini menghindari pola bawaan Supabase (`signInWithOtp`) yang memberi
**sesi penuh sebelum password dibuat**, dan menjaga agar token tidak perlu singgah di
state React (cookie httpOnly tetap jadi satu-satunya tempat token).

Seluruh endpoint di sini publik — middleware auth di `main.py` mengecualikan semua
`/auth/*`. Karena itu **tiket, batas laju, dan penghitung percobaan** yang menjadi
penjaganya, bukan middleware.

Keamanan yang dijaga di sini:
- Kode OTP tidak pernah dikembalikan di respons dan tidak pernah dicatat ke log.
- Email yang sudah terdaftar **ditolak di langkah 1**, supaya alur OTP→password tidak
  bisa dipakai mengganti password akun orang lain.
- Kode sekali pakai, berbatas waktu, dan berbatas percobaan.
"""
from __future__ import annotations

import os
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from services import signup_otp
from services.email import EmailDeliveryError, EmailNotConfigured, send_otp_email
from services.rate_limit import client_ip, get_limiter

router = APIRouter(prefix="/auth/signup", tags=["signup"])

#: Panjang minimum password. Supabase sendiri meminta 6; kita lebih ketat.
MIN_PASSWORD_LEN = 8

#: Panjang maksimum — menahan input raksasa sebelum sampai ke Supabase.
MAX_PASSWORD_LEN = 200
MAX_NAME_LEN = 100
MAX_EMAIL_LEN = 254

#: Validasi email yang sengaja konservatif. Bukan parser RFC 5322 lengkap —
#: tujuannya menyaring salah ketik, bukan memutuskan keabsahan; keabsahan sebenarnya
#: dibuktikan oleh kode yang benar-benar sampai ke kotak masuk.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$")


class SignupStartRequest(BaseModel):
    email: str
    name: str


class SignupStartResponse(BaseModel):
    status: str
    email: str
    expires_at: str
    expires_in_sec: int
    resend_after_sec: int


class SignupVerifyRequest(BaseModel):
    email: str
    code: str


class SignupVerifyResponse(BaseModel):
    ticket: str
    email: str
    name: str
    expires_at: str


class SignupCompleteRequest(BaseModel):
    ticket: str
    password: str


class SignupCompleteResponse(BaseModel):
    """**Sengaja identik** dengan `LoginResponse` (`api/auth.py`).

    Frontend memakai ulang `setSessionToken()` yang sudah ada untuk alur login,
    jadi pendaftaran tidak butuh jalur penyimpanan token tersendiri.
    """

    token: str
    username: str
    expires_at: str


# ─────────────────────────────────────────────────────────────
# Penjagaan bersama
# ─────────────────────────────────────────────────────────────

def _require_configured() -> None:
    """503 bila env pendaftaran belum lengkap — bukan 500 yang membingungkan."""
    if not signup_otp.signup_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Pendaftaran akun belum diaktifkan di server ini. "
                "Hubungi administrator."
            ),
        )


def _clean_email(raw: str) -> str:
    email = signup_otp.normalize_email(raw or "")
    if len(email) > MAX_EMAIL_LEN or not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Alamat email tidak valid.")
    return email


def _clean_name(raw: str) -> str:
    name = (raw or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Nama wajib diisi.")
    if len(name) > MAX_NAME_LEN:
        raise HTTPException(
            status_code=422, detail=f"Nama maksimal {MAX_NAME_LEN} karakter."
        )
    return name


def _limit(key: str, limit_name: str) -> None:
    """Catat satu permintaan; 429 bila kuota habis.

    Batas per-IP sudah ditangani middleware (`main._rate_limit_target`). Di sini
    yang dijaga adalah dimensi **per-email**, yang hanya diketahui setelah body
    dibaca — karena itu tidak bisa dikerjakan middleware.
    """
    allowed, retry_after = get_limiter().check(key, limit_name)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak permintaan untuk alamat email ini. Coba lagi sebentar lagi.",
            headers={"Retry-After": str(retry_after)},
        )


# ─────────────────────────────────────────────────────────────
# 1) Mulai — kirim kode OTP
# ─────────────────────────────────────────────────────────────

@router.post("/start", response_model=SignupStartResponse)
def signup_start(req: SignupStartRequest, request: Request):
    """Kirim kode verifikasi ke `req.email`.

    Memanggil ulang endpoint ini untuk email yang sama berfungsi sebagai "kirim ulang":
    kode lama langsung dihanguskan sehingga hanya kode terbaru yang berlaku.
    """
    _require_configured()
    email = _clean_email(req.email)
    name = _clean_name(req.name)

    # Batas per-email sebelum menyentuh DB/email, agar satu alamat tidak bisa
    # dipakai membanjiri kotak masuk orang lain.
    _limit(email, "signup_email")

    # Menolak email terdaftar. Ini menutup jalur "OTP → password" sebagai cara
    # mengganti password akun orang lain.
    try:
        if signup_otp.email_registered(email):
            raise HTTPException(
                status_code=409,
                detail="Email ini sudah terdaftar. Silakan masuk atau gunakan email lain.",
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[signup] ERROR: gagal memeriksa email terdaftar: {e}")
        raise HTTPException(
            status_code=503, detail="Layanan pendaftaran sedang bermasalah. Coba lagi."
        )

    code = signup_otp.generate_code()
    ttl = signup_otp.otp_ttl_sec()
    expires_at = signup_otp.expires_at_iso(ttl)

    try:
        # Urutan penting: hanguskan kode lama SEBELUM menyimpan yang baru, agar tidak
        # ada celah dua kode aktif berdampingan.
        signup_otp.invalidate_open_challenges(email)
        signup_otp.store_challenge(
            email=email,
            code_hash=signup_otp.hash_code(email, code),
            name=name,
            expires_at=expires_at,
            request_ip=client_ip(request),
        )
    except Exception as e:
        print(f"[signup] ERROR: gagal menyimpan tantangan OTP: {e}")
        raise HTTPException(
            status_code=503, detail="Layanan pendaftaran sedang bermasalah. Coba lagi."
        )

    try:
        send_otp_email(to=email, code=code, ttl_min=max(1, ttl // 60))
    except EmailNotConfigured:
        raise HTTPException(
            status_code=503,
            detail="Pengiriman email belum dikonfigurasi di server ini. Hubungi administrator.",
        )
    except EmailDeliveryError as e:
        # Kode tidak sampai ke pengguna; jangan biarkan barisnya menggantung seolah
        # masih bisa diverifikasi.
        print(f"[signup] ERROR: pengiriman OTP gagal: {e}")
        try:
            signup_otp.invalidate_open_challenges(email)
        except Exception:
            pass
        raise HTTPException(
            status_code=502,
            detail="Gagal mengirim email verifikasi. Periksa alamat email lalu coba lagi.",
        )

    return SignupStartResponse(
        status="sent",
        email=email,
        expires_at=expires_at,
        expires_in_sec=ttl,
        resend_after_sec=60,
    )


# ─────────────────────────────────────────────────────────────
# 2) Verifikasi — cocokkan kode, terbitkan tiket
# ─────────────────────────────────────────────────────────────

@router.post("/verify", response_model=SignupVerifyResponse)
def signup_verify(req: SignupVerifyRequest):
    """Cocokkan kode OTP. Sukses → tiket (bukan sesi).

    Penolakan sengaja tidak menjelaskan kode mana yang salah atau berapa digitnya,
    hanya berapa percobaan yang tersisa.
    """
    _require_configured()
    email = _clean_email(req.email)
    code = (req.code or "").strip()

    _limit(email, "signup_verify_email")

    if not code.isdigit():
        raise HTTPException(status_code=400, detail="Kode verifikasi harus berupa angka.")

    try:
        challenge = signup_otp.latest_open_challenge(email)
    except Exception as e:
        print(f"[signup] ERROR: gagal membaca tantangan OTP: {e}")
        raise HTTPException(
            status_code=503, detail="Layanan pendaftaran sedang bermasalah. Coba lagi."
        )

    if challenge is None:
        raise HTTPException(
            status_code=400,
            detail="Kode tidak ditemukan atau sudah kedaluwarsa. Minta kode baru.",
        )

    attempts = int(challenge.get("attempts") or 0)
    if attempts >= signup_otp.max_attempts():
        # Habis percobaan → kode dimatikan, harus minta yang baru.
        _safe(signup_otp.consume_challenge, challenge["id"])
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak percobaan salah. Minta kode baru.",
        )

    if not signup_otp.code_matches(email, code, challenge.get("code_hash", "")):
        next_attempts = attempts + 1
        _safe(signup_otp.bump_attempts, challenge["id"], next_attempts)
        remaining = max(0, signup_otp.max_attempts() - next_attempts)
        if remaining == 0:
            _safe(signup_otp.consume_challenge, challenge["id"])
            raise HTTPException(
                status_code=429,
                detail="Terlalu banyak percobaan salah. Minta kode baru.",
            )
        raise HTTPException(
            status_code=400,
            detail=f"Kode verifikasi salah. Sisa percobaan: {remaining}.",
        )

    # Kode benar → sekali pakai.
    _safe(signup_otp.consume_challenge, challenge["id"])

    ticket, expires_at = signup_otp.issue_ticket(email, challenge.get("name") or "")
    return SignupVerifyResponse(
        ticket=ticket,
        email=email,
        name=challenge.get("name") or "",
        expires_at=expires_at,
    )


# ─────────────────────────────────────────────────────────────
# 3) Selesai — buat akun, langsung terbitkan sesi
# ─────────────────────────────────────────────────────────────

@router.post("/complete", response_model=SignupCompleteResponse)
def signup_complete(req: SignupCompleteRequest):
    """Buat akun di Supabase Auth, lalu langsung login.

    Identitas tetap di Supabase Auth — bukan tabel sendiri — karena seluruh RLS
    (`users_self_select`, `classes_owner_all`, …) bersandar pada `auth.uid()`.
    Akun yang dibuat di luar sana akan membuat `auth.uid()` null dan menyembunyikan
    seluruh data guru.
    """
    _require_configured()

    try:
        claims = signup_otp.verify_ticket(req.ticket or "")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    email = _clean_email(claims["email"])
    name = (claims.get("name") or "").strip() or email.split("@")[0]

    password = req.password or ""
    if len(password) < MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=422,
            detail=f"Password minimal {MIN_PASSWORD_LEN} karakter.",
        )
    if len(password) > MAX_PASSWORD_LEN:
        raise HTTPException(
            status_code=422, detail=f"Password maksimal {MAX_PASSWORD_LEN} karakter."
        )

    admin = _admin_auth_client()
    try:
        admin.auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True}
        )
    except Exception as e:
        if _is_email_exists(e):
            raise HTTPException(
                status_code=409,
                detail="Email ini sudah terdaftar. Silakan masuk.",
            )
        print(f"[signup] ERROR: gagal membuat user Supabase: {e}")
        raise HTTPException(
            status_code=503,
            detail="Akun tidak dapat dibuat saat ini. Coba lagi sebentar lagi.",
        )

    # Login pakai jalur yang sama dengan /auth/login, supaya bentuk respons, umur
    # token, dan uji coba yang sudah ada tetap berlaku. `display_name` memastikan
    # `public.users.name` berisi nama asli, bukan email.
    from api.auth import _supabase_login

    try:
        session = _supabase_login(email, password, display_name=name)
    except HTTPException as e:
        # Akun SUDAH dibuat pada titik ini — katakan apa adanya, jangan "kredensial
        # tidak valid" yang menyesatkan dan membuat pengguna mendaftar ulang.
        if e.status_code == 401:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Akun berhasil dibuat, tetapi login otomatis gagal. "
                    "Silakan masuk lewat halaman login."
                ),
            )
        raise

    if session is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Akun berhasil dibuat, tetapi login otomatis tidak tersedia. "
                "Silakan masuk lewat halaman login."
            ),
        )

    return SignupCompleteResponse(
        token=session["token"],
        username=session["email"],
        expires_at=session["expires_at"],
    )


def _admin_auth_client():
    """Klien Supabase dengan **service-role** untuk `auth.admin.create_user`.

    Wajib service-role: `admin.create_user` menolak anon key. Klien ini hanya hidup
    di dalam fungsi ini dan tidak pernah menyentuh respons.
    """
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and service_key):
        raise HTTPException(
            status_code=503, detail="Pendaftaran belum dikonfigurasi di server ini."
        )
    from supabase import create_client

    return create_client(url, service_key)


def _is_email_exists(exc: Exception) -> bool:
    """Deteksi penolakan 'email sudah dipakai' dari GoTrue/Supabase.

    Diperiksa dari kode galat maupun pesannya karena bentuknya berbeda antar versi
    pustaka. Kekeliruan ke arah False hanya berarti 503 alih-alih 409 — tidak fatal.
    """
    code = getattr(exc, "code", None)
    if code in ("email_exists", "user_already_exists"):
        return True
    text = str(exc).lower()
    return "already" in text and ("registered" in text or "exists" in text)


def _safe(fn, *args) -> None:
    """Jalankan operasi housekeeping; kegagalannya tidak boleh menggagalkan permintaan.

    Dipakai untuk penandaan `consumed_at` / penghitung percobaan: bila ini gagal,
    yang terburuk adalah kode hidup sedikit lebih lama — bukan alasan membalas 500
    kepada pengguna yang kodenya sudah benar.
    """
    try:
        fn(*args)
    except Exception as e:
        print(f"[signup] peringatan: {getattr(fn, '__name__', 'operasi')} gagal: {e}")
