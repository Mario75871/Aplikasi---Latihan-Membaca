"use client";

import * as React from "react";
import { Icon } from "@/components/ui/icons";
import { StatusText } from "@/components/ui/StatusBadge";
import type { AdaptiveStatus } from "@/lib/tokens";
import { cn } from "@/lib/utils";

export interface PickableStudent {
  id: string;
  name: string;
  classLabel: string;
  grade: 1 | 2 | 3;
  status: AdaptiveStatus | null;
}

/**
 * StudentPicker — daftar siswa yang dapat dipilih untuk asesmen.
 * Menampilkan kelas, tingkat, dan status terakhir agar guru tahu siapa yang dipilih.
 * Kartu dapat diklik penuh dengan state terpilih yang jelas.
 */
export function StudentPicker({
  students,
  selectedId,
  onSelect,
}: {
  students: PickableStudent[];
  selectedId?: string;
  onSelect: (id: string) => void;
}) {
  const [query, setQuery] = React.useState("");

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? students.filter((s) => s.name.toLowerCase().includes(q)) : students;
  }, [students, query]);

  return (
    <div className="space-y-4">
      <div className="relative w-full sm:max-w-sm">
        <Icon
          name="search"
          size={18}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
        />
        <label htmlFor="pick-student-search" className="sr-only">
          Cari siswa
        </label>
        <input
          id="pick-student-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Cari nama siswa…"
          className="h-11 w-full rounded-md border border-slate-200 bg-white pl-10 pr-3 text-sm text-slate-800 placeholder:text-slate-400 hover:border-brand-300 focus-visible:outline-none"
        />
      </div>

      <div
        role="radiogroup"
        aria-label="Pilih siswa"
        className="grid max-h-[26rem] gap-3 overflow-y-auto pr-1 sm:grid-cols-2"
      >
        {filtered.length === 0 ? (
          <p className="col-span-full rounded-md bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
            Tidak ada siswa yang cocok dengan “{query}”.
          </p>
        ) : (
          filtered.map((s) => {
            const selected = s.id === selectedId;
            return (
              <button
                key={s.id}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => onSelect(s.id)}
                className={cn(
                  "flex items-center gap-3 rounded-lg border-2 bg-white p-3 text-left transition-colors",
                  "hover:border-brand-300 focus-visible:outline-none",
                  selected ? "border-brand-500 bg-brand-50/50" : "border-slate-200"
                )}
              >
                <span
                  aria-hidden
                  className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold",
                    selected ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-500"
                  )}
                >
                  {s.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-slate-800">{s.name}</p>
                  <p className="text-xs text-slate-500">
                    {s.classLabel} · Tingkat {s.grade}
                  </p>
                </div>
                <StatusText status={s.status} />
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
