import { Icon } from "@/components/ui/icons";
import { InfoTip } from "@/components/ui/Tooltip";
import { cn } from "@/lib/utils";
import type { WordScoreView } from "@/lib/types";

/**
 * Label Bahasa Indonesia untuk kode `review_reasons` dari framework.
 * Ini adalah sinyal "perlu diperiksa", BUKAN vonis kesalahan membaca.
 * Tidak ada klasifikasi jenis kesalahan.
 */
const REVIEW_REASON_LABEL: Record<string, string> = {
  low_model_probability: "Keyakinan model rendah",
  reference_transcript_mismatch: "Teks vs transkrip berbeda",
  missing_word_timestamp: "Stempel waktu kata hilang",
  invalid_word_timestamp: "Stempel waktu kata tidak wajar",
  zero_duration_word: "Durasi kata nol",
  suspicious_segment_metadata: "Metadata segmen mencurigakan",
  asr_processing_warning: "Peringatan proses ASR",
  alignment_ambiguous: "Penjajaran ambigu",
  watermark_suspected: "Dugaan watermark audio",
  manual_review_requested: "Diminta diperiksa manual",
  probability_unavailable: "Keyakinan model tidak tersedia",
};

function reviewLabel(code: string): string {
  return REVIEW_REASON_LABEL[code] ?? code;
}

/**
 * WordTracePanel — telusur keputusan tiap kata.
 *
 * Menampilkan keputusan tiap kata (Benar / Perlu latihan) dan kata yang DITANDAI
 * perlu diperiksa. Angka WCPM/Akurasi bisa ditelusuri ke input-nya.
 *
 * Batasan penting:
 * - Ini "penilaian otomatis (estimasi)" — bukan bukti pelafalan benar/salah.
 * - TIDAK menampilkan jenis kesalahan (mis. substitusi/mispronunciation) di UI.
 */
export function WordTracePanel({ words }: { words: WordScoreView[] }) {
  const flaggedCount = words.filter((w) => w.reviewReasons.length > 0).length;

  return (
    <div className="overflow-hidden rounded-lg border border-paper-200 bg-white">
      <div className="flex items-start justify-between gap-2 border-b border-paper-100 px-4 py-3">
        <div>
          <h4 className="font-serif text-h3 font-semibold text-slate-800">Kata per Kata</h4>
          <p className="mt-0.5 text-xs text-slate-500">
            Penilaian otomatis (estimasi) tiap kata, dihitung dari skor keyakinan model
            terhadap bacaan. Bukan bukti pelafalan benar/salah.
          </p>
        </div>
        <InfoTip
          label="Aturan penilaian kata"
          text="Kata dianggap Benar bila keyakinan model di atas 0,5; di bawah itu Perlu latihan. Nama diri tetap dianggap Benar. Kata yang ditandai perlu diperiksa tetap ditampilkan, tanpa menyimpulkan jenis kesalahan."
        />
      </div>

      {words.length === 0 ? (
        <p className="px-4 py-8 text-center text-sm text-slate-500">
          Rincian kata tidak tersedia untuk asesmen ini.
        </p>
      ) : (
        <>
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-paper-50 text-left text-xs font-medium text-slate-500">
                <tr>
                  <th scope="col" className="px-4 py-2 font-semibold">#</th>
                  <th scope="col" className="px-4 py-2 font-semibold">Kata</th>
                  <th scope="col" className="px-4 py-2 text-right font-semibold">Keyakinan</th>
                  <th scope="col" className="px-4 py-2 font-semibold">Keputusan</th>
                  <th scope="col" className="px-4 py-2 font-semibold">Catatan</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-100">
                {words.map((w) => {
                  const correct = w.isCorrect;
                  const flagged = w.reviewReasons.length > 0;
                  return (
                    <tr key={w.position} className={flagged ? "bg-amber-50/40" : undefined}>
                      <td className="tabular px-4 py-2 text-slate-400">{w.position}</td>
                      <td className="px-4 py-2 font-medium text-slate-800">
                        {w.word}
                        {w.isProperNoun && (
                          <span className="ml-1.5 text-xs font-normal text-slate-400">(nama diri)</span>
                        )}
                      </td>
                      <td className="tabular px-4 py-2 text-right text-slate-600">
                        {w.confidence === null ? "—" : w.confidence.toFixed(2)}
                      </td>
                      <td className="px-4 py-2">
                        {!w.attempted ? (
                          <span className="inline-flex items-center gap-1.5 font-semibold text-slate-400">
                            <Icon name="circle-dashed" size={15} />
                            Terlewat
                          </span>
                        ) : (
                          <span
                            className={cn(
                              "inline-flex items-center gap-1.5 font-semibold",
                              correct ? "text-emerald-600" : "text-amber-600"
                            )}
                          >
                            <Icon name={correct ? "check-circle" : "alert-triangle"} size={15} />
                            {correct ? "Benar" : "Perlu latihan"}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-xs text-slate-500">
                        {flagged ? (
                          <span className="inline-flex items-center gap-1 text-amber-700">
                            <Icon name="shield-alert" size={13} />
                            Perlu diperiksa:{" "}
                            {w.reviewReasons.map(reviewLabel).join(", ")}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {flaggedCount > 0 && (
            <p className="border-t border-paper-100 bg-paper-50 px-4 py-2 text-xs text-slate-500">
              {flaggedCount} kata ditandai <strong>perlu diperiksa</strong> (sinyal, bukan
              vonis). Tidak ada klasifikasi jenis kesalahan pada tampilan ini.
            </p>
          )}
        </>
      )}
    </div>
  );
}
