import { TeacherShell } from "@/components/teacher/TeacherShell";
import { AllStudentsTable, type AllStudentRow } from "@/components/teacher/AllStudentsTable";
import { StatusLegend } from "@/components/ui/StatusBadge";
import { formatDateID } from "@/lib/utils";
import { listStudents, listAllAssessments } from "@/lib/api";
import { getServerToken } from "@/lib/api-server";

export default async function StudentsPage() {
  const token = await getServerToken();
  const [students, assessments] = await Promise.all([
    listStudents(token),
    listAllAssessments(token).catch(() => []),
  ]);

  // Kelompokkan asesmen per siswa (urut lama → baru) untuk status & hitungan.
  const byStudent = new Map<string, typeof assessments>();
  for (const a of assessments) {
    const list = byStudent.get(a.studentId) ?? [];
    list.push(a);
    byStudent.set(a.studentId, list);
  }

  const rows: AllStudentRow[] = students
    .sort((a, b) => a.name.localeCompare(b.name, "id"))
    .map((s) => {
      const list = (byStudent.get(s.id) ?? []).sort((a, b) => a.date.localeCompare(b.date));
      const last = list[list.length - 1];
      return {
        id: s.id,
        name: s.name,
        classLabel: s.classLabel,
        assessmentCount: list.length,
        status: last?.status ?? null,
        lastDate: last ? formatDateID(last.date) : null,
      };
    });

  return (
    <TeacherShell title="Siswa" breadcrumb="Dashboard › Siswa">
      <div className="space-y-4">
        <AllStudentsTable students={rows} />
        <StatusLegend />
      </div>
    </TeacherShell>
  );
}
