"use client";

import * as React from "react";
import { Icon } from "@/components/ui/icons";
import { formatEstimate } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { ReadingText } from "@/lib/types";

const LEVEL_STYLE: Record<1 | 2 | 3, string> = {
  1: "bg-sky-50 text-sky-700 border-sky-200",
  2: "bg-brand-50 text-brand-700 border-brand-200",
  3: "bg-violet-50 text-violet-700 border-violet-200",
};

/**
 * ReadingCard — kartu bacaan yang dapat diklik penuh (bukan radio kecil).
 * Menampilkan badge level, jumlah kata, tema, estimasi durasi, dan — bila cocok —
 * penanda "Disarankan untuk <nama>" sesuai keputusan sebelumnya.
 * State terpilih jelas (border brand + check).
 *
 * `locked` dipakai untuk bacaan di atas level terbuka siswa (gerbang naik level):
 * kartu tampil redup, tidak bisa diklik, dan menjelaskan apa yang harus
 * dituntaskan lebih dulu. Penegaknya tetap backend (`POST /assessments` → 409).
 */
export function ReadingCard({
  reading,
  selected,
  recommended,
  recommendedFor,
  locked = false,
  lockedReason,
  onSelect,
}: {
  reading: ReadingText;
  selected: boolean;
  recommended?: boolean;
  recommendedFor?: string;
  /** Bacaan di atas level terbuka siswa → tidak bisa dipilih. */
  locked?: boolean;
  /** Penjelasan singkat kenapa terkunci (mis. sisa bacaan yang belum tuntas). */
  lockedReason?: string;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      disabled={locked}
      aria-disabled={locked}
      onClick={locked ? undefined : onSelect}
      className={cn(
        "relative flex w-full items-start gap-4 rounded-lg border-2 bg-white p-4 text-left transition-colors",
        locked
          ? "cursor-not-allowed border-paper-200 bg-slate-50/60"
          : "hover:border-brand-300 focus-visible:outline-none",
        !locked && (selected ? "border-brand-500 bg-brand-50/50" : "border-paper-200")
      )}
    >
      <span
        aria-hidden
        className={cn(
          "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2",
          locked
            ? "border-slate-200 bg-slate-100 text-slate-400"
            : selected
              ? "border-brand-500 bg-brand-500 text-white"
              : "border-slate-300 bg-white"
        )}
      >
        {locked ? (
          <Icon name="lock" size={14} />
        ) : (
          selected && <Icon name="check-circle" size={16} strokeWidth={2.5} />
        )}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3
            className={cn(
              "font-serif text-h3 font-semibold",
              locked ? "text-slate-500" : "text-slate-900"
            )}
          >
            {reading.title}
          </h3>
          <span
            className={cn(
              "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold",
              locked ? "border-slate-200 bg-slate-100 text-slate-500" : LEVEL_STYLE[reading.level]
            )}
          >
            Level {reading.level}
          </span>
          {locked ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs font-semibold text-slate-500">
              <Icon name="lock" size={13} />
              Terkunci
            </span>
          ) : (
            recommended && (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                <Icon name="sparkles" size={13} />
                Disarankan{recommendedFor ? ` untuk ${recommendedFor}` : ""}
              </span>
            )
          )}
        </div>

        {locked && lockedReason && (
          <p className="mt-2 text-sm text-slate-500">{lockedReason}</p>
        )}

        <dl className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-500">
          <div className="flex items-center gap-1.5">
            <Icon name="book-open" size={15} className="text-slate-400" />
            <dt className="sr-only">Jumlah kata</dt>
            <dd>{reading.wordCount} kata</dd>
          </div>
          <div className="flex items-center gap-1.5">
            <Icon name="clock" size={15} className="text-slate-400" />
            <dt className="sr-only">Estimasi durasi</dt>
            <dd>{formatEstimate(reading.estimatedSeconds)}</dd>
          </div>
          <div className="flex items-center gap-1.5">
            <Icon name="graduation-cap" size={15} className="text-slate-400" />
            <dt className="sr-only">Tema</dt>
            <dd>Tema: {reading.theme}</dd>
          </div>
        </dl>
      </div>
    </button>
  );
}
