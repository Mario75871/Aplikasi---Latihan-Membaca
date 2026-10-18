"use client";

import { useEffect } from "react";
import { TeacherShell } from "@/components/teacher/TeacherShell";
import { ErrorState } from "@/components/ui/States";

/** Error state daftar kelas — selalu ada tombol Coba Lagi (NFR-03). */
export default function ClassesError({
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
    <TeacherShell title="Kelas Saya" breadcrumb="Dashboard › Kelas">
      <ErrorState
        title="Gagal memuat daftar kelas"
        description="Terjadi masalah saat mengambil data kelas. Coba lagi ya."
        onRetry={reset}
      />
    </TeacherShell>
  );
}
