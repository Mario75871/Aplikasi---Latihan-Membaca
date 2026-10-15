import { TeacherShell } from "@/components/teacher/TeacherShell";
import { Skeleton } from "@/components/ui/States";

/** Loading skeleton halaman progres siswa. */
export default function StudentProgressLoading() {
  return (
    <TeacherShell title="Progres" breadcrumb="Dashboard › Siswa › Progres">
      <div className="space-y-6">
        <Skeleton className="h-52 w-full" />
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-52 w-full" />
          <Skeleton className="h-52 w-full" />
        </div>
      </div>
    </TeacherShell>
  );
}
