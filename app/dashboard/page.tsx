import Link from "next/link";
import { TeacherShell } from "@/components/teacher/TeacherShell";
import { ClassSwitcher } from "@/components/teacher/ClassSwitcher";
import { DashboardStudents, type StudentRowWithStatus } from "@/components/teacher/DashboardStudents";
import { DisclaimerBanner } from "@/components/ui/DisclaimerBanner";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { EmptyState } from "@/components/ui/States";
import { averageComprehension } from "@/lib/tokens";
import { listClasses, getClassDashboard } from "@/lib/api";
import { getServerToken } from "@/lib/api-server";

/**
 * F-10 Teacher Dashboard. Data dari GET /dashboard/class/{id}.
 * Status yang ditampilkan adalah keputusan Adaptive Engine (adaptive_status),
 * konsisten dengan kosakata status di seluruh UI (design-system).
 */
export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ class?: string }>;
}) {
  const { class: classParam } = await searchParams;
  const token = await getServerToken();

  const classes = await listClasses(token);
  const activeClassId =
    classes.find((c) => c.id === classParam)?.id ?? classes[0]?.id ?? "";

  // Ringkasan semua kelas untuk pemilih kelas (jumlah siswa).
  const dashboards = await Promise.all(
    classes.map((c) => getClassDashboard(c.id, token).catch(() => null))
  );
  const dashboardById = new Map(
    dashboards.filter((d): d is NonNullable<typeof d> => Boolean(d)).map((d) => [d.classId, d])
  );
  const dashboard = dashboardById.get(activeClassId) ?? null;

  const classOptions = classes.map((c) => ({
    id: c.id,
    name: c.name,
    studentCount: dashboardById.get(c.id)?.totalStudents ?? 0,
  }));

  if (!dashboard) {
    return (
      <TeacherShell title="Dashboard" breadcrumb="Dashboard">
        <EmptyState
          icon="school"
          title="Belum ada kelas"
          description="Buat kelas terlebih dahulu untuk mulai melakukan asesmen."
          action={
            <Link href="/classes">
              <Button variant="primary" size="md">
                <Icon name="plus" size={18} />
                Kelola Kelas
              </Button>
            </Link>
          }
        />
      </TeacherShell>
    );
  }

  // Baris tabel: status engine dari adaptive_status; siswa tanpa asesmen → null.
  const rows: StudentRowWithStatus[] = dashboard.students.map((s) => ({
    id: s.studentId,
    name: s.name,
    classLabel: dashboard.className,
    display: s.status ?? "UNASSESSED",
    status: s.status,
    wcpm: s.wcpm,
    accuracy: s.accuracy,
    comprehension: s.comprehension ? averageComprehension(s.comprehension) : null,
    recommendation: s.recommendation || "Belum ada asesmen. Mulai asesmen untuk melihat hasil.",
  }));

  const counts = {
    total: dashboard.totalStudents,
    unassessed: rows.filter((r) => r.status === null).length,
    intervene: rows.filter((r) => r.status === "INTERVENE").length,
    stay: rows.filter((r) => r.status === "STAY").length,
    candidate: rows.filter((r) => r.status === "PROMOTION_CANDIDATE").length,
    promote: rows.filter((r) => r.status === "PROMOTE").length,
  };
  const assessed = counts.total - counts.unassessed;

  return (
    <TeacherShell
      title={dashboard.className}
      breadcrumb="Dashboard"
      actions={
        <Link href={`/assess?class=${dashboard.classId}`}>
          <Button variant="primary" size="md">
            <Icon name="plus" size={18} />
            <span className="hidden sm:inline">Mulai Asesmen</span>
            <span className="sm:hidden">Asesmen</span>
          </Button>
        </Link>
      }
      toolbar={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <ClassSwitcher classes={classOptions} activeClassId={dashboard.classId} />
          <p className="text-sm text-slate-500">
            <span className="font-semibold text-slate-700">{assessed}</span> dari{" "}
            <span className="font-semibold text-slate-700">{counts.total}</span> siswa sudah
            diases
          </p>
        </div>
      }
    >
      <div className="space-y-8">
        {dashboard.students.length === 0 ? (
          <EmptyState
            icon="inbox"
            title="Belum ada siswa di kelas ini"
            description="Tambahkan siswa terlebih dahulu untuk mulai melakukan asesmen."
            action={
              <Link href={`/classes/${dashboard.classId}`}>
                <Button variant="primary" size="md">
                  <Icon name="plus" size={18} />
                  Tambah Siswa
                </Button>
              </Link>
            }
          />
        ) : (
          <DashboardStudents rows={rows} counts={counts} />
        )}

        <DisclaimerBanner kind="threshold" />
      </div>
    </TeacherShell>
  );
}
