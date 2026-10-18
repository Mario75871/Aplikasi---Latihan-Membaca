"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { Modal } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { ApiError, createClass } from "@/lib/api";

const GRADES = [1, 2, 3] as const;

const INPUT_CLASS = cn(
  "h-11 w-full rounded-md border border-slate-200 px-3 text-sm text-slate-800",
  "placeholder:text-slate-400 hover:border-brand-300 focus-visible:outline-none"
);

const LABEL_CLASS = "mb-1 block text-sm font-medium text-slate-700";

/**
 * Tombol "Buat Kelas" beserta dialognya (POST /classes).
 *
 * Dibuat sebagai komponen klien tersendiri supaya halaman pemanggilnya
 * (`app/classes/page.tsx`) tetap server component. `children` adalah isi tombol,
 * sehingga tiap pemanggil bebas memakai label responsifnya sendiri.
 */
export function CreateClassButton({
  children,
  variant = "primary",
  size = "md",
  className,
}: {
  children: React.ReactNode;
  variant?: "primary" | "secondary";
  size?: "md" | "lg";
  className?: string;
}) {
  const router = useRouter();
  // `router.refresh()` memuat ulang halaman server (~2 putaran ≈ 2,6 detik). Tanpa
  // transisi, tombol pemicu tampak diam selama itu — bagian dari kesan "lemot".
  const [isPending, startTransition] = React.useTransition();
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [grade, setGrade] = React.useState<1 | 2 | 3>(1);
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  function reset() {
    setName("");
    setGrade(1);
    setError("");
  }

  /**
   * Tutup karena aksi pengguna (Escape, klik latar, tombol Batal).
   * Diabaikan selama penyimpanan berjalan supaya hasilnya tidak hilang.
   */
  function requestClose() {
    if (loading) return;
    setOpen(false);
    reset();
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const nama = name.trim();
    if (!nama) return setError("Nama kelas wajib diisi.");

    setLoading(true);
    try {
      await createClass({ name: nama, grade });
      setLoading(false);
      setOpen(false);
      reset();
      // Halaman server memuat ulang daftar kelas, jadi kartu barunya langsung
      // tampil. Dibungkus transisi agar `isPending` menyala di tombol pemicu
      // selama penyegaran berlangsung.
      startTransition(() => router.refresh());
    } catch (err) {
      setLoading(false);
      setError(
        err instanceof ApiError ? err.detail : "Kelas gagal dibuat. Coba lagi sebentar lagi."
      );
    }
  }

  return (
    <>
      <Button
        variant={variant}
        size={size}
        className={className}
        onClick={() => setOpen(true)}
        loading={isPending}
      >
        {children}
      </Button>

      {open && (
        <Modal
          title="Buat Kelas"
          description="Kelas baru langsung menjadi milik akun Anda."
          onClose={requestClose}
        >
          <form onSubmit={submit} className="space-y-4" noValidate>
            <div>
              <label className={LABEL_CLASS} htmlFor="class-name">
                Nama Kelas
              </label>
              <input
                id="class-name"
                type="text"
                autoComplete="off"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (error) setError("");
                }}
                className={INPUT_CLASS}
                placeholder="Contoh: Kelas 3A"
              />
            </div>

            <fieldset>
              <legend className={LABEL_CLASS}>Tingkat</legend>
              <div className="flex gap-2">
                {GRADES.map((g) => (
                  <label
                    key={g}
                    className={cn(
                      "flex h-11 flex-1 cursor-pointer items-center justify-center rounded-sm border",
                      "text-sm font-medium transition-colors",
                      "focus-within:ring-2 focus-within:ring-brand-500",
                      grade === g
                        ? "border-brand-600 bg-brand-50 text-brand-700"
                        : "border-slate-200 text-slate-600 hover:border-brand-300"
                    )}
                  >
                    <input
                      type="radio"
                      name="grade"
                      value={g}
                      checked={grade === g}
                      onChange={() => setGrade(g)}
                      className="sr-only"
                    />
                    Kelas {g}
                  </label>
                ))}
              </div>
            </fieldset>

            {error && (
              <p
                role="alert"
                className="flex items-start gap-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
              >
                <Icon name="alert-triangle" size={16} className="mt-0.5 shrink-0" />
                <span>{error}</span>
              </p>
            )}

            <div className="flex justify-end gap-2 pt-1">
              <Button type="button" variant="ghost" size="md" onClick={requestClose} disabled={loading}>
                Batal
              </Button>
              <Button type="submit" variant="primary" size="md" loading={loading}>
                {loading ? "Menyimpan…" : "Simpan Kelas"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
