"""prune_audio.py — Retensi audio: hapus objek Storage & kosongkan referensi (integrasi #5, D2).

Kebijakan (D2): audio siswa disimpan **12 bulan** (`AUDIO_RETENTION_MONTHS`). Setelah itu:
1. Hapus objek dari Supabase Storage.
2. Bila terkonfirmasi terhapus → kosongkan `assessments.audio_url` (= null).
3. Catat status di `audio_purge_log` (TANPA URL/path/data sensitif).
4. Bila gagal hapus → **retry** (backoff) & **JANGAN** null-kan referensi (hindari objek yatim).

Urutan selalu: *hapus objek dulu, baru null-kan referensi*.

Pemakaian:
    python -m scripts.prune_audio            # DRY-RUN (default; tak mengubah apa pun)
    python -m scripts.prune_audio --apply    # eksekusi (butuh konfirmasi env)

Butuh env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (service-role; bypass RLS).
Jadwalkan via cron eksternal / Supabase scheduled function (lihat README).
"""
from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from services import audio_storage

#: Retry untuk penghapusan objek Storage (backoff detik).
RETRY_BACKOFF_SEC = (1, 4, 9)


def _retention_months() -> int:
    raw = os.getenv("AUDIO_RETENTION_MONTHS", "12")
    try:
        val = int(raw)
        return val if val > 0 else 12
    except ValueError:
        return 12


def _now() -> datetime:
    """Waktu sekarang (UTC). Dipisah agar mudah di-monkeypatch di test."""
    return datetime.now(timezone.utc)


@dataclass
class PruneCounts:
    purged: int = 0
    failed: int = 0
    skipped: int = 0


def _parse_ts(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _log(admin, assessment_id: str, status: str, attempts: int, note: str) -> None:
    admin.table("audio_purge_log").insert({
        "assessment_id": assessment_id,
        "status": status,
        "attempts": attempts,
        "note": note,
    }).execute()


def _remove_with_retry(admin, path: str) -> tuple[bool, int]:
    """Hapus objek Storage dengan retry+backoff. Kembalikan (sukses, attempts)."""
    attempts = 0
    for i, delay in enumerate(RETRY_BACKOFF_SEC):
        attempts = i + 1
        try:
            audio_storage.remove(admin, path)
            return True, attempts
        except Exception:  # noqa: BLE001 — jaringan/Storage bisa gagal
            if i < len(RETRY_BACKOFF_SEC) - 1:
                time.sleep(delay)
    return False, attempts


def run(admin=None, *, apply: bool = False, now: Optional[datetime] = None) -> dict:
    """Jalankan prune. `admin` = klien service-role (di- inject agar mudah di-test).

    Args:
        admin: klien Supabase service-role. Bila None → dibangun dari env.
        apply: False = dry-run (tak mengubah apa pun).
        now: waktu acuan (default: sekarang UTC).

    Returns:
        dict ringkasan {purged, failed, skipped, examined}.
    """
    if admin is None:
        admin = _build_admin_client()

    clock = now or _now()
    cutoff = clock - timedelta(days=30 * _retention_months())

    rows = (
        admin.table("assessments")
        .select("id, audio_url, completed_at, created_at")
        .not_.is_("audio_url", "null")
        .execute()
        .data
    )

    counts = PruneCounts()
    for row in rows:
        ref = row.get("completed_at") or row.get("created_at")
        ts = _parse_ts(ref)
        if ts is None or ts >= cutoff:
            continue  # belum melewati retensi

        path = row.get("audio_url")
        if not path:
            counts.skipped += 1
            continue

        if not apply:
            # Dry-run: hitung rencana, tanpa perubahan/penulisan log.
            counts.purged += 1
            continue

        ok, attempts = _remove_with_retry(admin, path)
        if ok:
            admin.table("assessments").update({"audio_url": None}).eq("id", row["id"]).execute()
            _log(admin, row["id"], "PURGED", attempts, "objek dihapus; referensi dikosongkan")
            counts.purged += 1
        else:
            # JANGAN null-kan referensi (hindari objek yatim).
            _log(admin, row["id"], "FAILED", attempts, "gagal hapus objek; referensi dipertahankan")
            counts.failed += 1

    return {
        "purged": counts.purged,
        "failed": counts.failed,
        "skipped": counts.skipped,
        "examined": len(rows),
    }


def _build_admin_client():
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and key):
        raise RuntimeError(
            "SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY wajib untuk prune_audio."
        )
    return create_client(url, key)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Prune audio lama (retensi).")
    parser.add_argument(
        "--apply", action="store_true",
        help="Eksekusi penghapusan (default: dry-run, tak mengubah apa pun).",
    )
    args = parser.parse_args(argv)

    if args.apply and not os.getenv("AUDIO_RETENTION_MONTHS"):
        # Konfirmasi eksplisit: kebijakan retensi harus di-set untuk --apply.
        print(
            "[prune] AUDIO_RETENTION_MONTHS belum di-set. Set dulu (mis. 12) untuk --apply."
        )
        return 2

    result = run(apply=args.apply)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(
        f"[prune] {mode}: diperiksa={result['examined']} "
        f"purged={result['purged']} failed={result['failed']} skipped={result['skipped']}"
    )
    if not args.apply:
        print("[prune] dry-run — jalankan dengan --apply untuk mengeksekusi.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
