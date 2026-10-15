import { TeacherShell } from "@/components/teacher/TeacherShell";
import { Skeleton, CardSkeleton } from "@/components/ui/States";

/** Loading skeleton detail kelas. */
export default function ClassDetailLoading() {
  return (
    <TeacherShell title="Kelas" breadcrumb="Dashboard › Kelas">
      <div className="space-y-4">
        <Skeleton className="h-6 w-48" />
        <CardSkeleton count={2} />
      </div>
    </TeacherShell>
  );
}
