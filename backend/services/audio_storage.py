"""Penyimpanan audio siswa di Supabase Storage (integrasi #4, D2 / B.4).

KEPUTUSAN (dikunci): audio disimpan di **Supabase Storage** (bukan disk server),
bucket **private** `reading-audio`. Struktur objek:

    {teacher_id}/{assessment_id}/normalized.<ext>   ← audio yang benar-benar diproses ASR
    {teacher_id}/{assessment_id}/original.<ext>     ← opsional salinan asli (audit)

Prinsip:
- **Gagal unggah tidak menggagalkan penilaian** (media penting, bukan alasan menolak).
  Bila Storage bermasalah, fungsi mengembalikan ``None`` + log peringatan; ``audio_url``
  dibiarkan ``null`` (bukan ``""`` — ``null`` ≠ nilai palsu).
- Akses memakai klien **guru (anon + RLS)**: policy Storage men-scope prefix folder =
  ``auth.uid()``. Jalur admin/seed memakai service-role.
- Nilai yang disimpan di ``assessments.audio_url`` adalah **path objek** (bukan URL
  publik permanen). URL akses dibuat **signed URL** berumur pendek saat dibutuhkan.
"""
from __future__ import annotations

import os
from typing import Optional

#: Nama bucket (harus cocok dengan `supabase_schema.sql`).
BUCKET = os.getenv("AUDIO_STORAGE_BUCKET", "reading-audio")

#: Umur signed URL (detik). Berumur pendek — bukan URL publik permanen.
SIGNED_URL_TTL_SEC = int(os.getenv("AUDIO_SIGNED_URL_TTL_SEC", "600"))


def _ext_for(fmt: str) -> str:
    return "wav" if fmt == "wav" else "mp3"


def store_audio(
    client,
    teacher_id: str,
    assessment_id: str,
    data: bytes,
    fmt: str,
    *,
    kind: str = "normalized",
) -> Optional[str]:
    """Unggah audio ke bucket private. Kembalikan **path objek** atau ``None``.

    Args:
        client: klien Supabase dengan sesi guru (agar RLS Storage berlaku).
        teacher_id: pemilik (prefix folder pertama).
        assessment_id: id asesmen (folder kedua).
        data: byte audio.
        fmt: 'wav' atau 'mp3'.
        kind: 'normalized' (diproses) atau 'original' (audit).

    Returns:
        path objek (mis. ``{teacher_id}/{assessment_id}/normalized.wav``) bila sukses;
        ``None`` bila gagal (dipanggil tidak menggagalkan penilaian).
    """
    path = f"{teacher_id}/{assessment_id}/{kind}.{_ext_for(fmt)}"
    content_type = "audio/wav" if fmt == "wav" else "audio/mpeg"
    try:
        client.storage.from_(BUCKET).upload(
            path,
            data,
            {"content-type": content_type, "upsert": "true"},
        )
        return path
    except Exception as e:  # pragma: no cover - bergantung jaringan/Supabase
        print(f"[storage] peringatan: gagal unggah audio {path}: {e}")
        return None


def signed_url(client, path: str, ttl: int = SIGNED_URL_TTL_SEC) -> Optional[str]:
    """Buat signed URL berumur pendek untuk path objek (akses terkontrol).

    Hanya dibuat backend setelah verifikasi kepemilikan (``teacher_id``). Kembalikan
    ``None`` bila gagal (mis. Storage tidak dikonfigurasi).
    """
    if not path:
        return None
    try:
        resp = client.storage.from_(BUCKET).create_signed_url(path, ttl)
        # supabase-py mengembalikan dict {"signedURL": ...} (varian versi berbeda).
        if isinstance(resp, dict):
            return resp.get("signedURL") or resp.get("signed_url")
        return getattr(resp, "signed_url", None)
    except Exception as e:  # pragma: no cover
        print(f"[storage] peringatan: gagal membuat signed URL untuk {path}: {e}")
        return None


def remove(client, path: str) -> bool:
    """Hapus objek dari Storage (untuk retensi/prune). Kembalikan True bila sukses.

    Integrasi #5 (D2): dipakai `scripts/prune_audio.py`. **Tidak** menelan daftar
    error — pemanggil menangani retry & pencatatan status. Bila ``path`` kosong →
    dianggap sukses (tak ada yang perlu dihapus).
    """
    if not path:
        return True
    client.storage.from_(BUCKET).remove([path])
    return True


