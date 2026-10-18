import { TeacherShell } from "@/components/teacher/TeacherShell";
import { Skeleton, TableSkeleton } from "@/components/ui/States";

/** Loading skeleton daftar siswa. */
export default function StudentsLoading() {
  return (
    <TeacherShell title="Siswa" breadcrumb="Dashboard › Siswa">
      <div className="space-y-3">
        <Skeleton className="h-6 w-40" />
        <TableSkeleton rows={8} />
      </div>
    </TeacherShell>
  );
}
