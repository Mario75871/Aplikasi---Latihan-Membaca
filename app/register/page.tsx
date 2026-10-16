"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";
import { register, setSessionToken, ApiError } from "@/lib/api";

/**
 * Halaman pendaftaran guru.
 *
 * CATATAN: backend `POST /auth/register` BELUM tersedia. Formulir ini sudah
 * siap-pakai; sampai endpoint ada, pengiriman akan gagal dan ditampilkan pesan
 * ramah ("Pendaftaran belum tersedia"), bukan error teknis mentah.
 * Begitu endpoint tersedia (sesi backend terpisah), alur ini langsung berfungsi.
 */
const MIN_PASSWORD = 6;

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setNotice("");

    const cleanName = name.trim();
    const cleanEmail = email.trim();

    if (!cleanName) return setError("Nama wajib diisi.");
    if (!cleanEmail) return setError("Email wajib diisi.");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail))
      return setError("Format email belum benar. Contoh: nama@sekolah.id.");
    if (password.length < MIN_PASSWORD)
      return setError(`Password minimal ${MIN_PASSWORD} karakter.`);
    if (password !== confirm) return setError("Konfirmasi password belum sama.");

    setLoading(true);
    try {
      const res = await register(cleanName, cleanEmail, password);
      await setSessionToken(res.token);
      window.location.href = "/dashboard";
    } catch (err) {
      setLoading(false);
      if (err instanceof ApiError && err.status === 409) {
        setError("Email ini sudah terdaftar. Coba masuk saja.");
      } else if (err instanceof ApiError && (err.status === 404 || err.status === 405)) {
        setNotice(
          "Pendaftaran belum tersedia. Untuk sementara, gunakan akun demo atau hubungi admin sekolah."
        );
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Data yang dikirim belum lengkap atau tidak valid.");
      } else if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setNotice("Pendaftaran belum tersedia saat ini. Coba lagi nanti ya.");
      }
    }
  }

  const fieldClass = cn(
    "h-11 w-full rounded-md border border-slate-200 px-3 text-sm text-slate-800 placeholder:text-slate-400",
    "hover:border-brand-300 focus-visible:outline-none"
  );

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper-50 p-4 sm:p-6">
      <div className="w-full max-w-sm rounded-xl border border-paper-200 bg-white p-6 sm:p-8">
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
          <h1 className="font-serif text-h2 font-semibold text-slate-900">
            Daftar sebagai guru
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Buat akun untuk mulai menilai membaca siswa.
          </p>
        </div>

        <form onSubmit={submit} className="space-y-4" noValidate>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="name">
              Nama lengkap
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
              className={fieldClass}
              placeholder="Nama Anda"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="email">
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
              className={fieldClass}
              placeholder="nama@sekolah.id"
            />
          </div>

          <div>
            <label
              className="mb-1 block text-sm font-medium text-slate-700"
              htmlFor="password"
            >
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
                className={cn(fieldClass, "pr-11")}
                placeholder={`Minimal ${MIN_PASSWORD} karakter`}
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
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="confirm">
              Konfirmasi password
            </label>
            <input
              id="confirm"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => {
                setConfirm(e.target.value);
                if (error) setError("");
              }}
              className={fieldClass}
              placeholder="Ulangi password"
            />
          </div>

          {error && (
            <p
              role="alert"
              className="flex items-start gap-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
            >
              <Icon name="alert-triangle" size={16} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </p>
          )}

          {notice && (
            <p
              role="status"
              className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700"
            >
              <Icon name="shield-alert" size={16} className="mt-0.5 shrink-0" />
              <span>{notice}</span>
            </p>
          )}

          <Button type="submit" variant="primary" size="lg" loading={loading} className="w-full">
            {loading ? "Mendaftarkan…" : "Daftar"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Sudah punya akun?{" "}
          <Link
            href="/login"
            className="font-semibold text-brand-700 underline-offset-2 hover:underline focus-visible:outline-none"
          >
            Masuk
          </Link>
        </p>
      </div>
    </main>
  );
}
