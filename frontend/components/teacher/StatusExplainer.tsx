import { THRESHOLDS } from "@/lib/tokens";
import { getThresholds } from "@/lib/api";
import { getServerToken } from "@/lib/api-server";
import { Icon } from "@/components/ui/icons";
import { InfoTip } from "@/components/ui/Tooltip";
import { cn } from "@/lib/utils";

export interface RuleHit {
  rule: string; // kode aturan internal, mis. "BR-01" (hanya tampil di Detail juri)
  text: string; // penjelasan
  passed: boolean;
}

/**
 * StatusExplainer — bagian "Kenapa status ini?".
 * Menegaskan prinsip AI Scores, Rules Decide: keputusan dapat ditelusuri ke aturan.
 *
 * Teks utama memakai **bahasa pengguna** (tanpa kode PRD). Kode aturan (BR-xx)
 * disimpan di blok "Detail untuk juri" yang bisa dibuka-tutup, untuk keperluan
 * penjurian/audit — bukan konsumsi guru harian.
 *
 * Ambang diambil dari backend saat runtime (`GET /config/thresholds`), dengan nilai
 * statis `THRESHOLDS` sebagai fallback bila permintaan gagal. Frontend tetap HANYA
 * presentasi — keputusan tetap di backend.
 */
export async function StatusExplainer({
  rules,
  conclusion,
  className,
}: {
  rules: RuleHit[];
  conclusion: string;
  className?: string;
}) {
  let comprehension: number = THRESHOLDS.comprehension;
  let accLow: number = THRESHOLDS.accuracy.low;
  let accHigh: number = THRESHOLDS.accuracy.high;
  try {
    const token = await getServerToken();
    const t = await getThresholds(token);
    comprehension = t.comprehensionMin;
    accLow = t.accuracyLow;
    accHigh = t.accuracyHigh;
  } catch {
    /* fallback ke nilai statis — presentasi tetap jalan */
  }

  return (
    <div className={cn("rounded-lg border border-paper-200 bg-white p-4", className)}>
      <div className="flex items-center gap-2">
        <h4 className="font-serif text-h3 font-semibold text-slate-800">
          Kenapa status ini?
        </h4>
        <InfoTip
          label="Penjelasan aturan keputusan"
          text="Status ditentukan oleh aturan yang dihitung dari WCPM, Akurasi, Pemahaman, dan hasil sebelumnya — bukan prediksi AI."
        />
      </div>
      <ul className="mt-3 space-y-1.5">
        {rules.map((r) => (
          <li key={r.rule} className="flex items-start gap-2 text-sm">
            <span aria-hidden className={cn("mt-0.5", r.passed ? "text-emerald-600" : "text-amber-600")}>
              <Icon name={r.passed ? "check-circle" : "alert-triangle"} size={16} />
            </span>
            <span className="text-slate-700">{r.text}</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 border-t border-paper-100 pt-3 text-sm font-semibold text-slate-800">
        → {conclusion}
      </p>
      <p className="mt-2 text-xs text-slate-400">
        Ambang pemahaman {comprehension}%, akurasi {accLow}–{accHigh}% (aturan MVP, bukan
        standar nasional).
      </p>

      {/* Jejak aturan untuk juri/demo — tertutup secara default. */}
      <details className="mt-3 border-t border-paper-100 pt-2 text-xs text-slate-500">
        <summary className="cursor-pointer rounded-sm text-slate-500 hover:text-slate-700 focus-visible:outline-none">
          Detail untuk juri
        </summary>
        <ul className="mt-2 space-y-1">
          {rules.map((r) => (
            <li key={r.rule} className="flex items-start gap-2">
              <span
                className={cn(
                  "mt-0.5 shrink-0",
                  r.passed ? "text-emerald-600" : "text-amber-600"
                )}
              >
                <Icon name={r.passed ? "check-circle" : "alert-triangle"} size={13} />
              </span>
              <span>
                <span className="font-semibold text-slate-600">{r.rule}</span> · {r.text}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
