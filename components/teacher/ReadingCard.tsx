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
 * penanda "Disarankan untuk <nama>" sesuai keputusan sebelumnya (§29).
 * State terpilih jelas (border brand + check).
 */
export function ReadingCard({
  reading,
  selected,
  recommended,
  recommendedFor,
  onSelect,
}: {
  reading: ReadingText;
  selected: boolean;
  recommended?: boolean;
  recommendedFor?: string;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cn(
        "relative flex w-full items-start gap-4 rounded-lg border-2 bg-white p-4 text-left transition-all",
        "hover:border-brand-300 focus-visible:outline-none",
        selected ? "border-brand-500 bg-brand-50/50" : "border-paper-200"
      )}
    >
      <span
        aria-hidden
        className={cn(
          "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2",
          selected ? "border-brand-500 bg-brand-500 text-white" : "border-slate-300 bg-white"
        )}
      >
        {selected && <Icon name="check-circle" size={16} strokeWidth={2.5} />}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-serif text-h3 font-semibold text-slate-900">
            {reading.title}
          </h3>
          <span
            className={cn(
              "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold",
              LEVEL_STYLE[reading.level]
            )}
          >
            Level {reading.level}
          </span>
          {recommended && (
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
              <Icon name="sparkles" size={13} />
              Disarankan{recommendedFor ? ` untuk ${recommendedFor}` : ""}
            </span>
          )}
        </div>

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
