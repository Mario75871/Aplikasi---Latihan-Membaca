"""Test pendaftaran akun (integrasi #7) — alur manual: email → OTP → password.

Penyimpanan OTP dan pengirim email di-mock: tidak ada jaringan dan tidak ada email
nyata yang terkirim. Yang diuji adalah **logika dan penjagaan** alurnya, termasuk
sifat-sifat keamanan yang menjadi alasan rancangan ini:

- Kode OTP tidak pernah muncul di respons.
- Tiket hasil verifikasi **bukan sesi** — ia tidak membuka endpoint guru mana pun.
- Kode sekali pakai, berbatas waktu, dan berbatas percobaan.
- Email terdaftar ditolak di langkah 1.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import api.auth as auth_mod
import api.signup as signup_api
import services.signup_otp as signup_otp


# ─────────────────────────────────────────────────────────────
# Ganda (fake) untuk penyimpanan & pengiriman
# ─────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class FakeStore:
    """Pengganti tabel `signup_otp` — cukup untuk perilaku yang diuji."""

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.registered: set[str] = set()
        self._seq = 0

    def _by_id(self, cid: str) -> dict:
        for r in self.rows:
            if r["id"] == cid:
                return r
        raise KeyError(cid)

    # -- API yang dipakai api/signup.py --
    def email_registered(self, email: str) -> bool:
        return email in self.registered

    def invalidate_open_challenges(self, email: str) -> None:
        for r in self.rows:
            if r["email"] == email and r["consumed_at"] is None:
                r["consumed_at"] = _now_iso()

    def store_challenge(self, email, code_hash, name, expires_at, request_ip) -> None:
        self._seq += 1
        self.rows.append(
            {
                "id": str(self._seq),
                "email": email,
                "code_hash": code_hash,
                "name": name,
                "attempts": 0,
                "consumed_at": None,
                "expires_at": expires_at,
                "created_at": _now_iso(),
                "request_ip": request_ip,
            }
        )

    def latest_open_challenge(self, email: str):
        # Format ISO dengan offset sama → perbandingan leksikografis = kronologis.
        open_rows = [
            r
            for r in self.rows
            if r["email"] == email
            and r["consumed_at"] is None
            and r["expires_at"] > _now_iso()
        ]
        return open_rows[-1] if open_rows else None

    def bump_attempts(self, cid: str, attempts: int) -> None:
        self._by_id(cid)["attempts"] = attempts

    def consume_challenge(self, cid: str) -> None:
        self._by_id(cid)["consumed_at"] = _now_iso()


class FakeAdminAuth:
    """Pengganti `supabase.create_client(...)` untuk `auth.admin.create_user`."""

    def __init__(self, fail: Exception | None = None) -> None:
        self.fail = fail
        self.created: list[dict] = []
        self.auth = self
        self.admin = self

    def create_user(self, attrs: dict):
        if self.fail is not None:
            raise self.fail
        self.created.append(attrs)
        return SimpleNamespace(
            user=SimpleNamespace(id="11111111-1111-1111-1111-111111111111", email=attrs["email"])
        )


# ─────────────────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def sent(monkeypatch):
    """Tangkap email yang 'terkirim' alih-alih memanggil Resend."""
    outbox: list[dict] = []

    def fake_send(to: str, code: str, ttl_min: int) -> None:
        outbox.append({"to": to, "code": code, "ttl_min": ttl_min})

    monkeypatch.setattr(signup_api, "send_otp_email", fake_send)
    return outbox


@pytest.fixture
def admin_auth(monkeypatch):
    """Ganti klien admin + `_supabase_login` agar tidak menyentuh Supabase.

    `_supabase_login` palsu menerbitkan token demo lokal, sehingga JWT yang
    dikembalikan `/complete` benar-benar bisa dipakai endpoint terlindungi —
    dan bentuk responsnya tetap persis seperti login.
    """
    admin = FakeAdminAuth()
    captured: dict = {}

    def fake_admin_client():
        return admin

    def fake_supabase_login(username: str, password: str, display_name=None):
        captured["password"] = password
        captured["display_name"] = display_name
        issued = auth_mod._issue_demo_token(username)
        return {
            "token": issued["token"],
            "user_id": "11111111-1111-1111-1111-111111111111",
            "email": username,
            "expires_at": issued["expires_at"],
        }

    monkeypatch.setattr(signup_api, "_admin_auth_client", fake_admin_client)
    monkeypatch.setattr(auth_mod, "_supabase_login", fake_supabase_login)
    return SimpleNamespace(client=admin, captured=captured)


@pytest.fixture
def client(monkeypatch, store, sent, admin_auth):
    """TestClient dengan env pendaftaran lengkap dan penyimpanan di-mock."""
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    monkeypatch.setenv("DEMO_FALLBACK", "true")

    # Env yang membuat `signup_configured()` True. SUPABASE_KEY sengaja TIDAK diisi
    # agar repository tetap in-memory (tanpa jaringan).
    monkeypatch.setenv("SUPABASE_URL", "https://contoh.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-palsu")
    monkeypatch.setenv("RESEND_API_KEY", "re_palsu")
    monkeypatch.setenv("MAIL_FROM", "BacaLaras <noreply@bacalaras.my.id>")
    monkeypatch.setenv("SIGNUP_OTP_SECRET", "rahasia-uji-yang-cukup-panjang-32byte")
    monkeypatch.delenv("SIGNUP_OTP_TTL_SEC", raising=False)
    monkeypatch.delenv("SIGNUP_OTP_MAX_ATTEMPTS", raising=False)
    monkeypatch.delenv("SIGNUP_TICKET_TTL_SEC", raising=False)

    for name, fn in (
        ("email_registered", store.email_registered),
        ("invalidate_open_challenges", store.invalidate_open_challenges),
        ("store_challenge", store.store_challenge),
        ("latest_open_challenge", store.latest_open_challenge),
        ("bump_attempts", store.bump_attempts),
        ("consume_challenge", store.consume_challenge),
    ):
        monkeypatch.setattr(signup_otp, name, fn)

    import repository
    repository._repo = None
    auth_mod.reset_sessions()

    # Limiter adalah singleton lintas-test; tanpa reset, batas per-IP menumpuk
    # antar test dan membuat hasilnya bergantung urutan.
    from services.rate_limit import get_limiter
    get_limiter().reset()

    import main
    with TestClient(main.app) as c:
        yield c


EMAIL = "guru.baru@sekolah.id"
NAME = "Bu Rina"


def _start(client, email: str = EMAIL, name: str = NAME):
    return client.post("/auth/signup/start", json={"email": email, "name": name})


def _verify(client, code: str, email: str = EMAIL):
    return client.post("/auth/signup/verify", json={"email": email, "code": code})


def _complete(client, ticket: str, password: str = "rahasia123"):
    return client.post(
        "/auth/signup/complete", json={"ticket": ticket, "password": password}
    )


# ─────────────────────────────────────────────────────────────
# Alur bahagia
# ─────────────────────────────────────────────────────────────

def test_alur_lengkap_sampai_masuk_dashboard(client, sent, admin_auth):
    """email → OTP → tiket → password → token yang benar-benar bisa dipakai."""
    r1 = _start(client)
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "sent"
    assert len(sent) == 1
    assert sent[0]["to"] == EMAIL

    r2 = _verify(client, sent[0]["code"])
    assert r2.status_code == 200, r2.text
    ticket = r2.json()["ticket"]
    assert r2.json()["name"] == NAME

    r3 = _complete(client, ticket)
    assert r3.status_code == 200, r3.text
    body = r3.json()

    # Bentuk respons identik dengan LoginResponse.
    assert set(body.keys()) == {"token", "username", "expires_at"}
    assert body["username"] == EMAIL

    # Nama dari langkah 1 diteruskan, bukan ditimpa email.
    assert admin_auth.captured["display_name"] == NAME
    assert admin_auth.client.created[0]["email"] == EMAIL
    assert admin_auth.client.created[0]["email_confirm"] is True

    # Token benar-benar berfungsi di endpoint terlindungi.
    r4 = client.get("/students", headers={"Authorization": f"Bearer {body['token']}"})
    assert r4.status_code == 200


def test_email_dinormalkan_jadi_huruf_kecil(client, sent):
    r1 = _start(client, email="  Guru.Baru@Sekolah.ID  ")
    assert r1.status_code == 200
    assert r1.json()["email"] == "guru.baru@sekolah.id"
    assert sent[0]["to"] == "guru.baru@sekolah.id"


# ─────────────────────────────────────────────────────────────
# Langkah 1 — /start
# ─────────────────────────────────────────────────────────────

def test_kode_otp_tidak_pernah_muncul_di_respons(client, sent):
    """Kebocoran kode di body akan membuat verifikasi jadi formalitas."""
    r = _start(client)
    assert sent[0]["code"] not in r.text
    assert sent[0]["code"] not in r.json()["email"]


def test_start_menolak_email_yang_sudah_terdaftar(client, store, sent):
    """Menutup jalur 'OTP → password' sebagai cara mengambil alih akun."""
    store.registered.add(EMAIL)
    r = _start(client)
    assert r.status_code == 409
    assert len(sent) == 0


def test_start_menolak_email_tidak_valid(client, sent):
    for buruk in ("bukan-email", "a@b", "@sekolah.id", "guru@.id", ""):
        r = _start(client, email=buruk)
        assert r.status_code == 422, buruk
    assert len(sent) == 0


def test_start_menolak_nama_kosong(client, sent):
    r = _start(client, name="   ")
    assert r.status_code == 422
    assert len(sent) == 0


def test_start_503_bila_belum_dikonfigurasi(client, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    r = _start(client)
    assert r.status_code == 503


def test_start_ulang_menggantikan_kode_lama(client, sent, store):
    """Kirim ulang: hanya kode terbaru yang berlaku."""
    _start(client)
    kode_lama = sent[0]["code"]
    _start(client)
    kode_baru = sent[1]["code"]

    assert _verify(client, kode_lama).status_code == 400
    assert _verify(client, kode_baru).status_code == 200


def test_start_dibatasi_per_email(client, sent):
    """Tiap /start mengirim email nyata — harus ada batasnya."""
    for i in range(3):
        assert _start(client).status_code == 200, f"panggilan ke-{i + 1}"
    assert _start(client).status_code == 429


def test_start_membatalkan_kode_bila_pengiriman_gagal(client, monkeypatch, store):
    from services.email import EmailDeliveryError

    def gagal(to, code, ttl_min):
        raise EmailDeliveryError("Resend menolak (HTTP 422).")

    monkeypatch.setattr(signup_api, "send_otp_email", gagal)
    r = _start(client)
    assert r.status_code == 502
    # Tidak boleh ada tantangan yang menggantung seolah masih bisa diverifikasi.
    assert store.latest_open_challenge(EMAIL) is None


# ─────────────────────────────────────────────────────────────
# Langkah 2 — /verify
# ─────────────────────────────────────────────────────────────

def test_verify_kode_salah_menyisakan_percobaan(client, sent):
    _start(client)
    benar = sent[0]["code"]
    salah = "000000" if benar != "000000" else "111111"

    r = _verify(client, salah)
    assert r.status_code == 400
    assert "4" in r.json()["detail"]  # 5 - 1

    # Kode benar masih berlaku selama percobaan belum habis.
    assert _verify(client, benar).status_code == 200


def test_verify_habis_percobaan_mengunci_kode(client, sent):
    _start(client)
    benar = sent[0]["code"]
    salah = "000000" if benar != "000000" else "111111"

    for _ in range(4):
        assert _verify(client, salah).status_code == 400

    # Percobaan ke-5 menghabiskan kuota → kode dimatikan.
    assert _verify(client, salah).status_code == 429
    # Kode yang benar pun tidak lagi berlaku.
    assert _verify(client, benar).status_code == 400


def test_verify_kode_kedaluwarsa(client, sent, store):
    _start(client)
    # Kedaluwarsakan paksa tanpa menunggu.
    store.rows[0]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    assert _verify(client, sent[0]["code"]).status_code == 400


def test_verify_tanpa_tantangan(client, store):
    r = _verify(client, "123456")
    assert r.status_code == 400
    assert "kedaluwarsa" in r.json()["detail"].lower()


def test_verify_kode_bukan_angka(client, sent):
    _start(client)
    r = _verify(client, "abcdef")
    assert r.status_code == 400


def test_kode_sekali_pakai(client, sent):
    _start(client)
    kode = sent[0]["code"]
    assert _verify(client, kode).status_code == 200
    assert _verify(client, kode).status_code == 400


def test_kode_terikat_ke_emailnya(client, sent, store):
    """Kode yang diterbitkan untuk satu alamat tidak berlaku untuk alamat lain."""
    _start(client)
    kode = sent[0]["code"]

    lain = "orang.lain@sekolah.id"
    store.store_challenge(  # type: ignore[attr-defined]
        email=lain,
        code_hash=signup_otp.hash_code(EMAIL, kode),
        name="Orang Lain",
        expires_at=signup_otp.expires_at_iso(600),
        request_ip="127.0.0.1",
    )
    assert _verify(client, kode, email=lain).status_code == 400


# ─────────────────────────────────────────────────────────────
# Langkah 3 — /complete
# ─────────────────────────────────────────────────────────────

def test_tiket_bukan_sesi(client, sent):
    """Sifat keamanan inti: tiket tidak membuka satu pun endpoint guru."""
    _start(client)
    ticket = _verify(client, sent[0]["code"]).json()["ticket"]

    for path in ("/students", "/classes", "/dashboard/summary"):
        r = client.get(path, headers={"Authorization": f"Bearer {ticket}"})
        assert r.status_code == 401, path


def test_complete_menolak_tiket_palsu(client):
    for palsu in ("", "abc", "abc.def", "a.b.c", "x" * 40):
        assert _complete(client, palsu).status_code == 401


def test_complete_menolak_tiket_yang_diubah(client, sent):
    """Mengubah isi payload harus merusak tanda tangan."""
    _start(client)
    ticket = _verify(client, sent[0]["code"]).json()["ticket"]
    b64, sig = ticket.split(".")

    # Ganti satu karakter payload (tetap base64 valid).
    swapped = ("B" if b64[0] != "B" else "C") + b64[1:]
    assert _complete(client, f"{swapped}.{sig}").status_code == 401

    # Tanda tangan palsu.
    assert _complete(client, f"{b64}.{'0' * len(sig)}").status_code == 401


def test_complete_menolak_tiket_kedaluwarsa(client, sent, monkeypatch):
    _start(client)
    ticket = _verify(client, sent[0]["code"]).json()["ticket"]

    class _WaktuMasaDepan:
        @staticmethod
        def time():
            return time.time() + 100_000

    monkeypatch.setattr(signup_otp, "time", _WaktuMasaDepan)
    r = _complete(client, ticket)
    assert r.status_code == 401
    assert "kedaluwarsa" in r.json()["detail"].lower()


def test_complete_menolak_password_pendek(client, sent):
    _start(client)
    ticket = _verify(client, sent[0]["code"]).json()["ticket"]
    r = _complete(client, ticket, password="pendek")
    assert r.status_code == 422


def test_complete_409_bila_email_sudah_ada_di_supabase(client, sent, monkeypatch):
    """Perlombaan antara /start dan /complete: Supabase tetap otoritatif."""
    _start(client)
    ticket = _verify(client, sent[0]["code"]).json()["ticket"]

    err = Exception("User already registered")
    err.code = "email_exists"  # type: ignore[attr-defined]
    monkeypatch.setattr(signup_api, "_admin_auth_client", lambda: FakeAdminAuth(fail=err))

    r = _complete(client, ticket)
    assert r.status_code == 409


def test_complete_503_bila_supabase_menolak_sebab_lain(client, sent, monkeypatch):
    _start(client)
    ticket = _verify(client, sent[0]["code"]).json()["ticket"]
    err = Exception("koneksi terputus")
    monkeypatch.setattr(signup_api, "_admin_auth_client", lambda: FakeAdminAuth(fail=err))
    assert _complete(client, ticket).status_code == 503


# ─────────────────────────────────────────────────────────────
# Unit — primitif di services/signup_otp.py
# ─────────────────────────────────────────────────────────────

def test_hash_kode_tidak_mengembalikan_kode_mentah(monkeypatch):
    monkeypatch.setenv("SIGNUP_OTP_SECRET", "rahasia-uji")
    h = signup_otp.hash_code(EMAIL, "123456")
    assert "123456" not in h and len(h) == 64


def test_hash_kode_berbeda_antar_email(monkeypatch):
    monkeypatch.setenv("SIGNUP_OTP_SECRET", "rahasia-uji")
    assert signup_otp.hash_code(EMAIL, "123456") != signup_otp.hash_code("lain@x.id", "123456")


def test_hash_kode_berbeda_antar_secret(monkeypatch):
    monkeypatch.setenv("SIGNUP_OTP_SECRET", "rahasia-satu")
    a = signup_otp.hash_code(EMAIL, "123456")
    monkeypatch.setenv("SIGNUP_OTP_SECRET", "rahasia-dua")
    assert signup_otp.hash_code(EMAIL, "123456") != a


def test_secret_kosong_menolak_bekerja(monkeypatch):
    """Tanpa SIGNUP_OTP_SECRET fitur harus mati, bukan memakai kunci yang bisa ditebak."""
    monkeypatch.delenv("SIGNUP_OTP_SECRET", raising=False)
    with pytest.raises(signup_otp.SignupNotConfigured):
        signup_otp.hash_code(EMAIL, "123456")
    with pytest.raises(signup_otp.SignupNotConfigured):
        signup_otp.issue_ticket(EMAIL, NAME)


def test_generate_code_selalu_enam_digit():
    for _ in range(200):
        kode = signup_otp.generate_code()
        assert len(kode) == 6 and kode.isdigit()


def test_tiket_bolak_balik(monkeypatch):
    monkeypatch.setenv("SIGNUP_OTP_SECRET", "rahasia-uji")
    ticket, expires = signup_otp.issue_ticket(EMAIL, NAME)
    claims = signup_otp.verify_ticket(ticket)
    assert claims == {"email": EMAIL, "name": NAME}
    assert expires > _now_iso()


def test_tiket_menolak_bentuk_yang_tidak_diharapkan(monkeypatch):
    monkeypatch.setenv("SIGNUP_OTP_SECRET", "rahasia-uji")
    for buruk in ("", "abc", "a.b.c", "..", "x.y"):
        with pytest.raises(ValueError):
            signup_otp.verify_ticket(buruk)


def test_nilai_default_env(monkeypatch):
    for name in ("SIGNUP_OTP_TTL_SEC", "SIGNUP_OTP_MAX_ATTEMPTS", "SIGNUP_TICKET_TTL_SEC"):
        monkeypatch.delenv(name, raising=False)
    assert signup_otp.otp_ttl_sec() == 600
    assert signup_otp.max_attempts() == 5
    assert signup_otp.ticket_ttl_sec() == 900

    # Nilai tidak masuk akal jatuh ke default, bukan mematikan fitur.
    monkeypatch.setenv("SIGNUP_OTP_MAX_ATTEMPTS", "0")
    assert signup_otp.max_attempts() == 5
    monkeypatch.setenv("SIGNUP_OTP_MAX_ATTEMPTS", "abc")
    assert signup_otp.max_attempts() == 5
