import { notFound } from "next/navigation";
import { TeacherShell } from "@/components/teacher/TeacherShell";
import { Card, CardHeader } from "@/components/ui/Card";
import { ProgressChart } from "@/components/teacher/ProgressChart";
import { Meter } from "@/components/ui/Meter";
import { StatusText } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/States";
import { COMPETENCY_META, THRESHOLDS } from "@/lib/tokens";
import { getStudent, listStudentAssessments } from "@/lib/api";
import { getServerToken } from "@/lib/api-server";
import { formatDateID } from "@/lib/utils";

export default async function StudentProgressPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const token = await getServerToken();
  // Keduanya hanya butuh `id`, jadi dijalankan bersamaan: 3 putaran → 1 (satu di
  // antaranya dulu dipakai mencari katalog bacaan setelah riwayatnya tiba).
  const [student, assessments] = await Promise.all([
    getStudent(id, token),
    listStudentAssessments(id, token),
  ]);
  if (!student) notFound();

  const labels = assessments.map((_, i) => `A${i + 1}`);

  return (
    <TeacherShell
      title={`${student.name} · Progres`}
      breadcrumb={`Dashboard › ${student.name} › Progres`}
    >
      {assessments.length === 0 ? (
        <EmptyState
          icon="layout-dashboard"
          title="Belum ada data progres"
          description="Tren akan muncul setelah siswa menyelesaikan asesmen pertama."
        />
      ) : (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Tren WCPM"
              description="Penanda Awal/Tengah/Akhir Tahun hanya untuk pemantauan, bukan batas jumlah asesmen."
            />
            <ProgressChart
              points={assessments.map((a) => a.wcpm)}
              labels={labels}
              color="#BD582E"
              milestones={[{ index: 0, label: "Awal" }]}
            />
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader title="Tren Akurasi" />
              <ProgressChart
                points={assessments.map((a) => a.accuracy)}
                labels={labels}
                color="#346841"
                unit="%"
              />
            </Card>
            <Card>
              <CardHeader title="Tren Pemahaman" />
              <ProgressChart
                points={assessments.map((a) =>
                  Math.round(
                    (a.comprehension.retrieve +
                      a.comprehension.interpret +
                      a.comprehension.reflect) /
                      3
                  )
                )}
                labels={labels}
                color="#6B4B82"
                unit="%"
              />
            </Card>
          </div>

          {/* Profil pemahaman asesmen terakhir */}
          <Card>
            <CardHeader title="Pemahaman Asesmen Terakhir" />
            <div className="space-y-4">
              {(["retrieve", "interpret", "reflect"] as const).map((key) => (
                <Meter
                  key={key}
                  label={COMPETENCY_META[key].label}
                  value={assessments[assessments.length - 1].comprehension[key]}
                  color={COMPETENCY_META[key].bar}
                  markers={[THRESHOLDS.comprehension]}
                />
              ))}
            </div>
          </Card>

          {/* Riwayat asesmen */}
          <Card>
            <CardHeader title="Riwayat Asesmen" />
            <div className="overflow-hidden rounded-md border border-paper-200">
              <table className="w-full text-sm">
                <thead className="bg-paper-50 text-left text-xs font-medium text-slate-500">
                  <tr>
                    <th scope="col" className="px-4 py-2 font-semibold">#</th>
                    <th scope="col" className="px-4 py-2 font-semibold">Tanggal</th>
                    <th scope="col" className="px-4 py-2 text-right font-semibold">WCPM</th>
                    <th scope="col" className="px-4 py-2 text-right font-semibold">Akurasi</th>
                    <th scope="col" className="px-4 py-2 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-paper-100">
                  {assessments.map((a, i) => (
                    <tr key={a.id}>
                      <td className="tabular px-4 py-2 text-slate-400">{i + 1}</td>
                      <td className="px-4 py-2 text-slate-600">{formatDateID(a.date)}</td>
                      <td className="tabular px-4 py-2 text-right text-slate-700">
                        {a.wcpm === null ? "–" : a.wcpm}
                      </td>
                      <td className="tabular px-4 py-2 text-right text-slate-700">
                        {a.accuracy === null ? "–" : `${a.accuracy}%`}
                      </td>
                      <td className="px-4 py-2">
                        <StatusText status={a.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </TeacherShell>
  );
}
