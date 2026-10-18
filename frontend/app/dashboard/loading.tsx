import { TeacherShell } from "@/components/teacher/TeacherShell";
import { Skeleton, TableSkeleton } from "@/components/ui/States";

/** Loading skeleton dashboard — menjaga layout stabil saat data dimuat. */
export default function DashboardLoading() {
  return (
    <TeacherShell title="Dashboard" breadcrumb="Dashboard">
      <div className="space-y-6">
        {/* KPI row */}
        <Skeleton className="h-[68px] w-full" />

        {/* Perlu perhatian hari ini */}
        <div className="rounded-lg border border-paper-200 bg-white p-5">
          <Skeleton className="h-5 w-56" />
          <div className="mt-4 space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        </div>

        {/* Daftar siswa */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-11 w-72" />
          </div>
          <TableSkeleton rows={6} />
        </div>
      </div>
    </TeacherShell>
  );
}
