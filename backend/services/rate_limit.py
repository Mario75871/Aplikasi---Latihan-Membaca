"""Rate limiting in-memory (integrasi #4, D4 / P1).

Batas awal (dapat dikonfigurasi via env):
- Upload/transkripsi: 10 permintaan / guru / 10 menit.
- Upload/transkripsi: 30 permintaan / IP / 10 menit.
- Login:             20 percobaan / IP / 10 menit.
- Polling status:    120 permintaan / guru / menit.

Kunci = IP (``request.client.host``, hormati ``X-Forwarded-For`` bila di belakang
proxy) dan/atau guru (dari JWT ``user_id``). Mengembalikan 429 + ``Retry-After``.

BATAS MVP: store in-memory hanya berlaku untuk **1 proses**. Untuk multi-instance,
gunakan store bersama (Redis). Tidak dipakai untuk melindungi lebih dari 1 worker.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field


@dataclass
class Limit:
    """Batas: `max_requests` per `window_sec`."""
    max_requests: int
    window_sec: int


@dataclass
class _Bucket:
    hits: list[float] = field(default_factory=list)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        val = int(raw)
        return val if val > 0 else default
    except ValueError:
        return default


def limits_from_env() -> dict[str, Limit]:
    """Batas dari env (fallback nilai awal D4)."""
    return {
        # Upload/transkripsi
        "audio_teacher": Limit(_int_env("RATE_LIMIT_AUDIO_TEACHER", 10), _int_env("RATE_LIMIT_AUDIO_WINDOW_SEC", 600)),
        "audio_ip": Limit(_int_env("RATE_LIMIT_AUDIO_IP", 30), _int_env("RATE_LIMIT_AUDIO_WINDOW_SEC", 600)),
        # Login
        "login_ip": Limit(_int_env("RATE_LIMIT_LOGIN_IP", 20), _int_env("RATE_LIMIT_LOGIN_WINDOW_SEC", 600)),
        # Polling status job
        "poll_teacher": Limit(_int_env("RATE_LIMIT_POLL_TEACHER", 120), _int_env("RATE_LIMIT_POLL_WINDOW_SEC", 60)),
        # Pendaftaran akun (integrasi #7). Sengaja ketat: tiap permintaan /start
        # mengirim satu email nyata, jadi tanpa batas ini satu alamat bisa dipakai
        # membanjiri kotak masuk orang lain.
        #   *_ip     → ditegakkan middleware di main._rate_limit_target
        #   *_email  → ditegakkan di dalam endpoint (butuh isi body)
        "signup_ip": Limit(_int_env("RATE_LIMIT_SIGNUP_IP", 5), _int_env("RATE_LIMIT_SIGNUP_WINDOW_SEC", 600)),
        "signup_email": Limit(_int_env("RATE_LIMIT_SIGNUP_EMAIL", 3), _int_env("RATE_LIMIT_SIGNUP_WINDOW_SEC", 600)),
        "signup_verify_ip": Limit(_int_env("RATE_LIMIT_SIGNUP_VERIFY_IP", 20), _int_env("RATE_LIMIT_SIGNUP_WINDOW_SEC", 600)),
        "signup_verify_email": Limit(_int_env("RATE_LIMIT_SIGNUP_VERIFY_EMAIL", 10), _int_env("RATE_LIMIT_SIGNUP_WINDOW_SEC", 600)),
    }


class RateLimiter:
    """Fixed-window in-memory limiter (kunci → daftar timestamp)."""

    def __init__(self, limits: dict[str, Limit] | None = None):
        self.limits = limits or limits_from_env()
        self._buckets: dict[str, _Bucket] = {}

    def check(self, key: str, limit_name: str, now: float | None = None) -> tuple[bool, int]:
        """Periksa & catat satu permintaan.

        Returns:
            (allowed, retry_after_sec). ``allowed=False`` → tolak (429) dengan
            ``retry_after_sec`` detik sampai slot berikutnya bebas.
        """
        limit = self.limits.get(limit_name)
        if limit is None:
            return True, 0
        now = time.time() if now is None else now
        bucket = self._buckets.setdefault(f"{limit_name}:{key}", _Bucket())
        cutoff = now - limit.window_sec
        bucket.hits = [t for t in bucket.hits if t > cutoff]
        if len(bucket.hits) >= limit.max_requests:
            retry_after = int(bucket.hits[0] + limit.window_sec - now) + 1
            return False, max(1, retry_after)
        bucket.hits.append(now)
        return True, 0

    def reset(self) -> None:
        """Kosongkan bucket & muat ulang batas dari env (untuk test/ubah runtime)."""
        self._buckets.clear()
        self.limits = limits_from_env()


def client_ip(request) -> str:
    """Ambil IP klien. Hormati X-Forwarded-For (proxy tepercaya) — ambil hop pertama."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


#: Singleton default (dipakai middleware).
_limiter = RateLimiter()


def get_limiter() -> RateLimiter:
    return _limiter
