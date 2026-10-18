import { TeacherShell } from "@/components/teacher/TeacherShell";
import { AssessmentsTable, type AssessmentRow } from "@/components/teacher/AssessmentsTable";
import { StatusLegend } from "@/components/ui/StatusBadge";
import { listAllAssessments } from "@/lib/api";
import { getServerToken } from "@/lib/api-server";
import { formatDateID } from "@/lib/utils";

export default async function AssessmentsPage() {
  const token = await getServerToken();
  const assessments = await listAllAssessments(token);

  const rows: AssessmentRow[] = assessments.map((a) => ({
    id: a.id,
    date: formatDateID(a.date),
    studentName:
      (a as typeof a & { studentName?: string }).studentName ?? a.studentId,
    readingTitle: a.readingTitle,
    wcpm: a.wcpm,
    accuracy: a.accuracy,
    status: a.status,
  }));

  return (
    <TeacherShell title="Asesmen" breadcrumb="Dashboard › Asesmen">
      <div className="space-y-4">
        <AssessmentsTable rows={rows} />
        <StatusLegend />
      </div>
    </TeacherShell>
  );
}
