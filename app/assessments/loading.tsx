import { TeacherShell } from "@/components/teacher/TeacherShell";
import { Skeleton, TableSkeleton } from "@/components/ui/States";

/** Loading skeleton riwayat asesmen. */
export default function AssessmentsLoading() {
  return (
    <TeacherShell title="Asesmen" breadcrumb="Dashboard › Asesmen">
      <div className="space-y-3">
        <Skeleton className="h-6 w-40" />
        <TableSkeleton rows={6} />
      </div>
    </TeacherShell>
  );
}
