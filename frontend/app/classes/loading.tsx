import { TeacherShell } from "@/components/teacher/TeacherShell";
import { Skeleton } from "@/components/ui/States";

/** Loading skeleton daftar kelas. */
export default function ClassesLoading() {
  return (
    <TeacherShell title="Kelas Saya" breadcrumb="Dashboard › Kelas">
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-paper-200 bg-white p-5">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="mt-2 h-4 w-40" />
            <Skeleton className="mt-4 h-4 w-56" />
          </div>
        ))}
      </div>
    </TeacherShell>
  );
}
