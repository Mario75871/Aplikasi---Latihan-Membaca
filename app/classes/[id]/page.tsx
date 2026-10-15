import Link from "next/link";
import { notFound } from "next/navigation";
import { TeacherShell } from "@/components/teacher/TeacherShell";
import { ClassStudentTable, type ClassStudentRow } from "@/components/teacher/ClassStudentTable";
import { StatusLegend } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { formatDateID } from "@/lib/utils";
import { getClass, getClassDashboard, listAllAssessments } from "@/lib/api";
import { getServerToken } from "@/lib/api-server";

export default async function ClassDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const token = await getServerToken();

  const cls = await getClass(id, token);
  if (!cls) notFound();

  const [dashboard, assessments] = await Promise.all([
    getClassDashboard(id, token).catch(() => null),
    listAllAssessments(token).catch(() => []),
  ]);

  const countByStudent = new Map<string, number>();
  for (const a of assessments) {
    countByStudent.set(a.studentId, (countByStudent.get(a.studentId) ?? 0) + 1);
  }

  const students = dashboard?.students ?? [];
  const rows: ClassStudentRow[] = students.map((s) => {
    const trend = [...s.trend].sort((a, b) => a.date.localeCompare(b.date));
    const lastDate = trend[trend.length - 1]?.date;
    return {
      id: s.studentId,
      name: s.name,
      grade: s.grade,
      assessmentCount: countByStudent.get(s.studentId) ?? 0,
      status: s.status,
      lastDate: lastDate ? formatDateID(lastDate) : null,
    };
  });

  return (
    <TeacherShell
      title={cls.name}
      breadcrumb={`Dashboard › Kelas › ${cls.name}`}
      actions={
        <Link href={`/assess?class=${cls.id}`}>
          <Button variant="primary" size="md">
            <Icon name="mic" size={18} />
            <span className="hidden sm:inline">Mulai Asesmen</span>
            <span className="sm:hidden">Asesmen</span>
          </Button>
        </Link>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-slate-500">
            {cls.name} · <span className="font-semibold text-slate-700">{students.length}</span> siswa
          </p>
          <Button variant="secondary" size="md">
            <Icon name="plus" size={18} />
            Tambah Siswa
          </Button>
        </div>

        <ClassStudentTable students={rows} />

        <StatusLegend />
      </div>
    </TeacherShell>
  );
}
