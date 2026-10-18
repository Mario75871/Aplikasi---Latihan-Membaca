"use client";

import { useRouter } from "next/navigation";
import { StatusText } from "@/components/ui/StatusBadge";
import { Icon } from "@/components/ui/icons";
import { EmptyState } from "@/components/ui/States";
import type { AdaptiveStatus } from "@/lib/tokens";

export interface AllStudentRow {
  id: string;
  name: string;
  classLabel: string;
  assessmentCount: number;
  status: AdaptiveStatus | null;
  lastDate: string | null;
}

/**
 * AllStudentsTable — daftar seluruh siswa (lintas kelas) yang tenang.
 * Tanpa tombol biru per baris; klik baris membuka profil / mulai asesmen.
 */
export function AllStudentsTable({ students }: { students: AllStudentRow[] }) {
  const router = useRouter();

  if (students.length === 0) {
    return (
      <EmptyState
        icon="users"
        title="Belum ada siswa"
        description="Tambahkan siswa melalui halaman kelas untuk mulai melakukan asesmen."
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-paper-200 bg-white">
      <table className="w-full text-sm">
        <thead className="text-left text-xs font-medium text-slate-500">
          <tr className="border-b border-paper-200">
            <th scope="col" className="px-4 py-2.5 font-semibold">Nama</th>
            <th scope="col" className="hidden px-4 py-2.5 font-semibold sm:table-cell">Kelas</th>
            <th scope="col" className="px-4 py-2.5 text-right font-semibold">Asesmen</th>
            <th scope="col" className="px-4 py-2.5 font-semibold">Status</th>
            <th scope="col" className="hidden px-4 py-2.5 font-semibold md:table-cell">
              Asesmen terakhir
            </th>
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
                    <span
                      aria-hidden
                      className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
                    >
                      {hasAssessment ? "Lihat hasil" : "Mulai asesmen"}
                      <Icon name="arrow-right" size={13} />
                    </span>
                  </span>
                </td>
                <td className="hidden px-4 py-3 text-slate-600 sm:table-cell">{s.classLabel}</td>
                <td className="tabular px-4 py-3 text-right text-slate-600">
                  {s.assessmentCount}
                </td>
                <td className="px-4 py-3">
                  <StatusText status={s.status} />
                </td>
                <td className="hidden px-4 py-3 text-slate-500 md:table-cell">
                  {s.lastDate ?? "–"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
