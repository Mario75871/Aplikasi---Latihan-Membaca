import { TeacherShell } from "@/components/teacher/TeacherShell";
import { ReadingsTable } from "@/components/teacher/ReadingsTable";
import { EmptyState } from "@/components/ui/States";
import { listReadings } from "@/lib/api";
import { getServerToken } from "@/lib/api-server";

export default async function ReadingsPage() {
  const token = await getServerToken();
  const readings = await listReadings(token);

  return (
    <TeacherShell title="Bacaan" breadcrumb="Dashboard › Bacaan">
      {readings.length === 0 ? (
        <EmptyState
          icon="book-open"
          title="Belum ada bacaan"
          description="Bacaan yang tersedia untuk asesmen akan muncul di sini."
        />
      ) : (
        <ReadingsTable readings={readings} />
      )}
    </TeacherShell>
  );
}
