"use client";

import * as React from "react";
import { ClassKpiRow } from "@/components/teacher/ClassKpiRow";
import { StudentTable, type StudentRow } from "@/components/teacher/StudentTable";
import { AttentionList, pickAttention, type AttentionItem } from "@/components/teacher/AttentionList";
import { StatusLegend } from "@/components/ui/StatusBadge";
import { Icon } from "@/components/ui/icons";
import { STATUS_META, UNASSESSED_META, STATUS_PRIORITY, type DisplayStatus } from "@/lib/tokens";

export interface StudentRowWithStatus extends StudentRow {
  /** Status tampilan (untuk pengurutan/filter): "UNASSESSED" bila belum diases. */
  display: DisplayStatus;
  classLabel?: string;
}

/**
 * DashboardStudents — bagian interaktif dashboard guru.
 * 1) "Perlu perhatian hari ini" (maks 3 siswa prioritas).
 * 2) Tabel tenang (aksi saat hover/fokus; klik baris buka profil).
 * 3) Satu legenda status di footer (menggantikan ikon (i) tiap baris).
 *
 * KPI + filter + pencarian tetap ada; urutan prioritas sama seperti sebelumnya.
 */
export function DashboardStudents({
  rows,
  counts,
}: {
  rows: StudentRowWithStatus[];
  counts: {
    total: number;
    unassessed: number;
    intervene: number;
    stay: number;
    candidate: number;
    promote: number;
  };
}) {
  const [filter, setFilter] = React.useState<DisplayStatus | null>(null);
  const [query, setQuery] = React.useState("");

  const attention: AttentionItem[] = React.useMemo(
    () =>
      pickAttention(rows).map((r) => ({
        id: r.id,
        name: r.name,
        classLabel: r.classLabel ?? "",
        status: r.status as NonNullable<StudentRow["status"]>,
        reason: r.recommendation,
      })),
    [rows]
  );

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows
      .filter((r) => (filter ? r.display === filter : true))
      .filter((r) => (q ? r.name.toLowerCase().includes(q) : true))
      .sort((a, b) => {
        const p = STATUS_PRIORITY[a.display] - STATUS_PRIORITY[b.display];
        return p !== 0 ? p : a.name.localeCompare(b.name, "id");
      });
  }, [rows, filter, query]);

  const activeLabel = filter
    ? filter === "UNASSESSED"
      ? UNASSESSED_META.label
      : STATUS_META[filter].label
    : null;

  return (
    <div className="space-y-6">
      <ClassKpiRow
        total={counts.total}
        unassessed={counts.unassessed}
        intervene={counts.intervene}
        stay={counts.stay}
        candidate={counts.candidate}
        promote={counts.promote}
        activeStatus={filter}
        onSelect={setFilter}
      />

      <AttentionList items={attention} />

      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <h2 className="font-serif text-h3 font-semibold text-slate-800">Daftar siswa</h2>
            {activeLabel && (
              <button
                type="button"
                onClick={() => setFilter(null)}
                className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 hover:bg-brand-100"
              >
                Filter: {activeLabel}
                <span aria-hidden>✕</span>
                <span className="sr-only">Hapus filter</span>
              </button>
            )}
          </div>

          <div className="relative w-full sm:w-72">
            <Icon
              name="search"
              size={18}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <label htmlFor="student-search" className="sr-only">
              Cari siswa
            </label>
            <input
              id="student-search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Cari nama siswa…"
              className="h-11 w-full rounded-md border border-paper-200 bg-white pl-10 pr-3 text-sm text-slate-800 placeholder:text-slate-400 hover:border-brand-300 focus-visible:outline-none"
            />
          </div>
        </div>

        <p className="text-xs text-slate-500" aria-live="polite">
          Menampilkan {filtered.length} dari {rows.length} siswa
          {filtered.length !== rows.length && " (difilter)"}
        </p>

        <StudentTable students={filtered} />
      </div>

      <StatusLegend />
    </div>
  );
}
