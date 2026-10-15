"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { StatusText } from "@/components/ui/StatusBadge";
import { Icon } from "@/components/ui/icons";
import { EmptyState } from "@/components/ui/States";
import type { AdaptiveStatus } from "@/lib/tokens";

export interface StudentRow {
  id: string;
  name: string;
  /** null = belum pernah diases → tampil "Belum Diases" netral, bukan 0 merah. */
  status: AdaptiveStatus | null;
  wcpm: number | null;
  accuracy: number | null;
  comprehension: number | null;
  recommendation: string;
}

/** Nilai metrik: angka netral (tanpa warna merah) atau "–" bila belum ada. */
function Metric({ value, unit }: { value: number | null; unit?: string }) {
  if (value === null) return <span className="text-slate-300">–</span>;
  return (
    <span className="tabular font-semibold text-slate-700">
      {value}
      {unit}
    </span>
  );
}

/**
 * StudentTable — daftar siswa yang TENANG (§32).
 * Tidak ada tombol biru di setiap baris. Aksi muncul saat baris di-hover/fokus;
 * klik baris (atau Enter/Space) membuka profil siswa. Keyboard-friendly.
 * Warna hanya dipakai untuk status; angka akurasi/pemahaman netral (tanpa merah).
 */
export function StudentTable({
  students,
  emptyAction,
}: {
  students: StudentRow[];
  emptyAction?: React.ReactNode;
}) {
  const router = useRouter();

  if (students.length === 0) {
    return (
      <EmptyState
        icon="inbox"
        title="Tidak ada siswa yang cocok"
        description="Coba ubah filter status atau kata kunci pencarian."
        action={emptyAction}
      />
    );
  }

  return (
    <>
      {/* Desktop / tablet */}
      <div className="hidden overflow-hidden rounded-lg border border-paper-200 bg-white md:block">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
            <tr className="border-b border-paper-200">
              <th scope="col" className="px-4 py-2.5 font-semibold">Siswa</th>
              <th scope="col" className="px-4 py-2.5 text-right font-semibold">WCPM</th>
              <th scope="col" className="px-4 py-2.5 text-right font-semibold">Akurasi</th>
              <th scope="col" className="px-4 py-2.5 text-right font-semibold">Pemahaman</th>
              <th scope="col" className="px-4 py-2.5 font-semibold">Status</th>
              <th scope="col" className="hidden px-4 py-2.5 font-semibold xl:table-cell">Rekomendasi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-paper-100">
            {students.map((s) => {
              const hasAssessment = s.status !== null;
              const target = hasAssessment ? `/students/${s.id}` : `/assess?student=${s.id}`;
              return (
                <tr
                  key={s.id}
                  tabIndex={0}
                  role="link"
                  aria-label={`${s.name} — buka ${hasAssessment ? "profil" : "mulai asesmen"}`}
                  onClick={() => router.push(target)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      router.push(target);
                    }
                  }}
                  className="group cursor-pointer transition-colors hover:bg-paper-50 focus-visible:bg-paper-50 focus-visible:outline-none"
                >
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-2">
                      <span className="font-medium text-slate-800 group-hover:text-brand-700">
                        {s.name}
                      </span>
                      {/* Petunjuk aksi saat hover/fokus — teks, bukan tombol biru. */}
                      <span
                        aria-hidden
                        className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
                      >
                        {hasAssessment ? "Lihat hasil" : "Mulai asesmen"}
                        <Icon name="arrow-right" size={13} />
                      </span>
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Metric value={s.wcpm} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Metric value={s.accuracy} unit="%" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Metric value={s.comprehension} unit="%" />
                  </td>
                  <td className="px-4 py-3">
                    <StatusText status={s.status} />
                  </td>
                  <td className="hidden max-w-xs truncate px-4 py-3 text-slate-500 xl:table-cell">
                    {s.recommendation}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile — stacked rows (tetap tanpa tombol biru) */}
      <ul className="space-y-2 md:hidden">
        {students.map((s) => {
          const hasAssessment = s.status !== null;
          const target = hasAssessment ? `/students/${s.id}` : `/assess?student=${s.id}`;
          return (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => router.push(target)}
                className="flex w-full items-center justify-between gap-3 rounded-lg border border-paper-200 bg-white px-4 py-3 text-left focus-visible:outline-none"
              >
                <span className="min-w-0">
                  <span className="block font-medium text-slate-800">{s.name}</span>
                  <span className="mt-0.5 block">
                    <StatusText status={s.status} />
                  </span>
                </span>
                <Icon name="chevron-right" size={18} className="shrink-0 text-slate-400" />
              </button>
            </li>
          );
        })}
      </ul>
    </>
  );
}
