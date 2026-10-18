"""BacaLaras — FastAPI entrypoint (v2.5)."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import (
    assessments,
    auth,
    classes,
    config,
    dashboard,
    hasbrouck,
    readings,
    signup,
    students,
)
from services.speech import load_whisper_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load Whisper model + validasi env saat startup (integrasi #4, C.3)."""
    from api.env_validation import validate_environment
    from logging_config import get_logger, setup_logging

    setup_logging()  # integrasi #5, D5: logging terstruktur JSON
    log = get_logger("main")

    warnings = validate_environment()  # raise RuntimeError bila konfigurasi berbahaya
    for w in warnings:
        log.warning("env_peringatan", extra={"msg_extra": w})

    log.info("startup BacaLaras API v2.5")
    load_whisper_model()
    yield
    log.info("shutdown BacaLaras API")


app = FastAPI(
    title="BacaLaras API",
    version="2.5",
    description=(
        "Adaptive Oral Reading Fluency & Literacy Assessment. "
        "Model #1 (reading_framework + faster-whisper): transkrip + alignment + confidence per kata. "
        "Model #2 (scoring.py): penilaian kata benar/salah dari alignment. "
        "Adaptive Engine: rule-based (BR-01..BR-05, BR-07, BR-08)."
    ),
    lifespan=lifespan,
)

