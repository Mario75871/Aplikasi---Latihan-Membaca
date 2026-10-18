"use client";

import * as React from "react";
import { Icon } from "@/components/ui/icons";

/**
 * Modal — kerangka dialog yang dipakai ulang (Buat Kelas, Tambah Siswa).
 *
 * Perilaku aksesibilitasnya mengikuti `PreviewDialog` di
 * `components/teacher/ReadingsTable.tsx`: `role="dialog"` + `aria-modal`, judul
 * ditautkan lewat `aria-labelledby`, fokus dipindah ke dialog saat dibuka lalu
 * dikembalikan ke elemen pemicu saat ditutup, dan Escape menutup dialog.
 *
 * Isi (`children`) yang mengatur tombol aksinya sendiri.
 */
export function Modal({
  title,
  description,
  onClose,
  children,
}: {
  title: string;
  description?: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const titleId = React.useId();
  const closeRef = React.useRef<HTMLButtonElement>(null);

  // `onClose` disimpan di ref supaya efek di bawah cukup berjalan sekali
  // (mount/unmount). Kalau ia jadi dependensi, efek akan jalan ulang tiap render
  // induk dan merampas fokus pengguna di tengah mengetik.
  const onCloseRef = React.useRef(onClose);
  onCloseRef.current = onClose;

  React.useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCloseRef.current();
    }
    window.addEventListener("keydown", onKey);

    return () => {
      window.removeEventListener("keydown", onKey);
      previous?.focus?.();
    };
  }, []);

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div className="absolute inset-0 bg-slate-900/50" onClick={onClose} aria-hidden />

      <div className="relative flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-xl bg-white shadow-lg">
        <div className="flex items-start justify-between gap-4 border-b border-paper-100 px-6 py-4">
          <div>
            <h2 id={titleId} className="font-serif text-h3 font-semibold text-slate-900">
              {title}
            </h2>
            {description ? <p className="mt-0.5 text-sm text-slate-500">{description}</p> : null}
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Tutup"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-slate-400 hover:bg-paper-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <Icon name="x" size={20} />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5">{children}</div>
      </div>
    </div>
  );
}
