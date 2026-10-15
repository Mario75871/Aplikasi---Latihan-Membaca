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
    dashboard,
    hasbrouck,
    readings,
    students,
)
from services.speech import load_whisper_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load Whisper model saat startup."""
    print("[main] Starting BacaLaras API v2.5")
    load_whisper_model()
    yield
    print("[main] Shutting down")


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


# Middleware auth: endpoint selain /health dan /auth/* butuh token (D7)
_PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


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
        auth.verify_token(authorization)
    except Exception:
        return JSONResponse(
            status_code=401,
            content={"detail": "Autentikasi diperlukan. Silakan login."},
        )

    return await call_next(request)


app.include_router(auth.router)
app.include_router(students.router)
app.include_router(readings.router)
app.include_router(assessments.router)
app.include_router(classes.router)
app.include_router(dashboard.router)
app.include_router(hasbrouck.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.5"}
