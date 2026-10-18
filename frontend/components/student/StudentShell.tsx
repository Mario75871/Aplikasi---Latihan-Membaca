import * as React from "react";
import { Icon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

export interface StudentStep {
  id: string;
  label: string;
}

/**
 * StudentShell — kerangka layar siswa (design-system §5.3).
 *
 * Prinsip Student Mode: satu tugas per layar, ikon besar, teks minimal,
 * touch target ≥ 56px, non-punitif (tanpa warna/suara menghukum).
 * Header menampilkan langkah alur Baca → Rekam → Kirim → Jawab (NFR-02).
 */
export function StudentShell({
  children,
  step,
  steps,
  className,
  fullHeight = false,
}: {
  children: React.ReactNode;
  /** Indeks langkah aktif (0-based) untuk header progres. */
  step?: number;
  steps?: StudentStep[];
  className?: string;
  /**
   * true → tinggi terkunci 100dvh (bukan min-h-screen) agar isi bisa
   * menggulir di dalam dirinya sendiri sementara kontrol tetap terlihat.
   * Dipakai layar rekam S-03 (teks panjang + kontrol sticky di bawah).
   */
  fullHeight?: boolean;
}) {
  const DEFAULT_STEPS: StudentStep[] = [
    { id: "read", label: "Baca" },
    { id: "record", label: "Rekam" },
    { id: "send", label: "Kirim" },
    { id: "answer", label: "Jawab" },
  ];
  const list = steps ?? DEFAULT_STEPS;

  return (
    <main
      className={cn(
        "flex flex-col bg-brand-50",
        fullHeight ? "h-dvh overflow-hidden" : "min-h-screen",
        className
      )}
    >
      {typeof step === "number" && (
        <header className="flex shrink-0 items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <span className="flex items-center gap-2 font-display text-lg font-extrabold text-brand-800">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500 text-white">
              <Icon name="book-open" size={18} />
            </span>
            BacaLaras
          </span>
          <ol
            className="flex items-center gap-2"
            aria-label={`Langkah ${Math.min(step + 1, list.length)} dari ${list.length}${
              list[step]?.label ? `: ${list[step].label}` : " (selesai)"
            }`}
          >
            {list.map((s, i) => {
              const done = i < step;
              const active = i === step;
              return (
                <li key={s.id} className="flex items-center gap-1.5">
                  <span
                    className={cn(
                      "h-3 w-3 rounded-full transition-colors",
                      active && "w-6 bg-brand-500",
                      done && "bg-brand-400",
                      !active && !done && "bg-slate-300"
                    )}
                    aria-current={active ? "step" : undefined}
                  />
                  <span className="sr-only">
                    {s.label}
                    {done ? " (selesai)" : active ? " (sekarang)" : ""}
                  </span>
                </li>
              );
            })}
          </ol>
        </header>
      )}
      <div className={cn("flex flex-1 flex-col", fullHeight && "min-h-0 overflow-hidden")}>
        {children}
      </div>
    </main>
  );
}
