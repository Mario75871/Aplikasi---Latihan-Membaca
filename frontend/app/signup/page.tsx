"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { Stepper, type Step } from "@/components/ui/Stepper";
import { cn } from "@/lib/utils";
import {
  ApiError,
  setSessionToken,
  signupComplete,
  signupStart,
  signupVerify,
} from "@/lib/api";

/**
 * Pendaftaran guru (FR-01 lanjutan) — tiga langkah berurutan:
 *   1. Email + nama  → kode verifikasi dikirim ke email itu
 *   2. Kode          → diverifikasi
 *   3. Password      → akun dibuat, langsung masuk
 *
 * Urutan ini mengikat: password **tidak bisa** dibuat sebelum email terbukti
 * benar-benar bisa dibuka pemiliknya. Antara langkah 2 dan 3 pengguna belum login —
 * yang dipegang adalah tiket sementara dari backend, bukan sesi.
 */

const STEPS: Step[] = [
  { id: "email", label: "Email" },
  { id: "verifikasi", label: "Verifikasi" },
  { id: "password", label: "Password" },
];

const MIN_PASSWORD = 8;
/** Detik sebelum tombol "Kirim ulang kode" aktif (mengikuti batas backend). */
const RESEND_COOLDOWN = 60;

const INPUT_CLASS = cn(
  "h-11 w-full rounded-md border border-slate-200 px-3 text-sm text-slate-800",
  "placeholder:text-slate-400 hover:border-brand-300 focus-visible:outline-none"
);

const LABEL_CLASS = "mb-1 block text-sm font-medium text-slate-700";

