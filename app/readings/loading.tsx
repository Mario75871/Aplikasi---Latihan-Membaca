import { TeacherShell } from "@/components/teacher/TeacherShell";
import { TableSkeleton } from "@/components/ui/States";

/** Loading skeleton katalog bacaan (tabel ringkas). */
export default function ReadingsLoading() {
  return (
    <TeacherShell title="Bacaan" breadcrumb="Dashboard › Bacaan">
      <TableSkeleton rows={6} />
    </TeacherShell>
  );
}
