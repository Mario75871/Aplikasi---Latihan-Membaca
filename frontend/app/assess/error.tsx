"use client";

import { useEffect } from "react";
import { TeacherShell } from "@/components/teacher/TeacherShell";
import { ErrorState } from "@/components/ui/States";

/** Error state alur Mulai Asesmen. */
export default function AssessError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <TeacherShell title="Mulai Asesmen" breadcrumb="Dashboard › Asesmen › Mulai">
      <ErrorState
        title="Gagal memuat data asesmen"
        description="Terjadi masalah saat menyiapkan asesmen. Coba lagi ya."
        onRetry={reset}
      />
    </TeacherShell>
  );
}
