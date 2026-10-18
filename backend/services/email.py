"""Pengiriman email transaksional lewat Resend (fitur daftar akun).

Kenapa Resend: gratis 3.000 email/bulan tanpa kartu kredit, dan pengirim memakai
domain sendiri (mis. `noreply@bacalaras.my.id`) sehingga tidak mudah jatuh ke spam.

Fungsi di sini **sinkron** (`httpx.post`) supaya seragam dengan endpoint lain di
`api/` yang juga `def` biasa, bukan `async def`.

KEAMANAN: jangan pernah mencatat kode OTP, alamat penerima, atau isi email ke log.
Pesan galat di sini sengaja hanya memuat jenis/status kesalahan.
"""
from __future__ import annotations

import os

import httpx

#: Endpoint Resend untuk kirim satu email.
RESEND_ENDPOINT = "https://api.resend.com/emails"

#: Batas waktu permintaan ke Resend. Pendek — endpoint signup dipanggil pengguna
#: secara interaktif, jadi lebih baik gagal cepat daripada menggantung lama.
_TIMEOUT_SEC = 15.0


class EmailNotConfigured(RuntimeError):
    """Env pengiriman email belum diisi — fitur daftar akun nonaktif."""


class EmailDeliveryError(RuntimeError):
    """Pengiriman gagal (jaringan bermasalah atau Resend menolak)."""


def email_configured() -> bool:
    """True bila env pengiriman email lengkap (tanpa menyentuh jaringan)."""
    return bool(os.getenv("RESEND_API_KEY")) and bool(os.getenv("MAIL_FROM"))


def _require_config() -> tuple[str, str]:
    """Kembalikan (api_key, pengirim). Raise bila belum dikonfigurasi.

    Sengaja TIDAK memakai nilai default apa pun: alamat pengirim karangan akan
    ditolak Resend, dan lebih baik gagal dengan pesan jelas sejak awal.
    """
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("MAIL_FROM")
    if not api_key or not sender:
        raise EmailNotConfigured(
            "RESEND_API_KEY dan MAIL_FROM wajib diisi untuk mengirim email."
        )
    return api_key, sender


def _otp_body(code: str, ttl_min: int) -> tuple[str, str]:
    """Bangun (teks biasa, html) untuk email kode verifikasi.

    Versi teks biasa ikut dikirim karena sebagian klien email memblokir HTML;
    Resend mengirim keduanya dan klien yang memilih.
    """
    text = (
        "BacaLaras — Verifikasi Email\n"
        "\n"
        f"Kode verifikasi Anda: {code}\n"
        "\n"
        f"Kode ini berlaku {ttl_min} menit. Jangan bagikan kode ini kepada siapa pun, "
        "termasuk pihak yang mengaku dari BacaLaras.\n"
        "\n"
        "Bila Anda tidak merasa mendaftar di BacaLaras, abaikan saja email ini.\n"
    )

    # HTML sengaja sederhana & bergaya inline: banyak klien email membuang <style>.
    html_body = f"""\
<!doctype html>
<html lang="id">
  <body style="margin:0;padding:24px;background:#f8fafc;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;color:#1e293b;">
    <div style="max-width:480px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:32px;">
      <h1 style="margin:0 0 4px;font-size:20px;font-weight:800;">BacaLaras</h1>
      <p style="margin:0 0 24px;font-size:13px;color:#64748b;">Baca. Didengar. Dipahami.</p>

      <p style="margin:0 0 12px;font-size:15px;">Masukkan kode berikut untuk memverifikasi email Anda:</p>

      <p style="margin:0 0 20px;padding:16px;background:#f1f5f9;border-radius:8px;text-align:center;font-size:32px;font-weight:700;letter-spacing:8px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;">{code}</p>

      <p style="margin:0 0 20px;font-size:14px;color:#475569;">Kode ini berlaku <strong>{ttl_min} menit</strong>. Jangan bagikan kode ini kepada siapa pun, termasuk pihak yang mengaku dari BacaLaras.</p>

      <p style="margin:0;padding-top:20px;border-top:1px solid #e2e8f0;font-size:12px;color:#94a3b8;">Bila Anda tidak merasa mendaftar di BacaLaras, abaikan saja email ini.</p>
    </div>
  </body>
</html>"""
    return text, html_body


def send_otp_email(to: str, code: str, ttl_min: int) -> None:
    """Kirim kode verifikasi ke `to`.

    Raises:
        EmailNotConfigured: env belum diisi.
        EmailDeliveryError: jaringan gagal atau Resend menolak.
    """
    api_key, sender = _require_config()
    text, html_body = _otp_body(code, ttl_min)

    payload = {
        "from": sender,
        "to": [to],
        "subject": "Kode verifikasi BacaLaras",
        "text": text,
        "html": html_body,
    }

    try:
        resp = httpx.post(
            RESEND_ENDPOINT,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_TIMEOUT_SEC,
        )
    except httpx.HTTPError as e:
        # Hanya jenis galatnya yang dicatat — bukan isi permintaan (memuat kode).
        raise EmailDeliveryError(f"Gagal menghubungi Resend: {type(e).__name__}") from e

    if resp.status_code >= 400:
        raise EmailDeliveryError(f"Resend menolak pengiriman (HTTP {resp.status_code}).")
