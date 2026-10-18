# BacaLaras backend — Dockerfile (integrasi #3, Fase E).
# Multi-stage, non-root, uvicorn. Model Whisper dimuat saat startup (lihat lifespan).
FROM python:3.10-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg: opsional untuk probe_audio/format audio; libgomp1 dibutuhkan ctranslate2.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download model Whisper saat build (integrasi #5, C.3) agar tidak cold-start
# (unduh besar saat start) & tidak bergantung egress runtime. Model size dari
# build-arg WHISPER_MODEL (default base). Cache HF disamakan build↔runtime via HF_HOME
# (faster-whisper memakai cache HuggingFace).
ARG WHISPER_MODEL=base
ENV WHISPER_MODEL=${WHISPER_MODEL} \
    HF_HOME=/app/models
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL}', device='cpu', compute_type='int8')"

COPY . .

# Non-root user.
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck: liveness via /health; readiness via /ready (siap menerima trafik).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/ready').status==200 else 1)"

# --workers 1 (MVP): rate-limit in-memory & model tunggal konsisten (integrasi #5, D6).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
