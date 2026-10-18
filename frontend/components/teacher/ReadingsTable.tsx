"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";
import type { ReadingText } from "@/lib/types";
import { formatEstimate } from "@/lib/utils";

const LEVEL_DOT: Record<1 | 2 | 3, string> = {
  1: "bg-sky-500",
  2: "bg-brand-500",
  3: "bg-violet-500",
};

/**
 * ReadingsTable — katalog bacaan ringkas.
 * Tabel tenang: judul, level, kata, durasi, tema. Klik baris membuka PRATINJAU
 * teks dengan tombol "Pakai untuk asesmen" (menuju /assess).
 */
export function ReadingsTable({ readings }: { readings: ReadingText[] }) {
  const router = useRouter();
  const [preview, setPreview] = React.useState<ReadingText | null>(null);

  // Tutup dialog dengan Escape.
  React.useEffect(() => {
    if (!preview) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setPreview(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [preview]);

  return (
    <>
      <div className="overflow-hidden rounded-lg border border-paper-200 bg-white">
        <table className="w-full text-sm">
          <thead className="text-left text-xs font-medium text-slate-500">
            <tr className="border-b border-paper-200">
              <th scope="col" className="px-4 py-2.5 font-semibold">Judul</th>
              <th scope="col" className="px-4 py-2.5 font-semibold">Level</th>
              <th scope="col" className="px-4 py-2.5 text-right font-semibold">Kata</th>
              <th scope="col" className="hidden px-4 py-2.5 text-right font-semibold sm:table-cell">
                Durasi
              </th>
              <th scope="col" className="hidden px-4 py-2.5 font-semibold md:table-cell">Tema</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-paper-100">
            {readings.map((r) => (
              <tr
                key={r.id}
                tabIndex={0}
                role="button"
                aria-label={`Pratinjau bacaan ${r.title}`}
                onClick={() => setPreview(r)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setPreview(r);
                  }
                }}
                className="group cursor-pointer transition-colors hover:bg-paper-50 focus-visible:bg-paper-50 focus-visible:outline-none"
              >
                <td className="px-4 py-3">
                  <span className="flex items-center gap-2">
                    <span className="font-medium text-slate-800 group-hover:text-brand-700">
                      {r.title}
                    </span>
                    <span
                      aria-hidden
                      className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
                    >
                      Pratinjau
                      <Icon name="arrow-right" size={13} />
                    </span>
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-2 text-slate-700">
                    <span aria-hidden className={cn("inline-block h-2.5 w-2.5 rounded-full", LEVEL_DOT[r.level])} />
                    Level {r.level}
                  </span>
                </td>
                <td className="tabular px-4 py-3 text-right text-slate-700">{r.wordCount}</td>
                <td className="tabular hidden px-4 py-3 text-right text-slate-600 sm:table-cell">
                  {formatEstimate(r.estimatedSeconds)}
                </td>
                <td className="hidden px-4 py-3 text-slate-600 md:table-cell">{r.theme}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {preview && (
        <PreviewDialog
          reading={preview}
          onClose={() => setPreview(null)}
          onUse={() => router.push(`/assess?reading=${preview.id}`)}
        />
      )}
    </>
  );
}

/** Pratinjau teks bacaan (dialog) + CTA "Pakai untuk asesmen". */
function PreviewDialog({
  reading,
  onClose,
  onUse,
}: {
  reading: ReadingText;
  onClose: () => void;
  onUse: () => void;
}) {
  const closeRef = React.useRef<HTMLButtonElement>(null);

  // Pindahkan fokus ke dialog saat dibuka; kembalikan ke pemicu saat ditutup.
  React.useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    return () => previous?.focus?.();
  }, []);

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reading-preview-title"
    >
      <div
        className="absolute inset-0 bg-slate-900/50"
        onClick={onClose}
        aria-hidden
      />
      <div className="relative flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl bg-white shadow-lg">
        <div className="flex items-start justify-between gap-4 border-b border-paper-100 px-6 py-4">
          <div>
            <h2 id="reading-preview-title" className="font-serif text-h3 font-semibold text-slate-900">
              {reading.title}
            </h2>
            <p className="mt-0.5 text-sm text-slate-500">
              Level {reading.level} · {reading.wordCount} kata · {formatEstimate(reading.estimatedSeconds)} · Tema {reading.theme}
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Tutup pratinjau"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-slate-400 hover:bg-paper-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <Icon name="x" size={20} />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5">
          <p className="passage text-slate-900">{reading.content}</p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-paper-100 px-6 py-4">
          <p className="text-xs text-slate-400">
            {reading.questions.length} pertanyaan pemahaman
          </p>
          <Button variant="primary" size="lg" onClick={onUse}>
            <Icon name="mic" size={20} />
            Pakai untuk asesmen
          </Button>
        </div>
      </div>
    </div>
  );
}
