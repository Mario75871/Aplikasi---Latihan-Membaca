import { TeacherShell } from "@/components/teacher/TeacherShell";
import { Skeleton } from "@/components/ui/States";

/** Loading skeleton profil siswa. */
export default function StudentProfileLoading() {
  return (
    <TeacherShell title="Siswa" breadcrumb="Dashboard › Siswa">
      <div className="space-y-6">
        <Skeleton className="h-24 w-full" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-40 w-full" />
      </div>
    </TeacherShell>
  );
}
