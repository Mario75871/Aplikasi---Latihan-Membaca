"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { Modal } from "@/components/ui/Modal";
import { cn } from "@/lib/utils";
import { ApiError, createStudent } from "@/lib/api";
import type { ClassRoom } from "@/lib/types";

const INPUT_CLASS = cn(
  "h-11 w-full rounded-md border border-slate-200 px-3 text-sm text-slate-800",
  "placeholder:text-slate-400 hover:border-brand-300 focus-visible:outline-none"
);

const LABEL_CLASS = "mb-1 block text-sm font-medium text-slate-700";

/**
 * Tombol "Tambah Siswa" beserta dialognya (POST /students).
 *
 * Tingkat siswa tidak ditanyakan: backend menyimpan `grade` per siswa, tetapi
 * selalu sama dengan tingkat kelasnya (lihat konvensi seed), jadi nilainya
 * diturunkan dari kelas yang dipilih dan ditampilkan sebagai keterangan.
 *
 * `classes` dikirim dari server component pemanggil. Halaman kelas cukup
 * mengirim `[cls]` sehingga siswanya pasti masuk ke kelas itu.
 */
export function CreateStudentButton({
  classes,
  defaultClassId,
  children,
  variant = "secondary",
  size = "md",
  className,
}: {
  classes: ClassRoom[];
  defaultClassId?: string;
  children: React.ReactNode;
  variant?: "primary" | "secondary";
  size?: "md" | "lg";
  className?: string;
}) {
  const router = useRouter();
  // `router.refresh()` memuat ulang halaman server (~1–2 putaran); tanpa transisi,
  // tombol pemicu tampak diam selama itu — bagian dari kesan "lemot".
  const [isPending, startTransition] = React.useTransition();
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [classId, setClassId] = React.useState(defaultClassId ?? classes[0]?.id ?? "");
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  const selected = classes.find((c) => c.id === classId) ?? null;
  const noClasses = classes.length === 0;

  function reset() {
    setName("");
    setClassId(defaultClassId ?? classes[0]?.id ?? "");
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
    if (!nama) return setError("Nama siswa wajib diisi.");
    if (!selected) return setError("Pilih kelas untuk siswa ini.");

    setLoading(true);
    try {
      await createStudent({
        name: nama,
        grade: selected.grade,
        classId: selected.id,
        classLabel: selected.name,
      });
      setLoading(false);
      setOpen(false);
      reset();
      // Halaman server memuat ulang daftar siswa/kelas, jadi baris barunya langsung
      // tampil. Dibungkus transisi agar `isPending` menyala di tombol pemicu
      // selama penyegaran berlangsung.
      startTransition(() => router.refresh());
    } catch (err) {
      setLoading(false);
      setError(
        err instanceof ApiError ? err.detail : "Siswa gagal ditambahkan. Coba lagi sebentar lagi."
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
          title="Tambah Siswa"
          description="Siswa baru masuk ke kelas yang Anda pilih."
          onClose={requestClose}
        >
          {noClasses ? (
            <div className="space-y-4">
              <p className="flex items-start gap-2 rounded-md border border-paper-200 bg-paper-100 px-3 py-2 text-sm text-slate-700">
                <Icon name="school" size={16} className="mt-0.5 shrink-0" />
                <span>
                  Belum ada kelas. Setiap siswa harus punya kelas, jadi buat kelasnya lebih dulu.
                </span>
              </p>
              <div className="flex justify-end">
                <Link href="/classes">
                  <Button variant="primary" size="md" onClick={requestClose}>
                    <Icon name="plus" size={18} />
                    Buat Kelas
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-4" noValidate>
              <div>
                <label className={LABEL_CLASS} htmlFor="student-name">
                  Nama Lengkap
                </label>
                <input
                  id="student-name"
                  type="text"
                  autoComplete="off"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    if (error) setError("");
                  }}
                  className={INPUT_CLASS}
                  placeholder="Nama siswa"
                />
              </div>

              <div>
                <label className={LABEL_CLASS} htmlFor="student-class">
                  Kelas
                </label>
                <div className="relative">
                  <select
                    id="student-class"
                    value={classId}
                    onChange={(e) => {
                      setClassId(e.target.value);
                      if (error) setError("");
                    }}
                    className={cn(INPUT_CLASS, "appearance-none bg-white pr-9")}
                  >
                    {classes.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <Icon
                    name="chevron-down"
                    size={16}
                    className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
                  />
                </div>
                {selected && (
                  <p className="mt-1 text-xs text-slate-500">
                    Tingkat mengikuti kelas:{" "}
                    <span className="font-medium text-slate-700">Kelas {selected.grade}</span>
                  </p>
                )}
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

              <div className="flex justify-end gap-2 pt-1">
                <Button type="button" variant="ghost" size="md" onClick={requestClose} disabled={loading}>
                  Batal
                </Button>
                <Button type="submit" variant="primary" size="md" loading={loading}>
                  {loading ? "Menyimpan…" : "Simpan Siswa"}
                </Button>
              </div>
            </form>
          )}
        </Modal>
      )}
    </>
  );
}
