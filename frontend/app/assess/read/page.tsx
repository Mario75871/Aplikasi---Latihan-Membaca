"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StudentShell } from "@/components/student/StudentShell";
import { ReadingPassage } from "@/components/student/ReadingPassage";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { getReading } from "@/lib/api";
import type { ReadingText } from "@/lib/types";

type LoadState = "loading" | "ready" | "empty" | "error";

function ReadingSkeleton() {
  return (
    <div
      className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8"
      role="status"
      aria-label="Memuat bacaan"
    >
      <Skeleton className="mx-auto h-6 w-48" />
      <div className="mt-6 space-y-4">
        <Skeleton className="h-7 w-full" />
        <Skeleton className="h-7 w-11/12" />
        <Skeleton className="h-7 w-full" />
      </div>
    </div>
  );
}

/**
 * S-02 Baca Bacaan — mode fokus, teks besar, satu CTA.
 *
 * Bacaan diambil dari SUMBER DATA YANG SAMA dengan S-03 lewat query `?reading=`
 * (dikirim dari alur "Mulai Asesmen"). Tombol "Siap, Mulai Rekam" meneruskan
 * parameter yang sama ke S-03 agar teks tetap tampil saat merekam.
 */
function ReadScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const readingId = params.get("reading");
  const studentId = params.get("student");
  const assessmentId = params.get("assessment");

  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [reading, setReading] = useState<ReadingText | null>(null);

  useEffect(() => {
    let active = true;
    setLoadState("loading");
    getReading(readingId)
      .then((r) => {
        if (!active) return;
        if (!r) {
          setReading(null);
          setLoadState(readingId ? "error" : "empty");
          return;
        }
        setReading(r);
        setLoadState("ready");
      })
      .catch(() => {
        if (active) setLoadState("error");
      });
    return () => {
      active = false;
    };
  }, [readingId]);

  function next() {
    if (!reading) return;
    const qs = new URLSearchParams();
    qs.set("reading", reading.id);
    if (studentId) qs.set("student", studentId);
    if (assessmentId) qs.set("assessment", assessmentId);
    router.push(`/assess/record?${qs.toString()}`);
  }

  return (
    <StudentShell step={0}>
      <div className="flex flex-1 flex-col items-center justify-center gap-8 px-6 py-6 pb-16">
        {loadState === "loading" && <ReadingSkeleton />}

        {loadState === "empty" && (
          <div className="w-full max-w-md">
            <EmptyState
              icon="book-x"
              title="Bacaan belum dipilih"
              description="Minta Ibu/Bapak guru memilih bacaan dulu ya, lalu kembali ke sini."
              action={
                <Button variant="primary" size="lg" onClick={() => router.push("/assess")}>
                  <Icon name="arrow-left" size={20} />
                  Pilih Bacaan
                </Button>
              }
            />
          </div>
        )}

        {loadState === "error" && (
          <div className="w-full max-w-md">
            <ErrorState
              title="Bacaan belum bisa dibuka"
              description="Jaringan mungkin sedang sibuk. Coba muat ulang bacaan ya."
              onRetry={() => {
                setLoadState("loading");
                getReading(readingId)
                  .then((r) => {
                    if (r) {
                      setReading(r);
                      setLoadState("ready");
                    } else {
                      setLoadState("error");
                    }
                  })
                  .catch(() => setLoadState("error"));
              }}
              fallbackAction={
                <Button variant="secondary" size="lg" onClick={() => router.push("/assess")}>
                  <Icon name="arrow-left" size={20} />
                  Pilih Bacaan
                </Button>
              }
            />
          </div>
        )}

        {loadState === "ready" && reading && (
          <>
            <div className="w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
              <ReadingPassage
                title={reading.title}
                content={reading.content}
                level={reading.level}
              />
            </div>

            <button
              type="button"
              onClick={next}
              className="flex h-16 items-center justify-center gap-2 rounded-2xl bg-brand-500 px-8 text-xl font-bold text-white transition-colors hover:bg-brand-600 focus-visible:outline-none"
            >
              <Icon name="mic" size={24} strokeWidth={2.5} />
              Siap, Mulai Rekam
            </button>
          </>
        )}
      </div>
    </StudentShell>
  );
}

export default function StudentReadPage() {
  return (
    <Suspense
      fallback={
        <StudentShell step={0}>
          <div className="flex flex-1 items-center justify-center px-6 pb-16">
            <ReadingSkeleton />
          </div>
        </StudentShell>
      }
    >
      <ReadScreen />
    </Suspense>
  );
}