# CORS: batasi lewat env (jangan * di produksi)
_cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware auth: endpoint selain /health, /ready dan /auth/* butuh token (D7)
_PUBLIC_PATHS = {"/health", "/ready", "/docs", "/openapi.json", "/redoc"}


def _rate_limit_target(path: str, method: str) -> str | None:
    """Tentukan nama limit untuk (path, method), atau None bila tak dibatasi."""
    if path == "/auth/login" and method == "POST":
        return "login_ip"
    # Pendaftaran (integrasi #7): batas per-IP di sini; batas per-EMAIL ditegakkan
    # di dalam endpoint karena butuh membaca body (`api/signup.py`).
    if path == "/auth/signup/start" and method == "POST":
        return "signup_ip"
    if path == "/auth/signup/verify" and method == "POST":
        return "signup_verify_ip"
    if path.startswith("/assessments/") and path.endswith("/audio") and method == "POST":
        return "audio"  # dicek per-guru DAN per-IP di middleware
    if path.startswith("/assessments/") and method == "GET":
        return "poll_teacher"
    return None


def _token_user_id(request: Request) -> str | None:
    """Ambil user_id ringan dari token (tanpa round-trip Supabase) — untuk limiter.

    Token demo lokal → kunci per-username. JWT Supabase → klaim 'sub' didekode TANPA
    verifikasi tanda tangan (hanya untuk kunci rate-limit; verifikasi sebenarnya tetap
    dilakukan auth middleware). Gagal dekode → None (batas per-IP tetap berlaku).
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    from api import auth

    token = auth._extract_token(authorization)
    if not token:
        return None
    if token.startswith(auth._LOCAL_TOKEN_PREFIX):
        session = auth._local_tokens.get(token)
        return f"local:{session.get('username', 'demo')}" if session else None
    try:
        import base64
        import json

        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        sub = claims.get("sub")
        return f"jwt:{sub}" if sub else None
    except Exception:
        return None


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting per-IP & per-guru (integrasi #4, D4).

    Dijalankan SEBELUM auth middleware agar /auth/login juga terlindungi. Batas
    per-guru hanya berlaku bila identitas sudah tersedia (via header Authorization);
    karena middleware ini berjalan sebelum auth, kita verifikasi ringan di sini.
    """
    from services.rate_limit import client_ip, get_limiter

    path = request.url.path
    method = request.method
    target = _rate_limit_target(path, method)
    if target is None:
        return await call_next(request)

    limiter = get_limiter()
    ip = client_ip(request)

    def _reject(retry_after: int) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Terlalu banyak permintaan. Coba lagi sebentar lagi.",
            },
            headers={"Retry-After": str(retry_after)},
        )

    # Batas murni per-IP: login & pendaftaran (`signup_ip`, `signup_verify_ip`).
    # Batas per-email tidak bisa dikerjakan di sini — body belum dibaca.
    if target in ("login_ip", "signup_ip", "signup_verify_ip"):
        allowed, retry = limiter.check(ip, target)
        if not allowed:
            return _reject(retry)
        return await call_next(request)

    if target == "poll_teacher":
        user_id = _token_user_id(request)
        if user_id:
            allowed, retry = limiter.check(user_id, "poll_teacher")
            if not allowed:
                return _reject(retry)
        return await call_next(request)

    # target == "audio": batas per-guru DAN per-IP.
    user_id = _token_user_id(request)
    if user_id:
        allowed, retry = limiter.check(user_id, "audio_teacher")
        if not allowed:
            return _reject(retry)
    allowed, retry = limiter.check(ip, "audio_ip")
    if not allowed:
        return _reject(retry)
    return await call_next(request)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Proteksi endpoint: butuh token kecuali /health dan /auth/* (D7)."""
    path = request.url.path

    # Bila auth di-disable (untuk test/dev), lewati
    if os.getenv("AUTH_DISABLED", "false").lower() == "true":
        return await call_next(request)

    # Path publik
    if path in _PUBLIC_PATHS or path.startswith("/auth/"):
        return await call_next(request)

    # OPTIONS (preflight CORS) selalu diizinkan
    if request.method == "OPTIONS":
        return await call_next(request)

    # Verifikasi token
    authorization = request.headers.get("Authorization")
    try:
        user = auth.verify_token(authorization)
    except Exception:
        return JSONResponse(
            status_code=401,
            content={"detail": "Autentikasi diperlukan. Silakan login."},
        )

    # Integrasi #3, A.1: teruskan identitas ke endpoint (scoping per-guru).
    request.state.user = user

    return await call_next(request)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Tambahkan request-ID + log akses terstruktur (integrasi #5, D5).

    Middleware ini didaftarkan terakhir → berjalan paling luar, sehingga request-ID
    mencakup rate-limit & auth dan header respons selalu ter-set.
    """
    import time
    import uuid

    from logging_config import get_logger

    # Integrasi #6 (E.1): sanitasi X-Request-ID klien (potensi injeksi log).
    # Batasi panjang & karakter; bila kosong/tak valid → generate baru.
    raw_rid = request.headers.get("X-Request-ID") or ""
    sanitized = "".join(ch for ch in raw_rid if ch.isalnum() or ch in "-_")[:64]
    rid = sanitized or uuid.uuid4().hex
    request.state.request_id = rid
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)

    response.headers["X-Request-ID"] = rid
    # Log akses (tanpa rahasia). Endpoint publik pun dicatat — berguna saat prod.
    get_logger("access").info(
        "request",
        extra={
            "request_id": rid,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


app.include_router(auth.router)
app.include_router(signup.router)
app.include_router(students.router)
app.include_router(readings.router)
app.include_router(assessments.router)
app.include_router(classes.router)
app.include_router(dashboard.router)
app.include_router(hasbrouck.router)
app.include_router(config.router)


@app.get("/health")
def health():
    """Health check bermakna (integrasi #3, D.3).

    Melaporkan status dependency utama tanpa membocorkan rahasia:
    - versi API & versi kontrak framework (schema_version)
    - jenis repository (in-memory / supabase)
    - apakah model Whisper sudah dimuat
    """
    from repository import InMemoryRepository, get_repository
    from reading_framework.config import SCHEMA_VERSION as framework_schema
    from services import speech

    try:
        is_supabase = not isinstance(get_repository(), InMemoryRepository)
    except Exception:
        is_supabase = None

    whisper_loaded = bool(getattr(speech, "_whisper_model", None))

    from api.env_validation import current_env

    return {
        "status": "ok",
        "version": "2.5",
        "env": current_env(),
        "framework_schema_version": framework_schema,
        "repository": "supabase" if is_supabase else "in-memory",
        "supabase_configured": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")),
        "whisper_loaded": whisper_loaded,
        "auth_disabled": os.getenv("AUTH_DISABLED", "false").lower() == "true",
    }


@app.get("/ready")
def ready():
    """Readiness check (integrasi #5, C.4): siap menerima trafik?

    Berbeda dari `/health` (liveness — proses hidup): `/ready` memeriksa
    **kesiapan** menerima permintaan penilaian:
    - model Whisper sudah termuat (kecuali mode demo/fallback),
    - repository dapat diakses (in-memory selalu; supabase dicek ringan).

    Kembalikan 200 bila siap, 503 bila belum (mis. model belum termuat).
    """
    from repository import InMemoryRepository, get_repository
    from services import speech

    demo = os.getenv("DEMO_FALLBACK", "false").lower() == "true"
    whisper_loaded = bool(getattr(speech, "_whisper_model", None))
    model_ok = demo or whisper_loaded

    repo_ok = True
    try:
        repo = get_repository()
        if not isinstance(repo, InMemoryRepository):
            # Ping ringan ke Supabase (select 1 baris) — best-effort.
            try:
                repo.client.table("users").select("id").limit(1).execute()
            except Exception:
                repo_ok = False
    except Exception:
        repo_ok = False

    ok = model_ok and repo_ok
    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ready" if ok else "not_ready",
            "model_loaded": whisper_loaded,
            "demo_mode": demo,
            "repository_ok": repo_ok,
        },
    )
