"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StudentShell } from "@/components/student/StudentShell";
import { Icon } from "@/components/ui/icons";

/**
 * S-07 Selesai — progres sederhana, TANPA nilai menghakimi.
 * Siswa tidak melihat status INTERVENE/PROMOTE maupun angka WCPM/Akurasi.
 */
function DoneScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const assessmentId = params.get("assessment");

  function finish() {
    // Kembalikan perangkat ke guru: bila ada hasil, buka halaman hasil.
    router.push(assessmentId ? `/assessments/${assessmentId}` : "/dashboard");
  }

  return (
    <StudentShell step={4}>
      <div className="flex flex-1 flex-col items-center justify-center gap-8 px-6 pb-16 text-center">
        <span className="flex h-24 w-24 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
          <Icon name="check-circle" size={56} strokeWidth={2.5} />
        </span>

        <div>
          <h1 className="font-serif text-3xl font-semibold text-slate-800 sm:text-4xl">
            Kamu sudah membaca!
          </h1>
          <p className="mt-2 text-lg text-slate-600">
            Terima kasih sudah berusaha. 👏
          </p>
        </div>

        <div className="w-full max-w-sm rounded-2xl bg-white p-6 text-left shadow-sm">
          <p className="mb-2 text-sm font-semibold text-slate-500">Kamu sudah selesai</p>
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex items-center gap-2">
              <Icon name="check-circle" size={16} className="text-emerald-500" />
              Membaca dengan suara jelas
            </li>
            <li className="flex items-center gap-2">
              <Icon name="check-circle" size={16} className="text-emerald-500" />
              Menjawab pertanyaan cerita
            </li>
          </ul>
          <p className="mt-4 text-sm text-slate-500">
            Terus berlatih ya, kamu semakin baik!
          </p>
        </div>

        <button
          type="button"
          onClick={finish}
          className="flex h-16 w-full max-w-sm items-center justify-center gap-2 rounded-2xl bg-brand-500 text-xl font-bold text-white transition-colors hover:bg-brand-600 focus-visible:outline-none"
        >
          Selesai
          <Icon name="arrow-right" size={24} />
        </button>
      </div>
    </StudentShell>
  );
}

export default function StudentDonePage() {
  return (
    <Suspense
      fallback={
        <StudentShell step={4}>
          <div className="flex flex-1 items-center justify-center px-6 pb-16">
            <p className="text-lg text-slate-500">Menyelesaikan…</p>
          </div>
        </StudentShell>
      }
    >
      <DoneScreen />
    </Suspense>
  );
}