function SignupForm() {
  const router = useRouter();
  const [step, setStep] = useState(0);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [ticket, setTicket] = useState("");
  const [cooldown, setCooldown] = useState(0);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  const codeRef = useRef<HTMLInputElement>(null);

  // Hitung mundur tombol kirim ulang.
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = window.setInterval(() => setCooldown((s) => (s > 0 ? s - 1 : 0)), 1000);
    return () => window.clearInterval(t);
  }, [cooldown]);

  // Pindah ke langkah kode: langsung fokuskan kolomnya (guru sering di tablet).
  useEffect(() => {
    if (step === 1) codeRef.current?.focus();
  }, [step]);

  function fail(err: unknown, fallback: string) {
    setLoading(false);
    setError(err instanceof ApiError ? err.detail : fallback);
  }

  /** Langkah 1 — minta kode dikirim. */
  async function submitEmail(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setNotice("");

    const nama = name.trim();
    const surel = email.trim();
    if (!nama) return setError("Nama wajib diisi.");
    if (!surel) return setError("Email wajib diisi.");
    if (!/^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$/.test(surel)) {
      return setError("Alamat email belum benar. Contoh: nama@sekolah.id");
    }

    setLoading(true);
    try {
      const res = await signupStart(surel, nama);
      setEmail(res.email);
      setCode("");
      setCooldown(res.resendAfterSec || RESEND_COOLDOWN);
      setStep(1);
      setNotice(`Kode verifikasi dikirim ke ${res.email}.`);
      setLoading(false);
    } catch (err) {
      fail(err, "Gagal mengirim kode verifikasi. Periksa koneksi lalu coba lagi.");
    }
  }

  /** Kirim ulang: memakai endpoint yang sama; kode lama otomatis tidak berlaku. */
  async function resend() {
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const res = await signupStart(email, name.trim());
      setCode("");
      setCooldown(res.resendAfterSec || RESEND_COOLDOWN);
      setNotice(`Kode baru dikirim ke ${res.email}. Kode sebelumnya tidak berlaku lagi.`);
      setLoading(false);
      codeRef.current?.focus();
    } catch (err) {
      fail(err, "Gagal mengirim ulang kode. Coba lagi sebentar lagi.");
    }
  }

  /** Langkah 2 — verifikasi kode. */
  async function submitCode(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const kode = code.trim();
    if (kode.length !== 6) return setError("Kode verifikasi terdiri dari 6 angka.");

    setLoading(true);
    try {
      const res = await signupVerify(email, kode);
      setTicket(res.ticket);
      setStep(2);
      setNotice("");
      setLoading(false);
    } catch (err) {
      fail(err, "Kode tidak dapat diverifikasi. Coba lagi.");
    }
  }

  /** Langkah 3 — buat password & akun. */
  async function submitPassword(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < MIN_PASSWORD) {
      return setError(`Password minimal ${MIN_PASSWORD} karakter.`);
    }
    if (password !== password2) {
      return setError("Konfirmasi password belum sama.");
    }

    setLoading(true);
    try {
      const res = await signupComplete(ticket, password);
      // Sama seperti login: token disimpan di cookie httpOnly oleh route handler.
      await setSessionToken(res.token);
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      fail(err, "Akun gagal dibuat. Coba lagi sebentar lagi.");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper p-4 sm:p-6">
      <div className="w-full max-w-md rounded-xl border border-paper-200 bg-white p-6 sm:p-8">
        <div className="mb-6">
          <Link
            href="/"
            className="mb-4 inline-flex items-center gap-2.5 rounded-md focus-visible:outline-none"
            aria-label="BacaLaras — beranda"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-slate-900 text-paper">
              <Icon name="book-open" size={20} />
            </span>
            <span className="font-serif text-2xl font-semibold tracking-tight text-slate-900">
              BacaLaras
            </span>
          </Link>
          <h1 className="font-serif text-h2 font-semibold text-slate-900">Daftar Akun</h1>
          <p className="mt-1 text-sm italic text-slate-500">Baca. Didengar. Dipahami.</p>
        </div>

        <Stepper steps={STEPS} current={step} className="mb-6 justify-center" />

        {notice && !error && (
          <p
            role="status"
            className="mb-4 flex items-start gap-2 rounded-md border border-paper-200 bg-paper-100 px-3 py-2 text-sm text-slate-700"
          >
            <Icon name="check-circle" size={16} className="mt-0.5 shrink-0" />
            <span>{notice}</span>
          </p>
        )}

        {error && (
          <p
            role="alert"
            className="mb-4 flex items-start gap-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
          >
            <Icon name="alert-triangle" size={16} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </p>
        )}

        {/* ---------- Langkah 1: email + nama ---------- */}
        {step === 0 && (
          <form onSubmit={submitEmail} className="space-y-4" noValidate>
            <div>
              <label className={LABEL_CLASS} htmlFor="name">
                Nama Lengkap
              </label>
              <input
                id="name"
                type="text"
                autoComplete="name"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (error) setError("");
                }}
                className={INPUT_CLASS}
                placeholder="Nama Anda"
              />
            </div>

            <div>
              <label className={LABEL_CLASS} htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (error) setError("");
                }}
                className={INPUT_CLASS}
                placeholder="nama@sekolah.id"
              />
              <p className="mt-1 text-xs text-slate-500">
                Kode verifikasi akan dikirim ke alamat ini.
              </p>
            </div>

            <Button type="submit" variant="primary" size="lg" loading={loading} className="w-full">
              {loading ? "Mengirim kode…" : "Kirim Kode Verifikasi"}
            </Button>
          </form>
        )}

        {/* ---------- Langkah 2: kode OTP ---------- */}
        {step === 1 && (
          <form onSubmit={submitCode} className="space-y-4" noValidate>
            <div>
              <label className={LABEL_CLASS} htmlFor="code">
                Kode Verifikasi
              </label>
              <input
                id="code"
                ref={codeRef}
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                value={code}
                onChange={(e) => {
                  setCode(e.target.value.replace(/\D/g, "").slice(0, 6));
                  if (error) setError("");
                }}
                className={cn(INPUT_CLASS, "h-14 text-center text-2xl tracking-[0.5em]")}
                placeholder="000000"
                aria-describedby="code-hint"
              />
              <p id="code-hint" className="mt-1 text-xs text-slate-500">
                Masukkan 6 angka dari email. Kode berlaku 10 menit.
              </p>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              disabled={code.length !== 6}
              className="w-full"
            >
              {loading ? "Memeriksa…" : "Verifikasi"}
            </Button>

            <div className="flex items-center justify-between text-sm">
              <button
                type="button"
                onClick={() => {
                  setStep(0);
                  setError("");
                  setNotice("");
                  setCode("");
                }}
                className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-700 focus-visible:outline-none"
              >
                <Icon name="arrow-left" size={16} />
                Ubah email
              </button>

              <button
                type="button"
                onClick={resend}
                disabled={cooldown > 0 || loading}
                className={cn(
                  "font-medium focus-visible:outline-none",
                  cooldown > 0 || loading
                    ? "cursor-not-allowed text-slate-400"
                    : "text-brand-600 hover:text-brand-700"
                )}
              >
                {cooldown > 0 ? `Kirim ulang dalam ${cooldown} dtk` : "Kirim ulang kode"}
              </button>
            </div>
          </form>
        )}

        {/* ---------- Langkah 3: password ---------- */}
        {step === 2 && (
          <form onSubmit={submitPassword} className="space-y-4" noValidate>
            <p className="flex items-start gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              <Icon name="check-circle" size={16} className="mt-0.5 shrink-0" />
              <span>
                Email <strong className="font-semibold">{email}</strong> terverifikasi.
                Buat password untuk menyelesaikan pendaftaran.
              </span>
            </p>

            <div>
              <label className={LABEL_CLASS} htmlFor="password">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError("");
                  }}
                  className={cn(INPUT_CLASS, "pr-11")}
                  placeholder="Minimal 8 karakter"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Sembunyikan password" : "Tampilkan password"}
                  aria-pressed={showPassword}
                  className="absolute right-1 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 hover:text-slate-600 focus-visible:outline-none"
                >
                  <Icon name={showPassword ? "eye-off" : "eye"} size={18} />
                </button>
              </div>
            </div>

            <div>
              <label className={LABEL_CLASS} htmlFor="password2">
                Ulangi Password
              </label>
              <input
                id="password2"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                value={password2}
                onChange={(e) => {
                  setPassword2(e.target.value);
                  if (error) setError("");
                }}
                className={INPUT_CLASS}
                placeholder="Ulangi password"
              />
            </div>

            <Button type="submit" variant="primary" size="lg" loading={loading} className="w-full">
              {loading ? "Membuat akun…" : "Buat Akun & Masuk"}
            </Button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-slate-500">
          Sudah punya akun?{" "}
          <Link
            href="/login"
            className="font-semibold text-brand-700 underline-offset-2 hover:underline focus-visible:outline-none"
          >
            Masuk
          </Link>
        </p>

        <p className="mt-4 text-center text-xs leading-relaxed text-slate-400">
          BacaLaras membantu asesmen, bukan alat diagnosis medis.
        </p>
      </div>
    </main>
  );
}

export default function SignupPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-paper p-4">
          <p className="text-sm text-slate-500">Menyiapkan…</p>
        </main>
      }
    >
      <SignupForm />
    </Suspense>
  );
}
