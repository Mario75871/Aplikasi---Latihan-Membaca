import Link from "next/link";
import { notFound } from "next/navigation";
import { TeacherShell } from "@/components/teacher/TeacherShell";
import { StatTile } from "@/components/ui/StatTile";
import { Meter } from "@/components/ui/Meter";
import { StatusText } from "@/components/ui/StatusBadge";
import { DisclaimerBanner } from "@/components/ui/DisclaimerBanner";
import { ProgressChart } from "@/components/teacher/ProgressChart";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { InfoTip } from "@/components/ui/Tooltip";
import { EmptyState } from "@/components/ui/States";
import { averageComprehension, COMPETENCY_META, THRESHOLDS } from "@/lib/tokens";
import { getStudent, listStudentAssessments } from "@/lib/api";
import { getServerToken } from "@/lib/api-server";
import { formatDateID } from "@/lib/utils";

export default async function StudentProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const token = await getServerToken();

  const student = await getStudent(id, token);
  if (!student) notFound();

  const assessments = await listStudentAssessments(id, token);
  const last = assessments[assessments.length - 1];
  const prev = assessments[assessments.length - 2];

  const avgComprehension = last ? averageComprehension(last.comprehension) : 0;
  const wcpmDelta =
    last && prev && last.wcpm !== null && prev.wcpm !== null
      ? last.wcpm - prev.wcpm
      : undefined;

  return (
    <TeacherShell
      title={student.name}
      breadcrumb={`Dashboard › ${student.classLabel} › ${student.name}`}
      actions={
        <Link href={`/assess?student=${student.id}`}>
          <Button variant="primary" size="md">
            <Icon name="mic" size={18} />
            <span className="hidden sm:inline">Mulai Asesmen</span>
            <span className="sm:hidden">Asesmen</span>
          </Button>
        </Link>
      }
    >
      <div className="space-y-6">
        {/* Identitas siswa */}
        <div className="flex items-center gap-4 rounded-lg border border-paper-200 bg-white p-5">
          <span className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-100 text-lg font-bold text-brand-700">
            {student.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}
          </span>
          <div>
            <h2 className="font-serif text-h3 font-semibold text-slate-900">{student.name}</h2>
            <p className="text-sm text-slate-500">
              {student.classLabel} · Tingkat {student.grade} · {assessments.length} asesmen
            </p>
          </div>
        </div>

        {!last ? (
          <EmptyState
            icon="mic"
            title="Belum ada asesmen"
            description="Siswa ini belum pernah diases. Mulai asesmen pertama untuk melihat hasil dan rekomendasi."
            action={
              <Link href={`/assess?student=${student.id}`}>
                <Button variant="primary" size="md">
                  <Icon name="mic" size={18} />
                  Mulai Asesmen
                </Button>
              </Link>
            }
          />
        ) : (
          <>
            {/* Metrik terbaru */}
            <section>
              <h2 className="mb-3 font-serif text-h3 font-semibold text-slate-800">
                Hasil Terbaru · {formatDateID(last.date)}
              </h2>
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                <StatTile
                  label="WCPM"
                  value={last.wcpm ?? 0}
                  empty={last.wcpm === null}
                  hint="Kata benar per menit"
                  delta={
                    wcpmDelta !== undefined
                      ? { value: wcpmDelta, direction: wcpmDelta >= 0 ? "up" : "down" }
                      : undefined
                  }
                />
                <StatTile
                  label="Akurasi"
                  value={last.accuracy ?? 0}
                  empty={last.accuracy === null}
                  unit="%"
                />
                <StatTile label="Pemahaman" value={avgComprehension} unit="%" />
                <div className="rounded-lg border border-paper-200 bg-white p-4">
                  <p className="text-xs font-medium text-slate-500">Status</p>
                  <div className="mt-2">
                    <StatusText status={last.status} />
                  </div>
                </div>
              </div>
            </section>

            {/* Rekomendasi */}
            <Card>
              <CardHeader title="Rekomendasi" />
              <p className="text-sm text-slate-700">{last.recommendation}</p>
              <p className="mt-2 text-xs text-slate-500">
                Bacaan berikutnya disarankan: Level {last.nextReadingLevel}
              </p>
            </Card>

            {/* Profil literasi */}
            <Card>
              <CardHeader title="Profil Pemahaman" />
              <div className="space-y-4">
                {(["retrieve", "interpret", "reflect"] as const).map((key) => (
                  <div key={key}>
                    <div className="mb-1 flex items-center gap-1.5">
                      <span className="text-sm font-semibold text-slate-700">
                        {COMPETENCY_META[key].label}
                      </span>
                      <InfoTip
                        label={`Arti ${COMPETENCY_META[key].label}`}
                        text={COMPETENCY_META[key].description}
                      />
                    </div>
                    <Meter
                      value={last.comprehension[key]}
                      color={COMPETENCY_META[key].bar}
                      markers={[THRESHOLDS.comprehension]}
                    />
                  </div>
                ))}
              </div>
            </Card>

            {/* Tren */}
            <Card>
              <CardHeader
                title="Tren WCPM"
                action={
                  <Link
                    href={`/students/${student.id}/progress`}
                    className="text-sm font-semibold text-brand-600 hover:underline"
                  >
                    Lihat Progres →
                  </Link>
                }
              />
              <ProgressChart
                points={assessments.map((a) => a.wcpm)}
                labels={assessments.map((_, i) => `A${i + 1}`)}
                color="#BD582E"
              />
            </Card>

            <DisclaimerBanner kind="hasbrouck" />
          </>
        )}
      </div>
    </TeacherShell>
  );
}
