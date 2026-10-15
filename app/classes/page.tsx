import Link from "next/link";
import { TeacherShell } from "@/components/teacher/TeacherShell";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { StatusLegend } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/States";
import { STATUS_META, UNASSESSED_META } from "@/lib/tokens";
import { listClasses, getClassDashboard } from "@/lib/api";
import { getServerToken } from "@/lib/api-server";
import { cn, formatDateID } from "@/lib/utils";

/** Halaman daftar kelas (F-02). Ringkasan dihitung dari dashboard tiap kelas. */
export default async function ClassesPage() {
  const token = await getServerToken();
  const classes = await listClasses(token);

  const dashboards = await Promise.all(
    classes.map((c) => getClassDashboard(c.id, token).catch(() => null))
  );

  const summaries = classes.map((c, i) => {
    const d = dashboards[i];
    const students = d?.students ?? [];
    const lastDates = students
      .flatMap((s) => s.trend.map((t) => t.date))
      .sort();
    return {
      cls: c,
      total: d?.totalStudents ?? 0,
      intervene: students.filter((s) => s.status === "INTERVENE").length,
      unassessed: students.filter((s) => s.status === null).length,
      lastActivity: lastDates[lastDates.length - 1],
    };
  });

  return (
    <TeacherShell
      title="Kelas Saya"
      breadcrumb="Dashboard › Kelas"
      actions={
        <Button variant="primary" size="md">
          <Icon name="plus" size={18} />
          <span className="hidden sm:inline">Buat Kelas</span>
        </Button>
      }
    >
      {classes.length === 0 ? (
        <EmptyState
          icon="school"
          title="Belum ada kelas"
          description="Buat kelas pertama untuk mulai menambahkan siswa dan melakukan asesmen."
          action={
            <Button variant="primary" size="md">
              <Icon name="plus" size={18} />
              Buat Kelas
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {summaries.map(({ cls, total, intervene, unassessed, lastActivity }) => (
            <div
              key={cls.id}
              className="flex flex-col rounded-lg border border-paper-200 bg-white p-5 transition-colors hover:border-brand-300"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-serif text-h3 font-semibold text-slate-900">
                    {cls.name}
                  </h3>
                  <p className="mt-0.5 text-sm text-slate-500">
                    Tingkat {cls.grade} · {total} siswa
                  </p>
                </div>
                <Link href={`/dashboard?class=${cls.id}`} className="shrink-0">
                  <Button variant="secondary" size="sm">
                    Buka
                    <Icon name="arrow-right" size={16} />
                  </Button>
                </Link>
              </div>

              {/* Dua hitungan dipisah — tidak dijumlahkan. */}
              <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
                <span className="inline-flex items-center gap-2 text-slate-700">
                  <span
                    aria-hidden
                    className={cn("inline-block h-2.5 w-2.5 rounded-full", STATUS_META.INTERVENE.dot)}
                  />
                  <span className="tabular font-semibold">{intervene}</span>
                  <span className="text-slate-500">perlu intervensi</span>
                </span>
                <span className="inline-flex items-center gap-2 text-slate-700">
                  <span
                    aria-hidden
                    className={cn("inline-block h-2.5 w-2.5 rounded-full", UNASSESSED_META.dot)}
                  />
                  <span className="tabular font-semibold">{unassessed}</span>
                  <span className="text-slate-500">belum diases</span>
                </span>
              </div>

              <p className="mt-3 border-t border-paper-100 pt-3 text-sm text-slate-500">
                {lastActivity
                  ? `Asesmen terakhir: ${formatDateID(lastActivity)}`
                  : "Belum ada aktivitas asesmen"}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Satu legenda status untuk halaman (kosakata sama dengan dashboard). */}
      <StatusLegend className="mt-6" />
    </TeacherShell>
  );
}
