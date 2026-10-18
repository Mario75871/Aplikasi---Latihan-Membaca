import * as React from "react";
import { Icon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

export interface Step {
  id: string;
  label: string;
}

/**
 * Stepper — indikator langkah linear.
 * Dipakai di alur Mulai Asesmen guru (Pilih Siswa → Pilih Bacaan → Serahkan)
 * dan Student Mode (Baca → Rekam → Kirim → Jawab).
 *
 * Aksesibel: memakai <ol> dengan aria-current untuk langkah aktif.
 */
export function Stepper({
  steps,
  current,
  variant = "teacher",
  className,
}: {
  steps: Step[];
  /** Indeks langkah aktif (0-based). */
  current: number;
  variant?: "teacher" | "student";
  className?: string;
}) {
  return (
    <ol
      className={cn("flex flex-wrap items-center gap-x-2 gap-y-3", className)}
      aria-label="Langkah asesmen"
    >
      {steps.map((step, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={step.id} className="flex items-center gap-2">
            <div
              className={cn(
                "flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold",
                active && "bg-brand-600 text-white",
                done && "bg-brand-50 text-brand-700",
                !active && !done && "bg-paper-100 text-slate-500"
              )}
              aria-current={active ? "step" : undefined}
            >
              <span
                aria-hidden
                className={cn(
                  "flex h-5 w-5 items-center justify-center rounded-full text-xs",
                  active && "bg-white/25 text-white",
                  done && "bg-brand-600 text-white",
                  !active && !done && "bg-paper-200 text-slate-500"
                )}
              >
                {done ? <Icon name="check-circle" size={14} strokeWidth={2.5} /> : i + 1}
              </span>
              <span className={variant === "student" ? "text-base" : undefined}>
                {step.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <Icon
                name="chevron-right"
                size={16}
                className="hidden text-slate-300 sm:block"
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
