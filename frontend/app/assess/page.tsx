import { TeacherShell } from "@/components/teacher/TeacherShell";
import { AssessWizard } from "@/components/teacher/AssessWizard";
import type { PickableStudent } from "@/components/teacher/StudentPicker";
import {
  listStudents,
  listReadings,
  listAllAssessments,
} from "@/lib/api";
import { getServerToken } from "@/lib/api-server";
import { studentProgression, type StudentProgression } from "@/lib/progression";
import type { AdaptiveStatus } from "@/lib/tokens";

/**
 * Halaman "Mulai Asesmen" (T-08). Data siswa & bacaan diambil dari backend.
 * Level bacaan yang disarankan dihitung server dari riwayat asesmen terakhir.
 *
 * Level terbuka per siswa juga dihitung di sini dari data yang sudah ada —
 * `listAllAssessments` hanya mengembalikan sesi yang sudah tuntas, jadi tidak
 * ada permintaan API tambahan (lihat lib/progression.ts).
 */
export default async function StartAssessmentPage({
  searchParams,
}: {
  searchParams: Promise<{ student?: string; class?: string; reading?: string }>;
}) {
  const { student: studentId, reading: readingId } = await searchParams;
  const token = await getServerToken();

  const [students, readings, assessments] = await Promise.all([
    listStudents(token),
    listReadings(token),
    listAllAssessments(token).catch(() => []),
  ]);

  // Status & level bacaan berikutnya dari asesmen terbaru tiap siswa.
  const latest = new Map<string, (typeof assessments)[number]>();
  for (const a of assessments) {
    const prev = latest.get(a.studentId);
    if (!prev || a.date > prev.date) latest.set(a.studentId, a);
  }

  const pickable: PickableStudent[] = students
    .sort((a, b) => a.name.localeCompare(b.name, "id"))
    .map((s) => ({
      id: s.id,
      name: s.name,
      classLabel: s.classLabel,
      grade: s.grade,
      status: (latest.get(s.id)?.status ?? null) as AdaptiveStatus | null,
    }));

  // Level terbuka (gerbang naik level) + level yang disarankan, per siswa.
  // Tangga mulai Level 1 untuk semua siswa — tingkat kelas tidak dipakai lagi
  // sebagai tebakan awal, karena bacaan di atas level terbuka memang terkunci.
  const progressionByStudent: Record<string, StudentProgression> = {};
  const recommendedLevels: Record<string, 1 | 2 | 3> = {};
  for (const s of students) {
    const progression = studentProgression(readings, assessments, s.id);
    progressionByStudent[s.id] = progression;
    // Saran Adaptive Engine dibatasi gerbang: jangan pernah menyorot level yang
    // terkunci, karena wizard akan menolak pilihannya sendiri.
    const suggested = latest.get(s.id)?.nextReadingLevel ?? progression.unlockedLevel;
    recommendedLevels[s.id] =
      suggested <= progression.unlockedLevel ? suggested : progression.unlockedLevel;
  }

  const initialReadingId = readings.some((r) => r.id === readingId)
    ? readingId
    : undefined;

  return (
    <TeacherShell title="Mulai Asesmen" breadcrumb="Dashboard › Asesmen › Mulai">
      <AssessWizard
        students={pickable}
        readings={readings}
        initialStudentId={studentId}
        initialReadingId={initialReadingId}
        recommendedLevels={recommendedLevels}
        progressionByStudent={progressionByStudent}
      />
    </TeacherShell>
  );
}
