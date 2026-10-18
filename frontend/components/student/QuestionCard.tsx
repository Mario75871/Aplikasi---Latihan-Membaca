"use client";

import * as React from "react";
import { COMPETENCY_META, type Competency } from "@/lib/tokens";
import { Icon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

export interface QuestionOption {
  id: string;
  text: string;
}

/**
 * QuestionCard — satu pertanyaan pemahaman (§17).
 * Badge kompetensi (Retrieve/Interpret/Reflect) + opsi besar (touch ≥ 56px).
 * Non-punitif: tidak ada umpan balik menghukum; pilihan jelas dan besar.
 */
export function QuestionCard({
  competency,
  question,
  options,
  index,
  total,
  value,
  onChange,
  onNext,
}: {
  competency: Competency;
  question: string;
  options: QuestionOption[];
  index: number;
  total: number;
  value?: string;
  onChange: (id: string) => void;
  onNext: () => void;
}) {
  const meta = COMPETENCY_META[competency];

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-6">
      <p className="text-center text-sm font-semibold text-slate-500">
        Pertanyaan {index} dari {total}
      </p>

      <span
        className={cn(
          "mx-auto inline-flex w-fit items-center rounded-full bg-white px-4 py-1.5 text-sm font-semibold shadow-sm",
          meta.color
        )}
      >
        {meta.short}
      </span>

      <h2 className="text-center font-display text-2xl font-bold leading-snug text-slate-800 sm:text-3xl">
        {question}
      </h2>

      <div role="radiogroup" aria-label="Pilihan jawaban" className="flex flex-col gap-3">
        {options.map((opt) => {
          const selected = value === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(opt.id)}
              className={cn(
                "flex min-h-[64px] w-full items-center gap-4 rounded-2xl border-2 bg-white px-5 py-4 text-left text-xl transition-colors",
                "focus-visible:outline-none",
                selected
                  ? "border-brand-500 bg-brand-50"
                  : "border-slate-200 hover:border-brand-300 hover:bg-brand-50/40"
              )}
            >
              <span
                aria-hidden
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2",
                  selected ? "border-brand-500 bg-brand-500 text-white" : "border-slate-300"
                )}
              >
                {selected && <Icon name="check-circle" size={16} strokeWidth={2.5} />}
              </span>
              <span className="text-slate-800">{opt.text}</span>
            </button>
          );
        })}
      </div>

      <button
        type="button"
        disabled={!value}
        onClick={onNext}
        className={cn(
          "flex h-16 w-full items-center justify-center gap-2 rounded-2xl text-lg font-bold transition-colors focus-visible:outline-none",
          value
            ? "bg-brand-500 text-white hover:bg-brand-600"
            : "cursor-not-allowed bg-slate-200 text-slate-400"
        )}
      >
        {index === total ? "Selesai" : "Lanjut"}
        {index !== total && <Icon name="arrow-right" size={22} />}
      </button>
    </div>
  );
}
