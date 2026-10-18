"""Raw transcript writer (.txt) and JSON export helpers.

Tanggung jawab:
- menulis ``transcript_raw.txt`` berisi HANYA teks mentah model;
- memakai encoding UTF-8;
- menghindari overwrite tidak sengaja (mode anti-overwrite default);
- mencatat kegagalan penulisan file secara jelas (raise, bukan silent).

File raw transcript TIDAK boleh memuat skor, metadata, teks target, koreksi,
atau komentar.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class OutputWriteError(IOError):
    """Kegagalan menulis file output (TXT/JSON) yang dilaporkan eksplisit."""


def _prepare_out_path(path: str | os.PathLike[str], overwrite: bool) -> Path:
    out = Path(path)
    if out.exists() and not overwrite:
        raise OutputWriteError(
            f"refusing to overwrite existing file: {out} "
            "(pass overwrite=True to replace)"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def write_raw_transcript_text(raw_text: str, path: str | os.PathLike[str],
                              *, overwrite: bool = False,
                              failed_error: str | None = None) -> Path:
    """Tulis transkrip mentah ke TXT. Isi = teks apa adanya.

    Bila ``failed_error`` diberikan (ASR gagal), file TIDAK berpura-pura sukses:
    tulis satu baris penanda kegagalan saja, tanpa teks transkrip.
    """
    out = _prepare_out_path(path, overwrite)
    try:
        if failed_error:
            body = f"[ASR FAILED] {failed_error}\n"
        else:
            body = (raw_text or "").strip() + "\n"
        out.write_text(body, encoding="utf-8")
    except OSError as exc:
        raise OutputWriteError(f"failed to write raw transcript {out}: {exc}") from exc
    return out


def write_json(payload: dict[str, Any], path: str | os.PathLike[str],
               *, overwrite: bool = False) -> Path:
    """Tulis JSON (UTF-8, indent 2). Raise ``OutputWriteError`` bila gagal."""
    out = _prepare_out_path(path, overwrite)
    try:
        out.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    except OSError as exc:
        raise OutputWriteError(f"failed to write JSON {out}: {exc}") from exc
    return out


def read_json(path: str | os.PathLike[str]) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
