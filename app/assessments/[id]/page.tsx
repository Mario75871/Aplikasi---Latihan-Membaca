import Link from "next/link";
import { notFound } from "next/navigation";
import { TeacherShell } from "@/components/teacher/TeacherShell";
import { StatusText } from "@/components/ui/StatusBadge";
import { StatusExplainer } from "@/components/teacher/StatusExplainer";
import { WordTracePanel } from "@/components/teacher/WordTracePanel";
import { StatTile } from "@/components/ui/StatTile";
import { Meter } from "@/components/ui/Meter";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { DisclaimerBanner } from "@/components/ui/DisclaimerBanner";
import { Icon } from "@/components/ui/icons";
import { InfoTip } from "@/components/ui/Tooltip";
import { AudioPlayer } from "@/components/teacher/AudioPlayer";
import { averageComprehension, COMPETENCY_META, THRESHOLDS } from "@/lib/tokens";
import { getAssessment, getStudent, getHasbrouckReference, getAssessmentAudioUrl } from "@/lib/api";
import { getServerToken } from "@/lib/api-server";
import { formatDateID } from "@/lib/utils";

export default async function AssessmentResultPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const token = await getServerToken();

  const asmt = await getAssessment(id, token);
  if (!asmt) notFound();

  const student = await getStudent(asmt.studentId, token);
  const avgComprehension = averageComprehension(asmt.comprehension);

  // Rekaman siswa: signed URL berumur pendek (null bila tak tersedia).
  const audioUrl = await getAssessmentAudioUrl(id, token);

  // Referensi Hasbrouck–Tindal dari backend (musim dihitung server bila kosong).
  // WCPM null (tak dapat dihitung) → tidak ada posisi referensi.
  const hasbrouck =
    asmt.wcpm === null
      ? null
      : await getHasbrouckReference(
          student?.grade ?? 2,
          asmt.season ?? "",
          asmt.wcpm,
          token
        ).catch(() => null);

  return (
    <TeacherShell
      title={`${student?.name ?? "Siswa"} › Hasil Asesmen`}
      breadcrumb={`Dashboard › ${student?.classLabel ?? ""} › ${student?.name ?? ""} › Hasil`}
      actions={
        <Link href={`/students/${asmt.studentId}/progress`}>
          <Button variant="secondary" size="md">
            <Icon name="layout-dashboard" size={18} />
            <span className="hidden sm:inline">Lihat Progres</span>
            <span className="sm:hidden">Progres</span>
          </Button>
        </Link>
      }
    >
      <div className="space-y-8">
        {/* Mode demo — tandai jelas bila hasil berasal dari replay, bukan model nyata. */}
        {asmt.isDemoFallback && (
          <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            <Icon name="shield-alert" size={16} className="mt-0.5 shrink-0" />
            <span>
              <strong>Mode demo.</strong> Hasil ini berasal dari pemutaran ulang data contoh,
              bukan dari model pengenalan suara sebenarnya. Angka tidak mewakili performa siswa.
            </span>
          </div>
        )}

        {/* Ringkasan — konteks + metrik, satu blok padat. */}
        <section className="space-y-4">
          <p className="text-sm text-slate-500">
            {formatDateID(asmt.date)} · Bacaan:{" "}
            <span className="font-medium text-slate-700">{asmt.readingTitle}</span>
          </p>

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatTile label="WCPM" value={asmt.wcpm ?? 0} empty={asmt.wcpm === null} hint="Kata benar per menit" />
            <StatTile label="Akurasi" value={asmt.accuracy ?? 0} empty={asmt.accuracy === null} unit="%" />
            <StatTile label="Pemahaman" value={avgComprehension} unit="%" />
            <div className="rounded-lg border border-paper-200 bg-white p-4">
              <div className="flex items-center gap-1.5">
                <p className="text-xs font-medium text-slate-500">Status</p>
                <InfoTip
                  label="Arti status"
                  text="Status adalah keputusan sistem berdasarkan aturan yang transparan, bukan penilaian guru. Lihat bagian 'Kenapa status ini?' di bawah."
                />
              </div>
              <div className="mt-2">
                <StatusText status={asmt.status} />
              </div>
            </div>
          </div>
        </section>

        {/* Kenapa status ini? */}
        <StatusExplainer rules={asmt.rulesFired} conclusion={asmt.recommendation} />

        {/* Pemahaman + kelancaran — seksi hairline, bukan kartu bertumpuk. */}
        <section className="rounded-lg border border-paper-200 bg-white">
          <div className="border-b border-paper-100 p-5">
            <CardHeader title="Pemahaman Bacaan" className="mb-0" />
            <div className="mt-4 space-y-4">
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
                    value={asmt.comprehension[key]}
                    color={COMPETENCY_META[key].bar}
                    markers={[THRESHOLDS.comprehension]}
                  />
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-slate-400">
              Garis penanda pada 80% adalah ambang aturan MVP, bukan standar nasional.
            </p>
          </div>

          <div className="p-5">
            <h3 className="font-serif text-h3 font-semibold text-slate-800">
              Rincian Kelancaran Membaca
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Penilaian otomatis (estimasi) — bukan bukti pelafalan benar/salah.
            </p>
            <div className="tabular mt-4 flex flex-wrap gap-x-8 gap-y-3 text-sm text-slate-600">
              <span>
                Kata benar: <strong className="text-emerald-600">{asmt.correctWords}</strong>
              </span>
              <span>
                Kata perlu latihan:{" "}
                <strong className="text-amber-600">{asmt.incorrectWords}</strong>
              </span>
              <span>
                Total kata dicoba: <strong className="text-slate-800">{asmt.totalWordsRead}</strong>
              </span>
              <span>
                Waktu baca: <strong className="text-slate-800">{asmt.readingTimeSec} detik</strong>
              </span>
            </div>
          </div>
        </section>

        {/* Rekaman siswa + transkrip — guru dapat mendengar & membandingkan dengan
            transkripsi kata per kata. Presentasi saja. */}
        <Card>
          <CardHeader
            title="Rekaman Bacaan Siswa"
            description="Dengarkan rekaman asli untuk membandingkan dengan transkripsi di bawah."
          />
          <AudioPlayer url={audioUrl} />
          {asmt.transcript ? (
            <details className="mt-4">
              <summary className="cursor-pointer text-sm font-medium text-slate-700">
                Lihat transkripsi otomatis
              </summary>
              <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">
                {asmt.transcript}
              </p>
            </details>
          ) : (
            <p className="mt-4 text-sm text-slate-400">Transkripsi tidak tersedia.</p>
          )}
        </Card>

        {/* Kata per kata — dengan tanda "perlu diperiksa", tanpa jenis kesalahan. */}
        <WordTracePanel words={asmt.wordScores} />

        {/* Hasbrouck */}
        <Card>
          <CardHeader
            title="Perbandingan Kelancaran (Referensi)"
            description="Pembanding eksternal untuk konteks, bukan penentu keputusan."
          />
          {hasbrouck?.available ? (
            <>
              <p className="tabular text-sm text-slate-700">
                WCPM {hasbrouck.wcpm} · Kelas {hasbrouck.grade}
              </p>
              <p className="tabular mt-1 text-sm text-slate-500">
                P25 ── {hasbrouck.p25} &nbsp;&nbsp; P50 ── {hasbrouck.p50}
              </p>
              <p className="mt-2 text-sm font-semibold text-slate-700">
                Posisi: {hasbrouck.position}
              </p>
            </>
          ) : (
            <p className="text-sm text-slate-500">
              {hasbrouck?.reason ?? "Referensi tidak tersedia untuk kombinasi ini."}
            </p>
          )}
          <div className="mt-3">
            <DisclaimerBanner kind="hasbrouck" />
          </div>
        </Card>

        {/* Rekomendasi & langkah berikutnya */}
        <Card>
          <CardHeader title="Rekomendasi & Langkah Berikutnya" />
          <p className="text-sm text-slate-700">{asmt.recommendation}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href={`/assess?student=${asmt.studentId}`}>
              <Button variant="primary" size="md">
                <Icon name="book-open" size={18} />
                Pilih Bacaan Berikutnya
              </Button>
            </Link>
            <Link href={`/students/${asmt.studentId}/progress`}>
              <Button variant="secondary" size="md">
                Lihat Progres
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    </TeacherShell>
  );
}
