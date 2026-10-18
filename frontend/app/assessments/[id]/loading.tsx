import { TeacherShell } from "@/components/teacher/TeacherShell";
import { Skeleton } from "@/components/ui/States";

/** Loading skeleton hasil asesmen. */
export default function AssessmentDetailLoading() {
  return (
    <TeacherShell title="Hasil Asesmen" breadcrumb="Dashboard › Asesmen › Hasil">
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    </TeacherShell>
  );
}