def _extract_signed_upload(resp) -> tuple[Optional[str], Optional[str]]:
    """Ambil (url, token) dari respons `create_signed_upload_url` lintas-bentuk."""
    if isinstance(resp, dict):
        url = resp.get("signed_url") or resp.get("signedUrl")
        token = resp.get("token")
    else:
        url = getattr(resp, "signed_url", None) or getattr(resp, "signedUrl", None)
        token = getattr(resp, "token", None)
    return url, token


def create_signed_upload_url(
    client, path: str, *, upsert: bool = True
) -> Optional[dict]:
    """Terbitkan **signed upload URL** agar klien mengunggah langsung ke Storage.

    Integrasi #6 (Fase D, Opsi A): menutup blocker batas body Vercel 4.5 MB — browser
    meng-upload audio (≤10 MB) **langsung ke Supabase**, bukan lewat fungsi Vercel.
    Backend hanya menerbitkan URL berumur pendek (setelah verifikasi kepemilikan).

    Args:
        client: klien Supabase dengan sesi guru (RLS Storage berlaku saat unggah).
        path: path objek tujuan (mis. ``{teacher}/{assessment}/normalized.wav``).
        upsert: izinkan menimpa objek yang sudah ada (untuk retry/rekam ulang).

    Returns:
        dict ``{"path", "signed_url", "token"}`` bila sukses; ``None`` bila gagal.

    Catatan: bentuk ``options`` berbeda antar-versi `storage3` — sebagian mengakses
    ``options.upsert`` sebagai **atribut** (pydantic BaseModel), sebagian lagi sebagai
    **dict** (TypedDict). Kita coba beberapa bentuk berurutan agar tahan-versi.
    """
    if not path:
        return None

    value = "true" if upsert else "false"
    candidates: list = []
    # 1) Tipe resmi (pydantic BaseModel) — versi yang membaca atribut `.upsert`.
    try:
        from storage3.types import CreateSignedUploadUrlOptions

        candidates.append(CreateSignedUploadUrlOptions(upsert=value))
    except Exception:  # pragma: no cover - versi lama tak punya tipe ini
        pass

    # 2) Shim objek ber-atribut `.upsert`.
    class _Opts:  # noqa: D401 - shim sederhana
        def __init__(self, v: str) -> None:
            self.upsert = v

    candidates.append(_Opts(value))
    # 3) Dict (varian TypedDict).
    candidates.append({"upsert": value})
    # 4) Tanpa opsi (fallback terakhir; upsert default false).
    candidates.append(None)

    bucket = client.storage.from_(BUCKET)
    last_err: Exception | None = None
    for opts in candidates:
        try:
            resp = (
                bucket.create_signed_upload_url(path)
                if opts is None
                else bucket.create_signed_upload_url(path, opts)
            )
        except Exception as e:  # noqa: BLE001 - coba bentuk berikutnya
            last_err = e
            continue
        url, token = _extract_signed_upload(resp)
        if url and token:
            return {"path": path, "signed_url": url, "token": token}

    print(f"[storage] peringatan: gagal membuat signed upload URL {path}: {last_err}")
    return None


def download(client, path: str) -> Optional[bytes]:
    """Unduh byte objek dari Storage (integrasi #6, Opsi A).

    Dipakai backend untuk mengambil audio yang diunggah klien langsung ke Storage
    (jalur ``POST /audio {audio_path}``). Kembalikan ``None`` bila gagal.
    """
    if not path:
        return None
    try:
        data = client.storage.from_(BUCKET).download(path)
        if isinstance(data, bytes):
            return data
        if isinstance(data, bytearray):
            return bytes(data)
        # Varian versi: objek respons dengan .content
        content = getattr(data, "content", None)
        return content if isinstance(content, (bytes, bytearray)) else None
    except Exception as e:  # pragma: no cover - bergantung jaringan/Supabase
        print(f"[storage] peringatan: gagal mengunduh audio {path}: {e}")
        return None
