import { TeacherShell } from "@/components/teacher/TeacherShell";
import { Skeleton, CardSkeleton } from "@/components/ui/States";

/** Loading skeleton alur Mulai Asesmen. */
export default function AssessLoading() {
  return (
    <TeacherShell title="Mulai Asesmen" breadcrumb="Dashboard › Asesmen › Mulai">
      <div className="space-y-6">
        <Skeleton className="h-10 w-full max-w-xl" />
        <CardSkeleton count={4} />
      </div>
    </TeacherShell>
  );
}
