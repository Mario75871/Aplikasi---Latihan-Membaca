"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StudentShell } from "@/components/student/StudentShell";
import { Icon } from "@/components/ui/icons";
import { getReading } from "@/lib/api";
import type { ReadingText } from "@/lib/types";

/**
 * S-01 Halaman Mulai — layar ramah anak sebelum membaca.
 * Satu tugas, satu CTA besar, teks minimal + ikon besar (Student Mode §1.1).
 * Tidak menampilkan status/nilai apa pun (non-punitif).
 */
function StartScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const readingId = params.get("reading");
  const [reading, setReading] = useState<ReadingText | null>(null);

  useEffect(() => {
    let active = true;
    getReading(readingId)
      .then((r) => active && setReading(r))
      .catch(() => active && setReading(null));
    return () => {
      active = false;
    };
  }, [readingId]);

  function start() {
    const qs = new URLSearchParams();
    if (readingId) qs.set("reading", readingId);
    const student = params.get("student");
    if (student) qs.set("student", student);
    const assessment = params.get("assessment");
    if (assessment) qs.set("assessment", assessment);
    router.push(`/assess/read?${qs.toString()}`);
  }

  return (
    <StudentShell step={0}>
      <div className="flex flex-1 flex-col items-center justify-center gap-8 px-6 pb-16 text-center">
        <span className="flex h-24 w-24 items-center justify-center rounded-full bg-brand-100 text-brand-600">
          <Icon name="book-open" size={52} strokeWidth={2.5} />
        </span>

        <div className="space-y-3">
          <h1 className="font-serif text-3xl font-semibold text-slate-800 sm:text-4xl">
            Hai! Ayo membaca 👋
          </h1>
          <p className="mx-auto max-w-md text-lg text-slate-600">
            Bacalah dengan suara jelas. Ibu/Bapak guru akan mendengarkan.
          </p>
        </div>

        {reading && (
          <div className="w-full max-w-sm rounded-2xl bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold text-slate-500">Bacaan hari ini</p>
            <p className="mt-1 font-serif text-xl font-semibold text-slate-800">
              {reading.title}
            </p>
            <p className="mt-1 text-sm text-slate-500">
              {reading.wordCount} kata · pelan-pelan saja tidak apa-apa
            </p>
          </div>
        )}

        <button
          type="button"
          onClick={start}
          className="flex h-16 w-full max-w-sm items-center justify-center gap-2 rounded-2xl bg-brand-500 text-xl font-bold text-white transition-colors hover:bg-brand-600 focus-visible:outline-none"
        >
          Mulai
          <Icon name="arrow-right" size={24} />
        </button>
      </div>
    </StudentShell>
  );
}

export default function StudentStartPage() {
  return (
    <Suspense
      fallback={
        <StudentShell step={0}>
          <div className="flex flex-1 items-center justify-center px-6 pb-16">
            <p className="text-lg text-slate-500">Menyiapkan bacaan…</p>
          </div>
        </StudentShell>
      }
    >
      <StartScreen />
    </Suspense>
  );
}
