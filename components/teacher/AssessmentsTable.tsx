"use client";

import { useRouter } from "next/navigation";
import { StatusText } from "@/components/ui/StatusBadge";
import { Icon } from "@/components/ui/icons";
import { EmptyState } from "@/components/ui/States";
import type { AdaptiveStatus } from "@/lib/tokens";

export interface AssessmentRow {
  id: string;
  date: string;
  studentName: string;
  readingTitle: string;
  wcpm: number;
  accuracy: number;
  status: AdaptiveStatus | null;
}

/**
 * AssessmentsTable — daftar hasil asesmen yang tenang.
 * Status memakai titik + teks (bukan pil + ikon (i) per baris). Klik baris → detail.
 */
export function AssessmentsTable({ rows }: { rows: AssessmentRow[] }) {
  const router = useRouter();

  if (rows.length === 0) {
    return (
      <EmptyState
        icon="mic"
        title="Belum ada asesmen"
        description="Hasil asesmen siswa akan muncul di sini setelah Anda memulai asesmen pertama."
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-paper-200 bg-white">
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
          <tr className="border-b border-paper-200">
            <th scope="col" className="px-4 py-2.5 font-semibold">Tanggal</th>
            <th scope="col" className="px-4 py-2.5 font-semibold">Siswa</th>
            <th scope="col" className="hidden px-4 py-2.5 font-semibold md:table-cell">Bacaan</th>
            <th scope="col" className="px-4 py-2.5 text-right font-semibold">WCPM</th>
            <th scope="col" className="px-4 py-2.5 text-right font-semibold">Akurasi</th>
            <th scope="col" className="px-4 py-2.5 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-paper-100">
          {rows.map((a) => (
            <tr
              key={a.id}
              tabIndex={0}
              role="link"
              aria-label={`Hasil asesmen ${a.studentName}, ${a.date}`}
              onClick={() => router.push(`/assessments/${a.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  router.push(`/assessments/${a.id}`);
                }
              }}
              className="group cursor-pointer transition-colors hover:bg-paper-50 focus-visible:bg-paper-50 focus-visible:outline-none"
            >
              <td className="px-4 py-3 text-slate-600">{a.date}</td>
              <td className="px-4 py-3">
                <span className="flex items-center gap-2">
                  <span className="font-medium text-slate-800 group-hover:text-brand-700">
                    {a.studentName}
                  </span>
                  <span
                    aria-hidden
                    className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
                  >
                    Lihat hasil
                    <Icon name="arrow-right" size={13} />
                  </span>
                </span>
              </td>
              <td className="hidden px-4 py-3 text-slate-600 md:table-cell">{a.readingTitle}</td>
              <td className="tabular px-4 py-3 text-right text-slate-700">{a.wcpm}</td>
              <td className="tabular px-4 py-3 text-right text-slate-700">{a.accuracy}%</td>
              <td className="px-4 py-3">
                <StatusText status={a.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
