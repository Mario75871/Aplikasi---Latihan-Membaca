"""logging_config.py — Logging terstruktur JSON (integrasi #5, D5).

Tujuan: observability produksi. Satu baris JSON per event (mudah di-parse agregator),
level via `LOG_LEVEL`, dan **request-ID** untuk korelasi antar-log.

Prinsip keamanan: JANGAN pernah log rahasia (Authorization/token/key/email penuh).
Gunakan `redact()` bila perlu menyertakan nilai sensitif.
"""
from __future__ import annotations

import json
import logging
import os

#: Atribut yang boleh disertakan dari record (bila ada).
_EXTRA_KEYS = ("request_id", "path", "method", "status", "duration_ms", "teacher_id")


class JsonFormatter(logging.Formatter):
    """Format record sebagai satu baris JSON."""

    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in _EXTRA_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                base[key] = value
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)


def redact(value: str, keep: int = 4) -> str:
    """Sembunyikan sebagian besar nilai sensitif (mis. token). Untuk log aman."""
    if not value:
        return ""
    if len(value) <= keep:
        return "*" * len(value)
    return f"{value[:keep]}…{'*' * 8}"


def setup_logging() -> None:
    """Konfigurasi root logger dengan JSON formatter (idempotent)."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
