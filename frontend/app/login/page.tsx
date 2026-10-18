"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";
import { login, setSessionToken, ApiError } from "@/lib/api";

/** Formulir login guru (FR-01, D7). Token disimpan di cookie untuk server component. */
function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!email.trim() && !password) {
      setError("Email dan password wajib diisi.");
      return;
    }
    if (!email.trim()) {
      setError("Email atau nama pengguna wajib diisi.");
      return;
    }
    if (!password) {
      setError("Password wajib diisi.");
      return;
    }

    setLoading(true);
    try {
      const res = await login(email.trim(), password);
      // Simpan token di cookie httpOnly via route handler server (integrasi #4, D5).
      await setSessionToken(res.token);
      const next = searchParams.get("next");
      router.push(next && next.startsWith("/") ? next : "/dashboard");
      router.refresh();
    } catch (err) {
      setLoading(false);
      if (err instanceof ApiError && err.status === 401) {
        setError("Email atau password salah. Coba lagi ya.");
      } else if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Gagal masuk. Periksa koneksi lalu coba lagi.");
      }
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-paper-50 p-4 sm:p-6">
      <div className="w-full max-w-sm rounded-xl border border-paper-200 bg-white p-6 sm:p-8">
        <div className="mb-6">
          <div className="mb-4 flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-slate-900 text-paper">
              <Icon name="book-open" size={20} />
            </span>
            <span className="font-serif text-2xl font-semibold tracking-tight text-slate-900">
              BacaLaras
            </span>
          </div>
          <h1 className="font-serif text-h2 font-semibold text-slate-900">
            Masuk sebagai guru
          </h1>
          <p className="mt-1 text-sm italic text-slate-500">Baca. Didengar. Dipahami.</p>
        </div>

        <form onSubmit={submit} className="space-y-4" noValidate>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="email">
              Email / Nama Pengguna
            </label>
            <input
              id="email"
              type="text"
              autoComplete="username"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (error) setError("");
              }}
              aria-invalid={Boolean(error) && !email.trim()}
              className={cn(
                "h-11 w-full rounded-md border px-3 text-sm text-slate-800 placeholder:text-slate-400",
                "hover:border-brand-300 focus-visible:outline-none",
                "border-slate-200"
              )}
              placeholder="nama@sekolah.id"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="password">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) setError("");
                }}
                aria-invalid={Boolean(error) && !password}
                className={cn(
                  "h-11 w-full rounded-md border border-slate-200 px-3 pr-11 text-sm text-slate-800 placeholder:text-slate-400",
                  "hover:border-brand-300 focus-visible:outline-none"
                )}
                placeholder="••••••••"
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

          {error && (
            <p
              role="alert"
              className="flex items-start gap-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
            >
              <Icon name="alert-triangle" size={16} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </p>
          )}

          <Button type="submit" variant="primary" size="lg" loading={loading} className="w-full">
            {loading ? "Sedang masuk…" : "Masuk"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Belum punya akun?{" "}
          <Link
            href="/signup"
            className="font-semibold text-brand-700 underline-offset-2 hover:underline focus-visible:outline-none"
          >
            Daftar
          </Link>
        </p>

        <p className="mt-4 text-center text-xs leading-relaxed text-slate-400">
          BacaLaras membantu asesmen, bukan alat diagnosis medis.
        </p>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-paper-50 p-4">
          <p className="text-sm text-slate-500">Menyiapkan…</p>
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
