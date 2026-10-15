"use client";

import { useEffect } from "react";
import { TeacherShell } from "@/components/teacher/TeacherShell";
import { ErrorState } from "@/components/ui/States";

/** Error state dashboard — selalu ada tombol Coba Lagi (NFR-03). */
export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log ke konsol untuk debugging; di produksi dapat dikirim ke layanan monitoring.
    console.error(error);
  }, [error]);

  return (
    <TeacherShell title="Dashboard" breadcrumb="Dashboard">
      <ErrorState
        title="Gagal memuat data kelas"
        description="Terjadi masalah saat mengambil data. Periksa koneksi lalu coba lagi."
        onRetry={reset}
      />
    </TeacherShell>
  );
}
