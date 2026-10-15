import { THRESHOLDS } from "@/lib/tokens";
import { Icon } from "@/components/ui/icons";
import { InfoTip } from "@/components/ui/Tooltip";
import { cn } from "@/lib/utils";

export interface RuleHit {
  rule: string; // "BR-01"
  text: string; // penjelasan
  passed: boolean;
}

/**
 * StatusExplainer — bagian "Kenapa status ini?" (§38.2).
 * Menegaskan prinsip AI Scores, Rules Decide: keputusan dapat ditelusuri ke aturan.
 * Dipakai untuk juri/demo dan guru yang ingin tahu alasan di balik status.
 */
export function StatusExplainer({
  rules,
  conclusion,
  className,
}: {
  rules: RuleHit[];
  conclusion: string;
  className?: string;
}) {
  return (
    <div className={cn("rounded-lg border border-paper-200 bg-white p-4", className)}>
      <div className="flex items-center gap-2">
        <Icon name="sparkles" size={16} className="text-brand-500" />
        <h4 className="font-serif text-h3 font-semibold text-slate-800">
          Kenapa status ini?
        </h4>
        <InfoTip
          label="Penjelasan aturan keputusan"
          text="Keputusan status berasal dari aturan bisnis (BR-xx) yang dihitung dari WCPM, Akurasi, Pemahaman, dan hasil sebelumnya — bukan prediksi AI."
        />
      </div>
      <ul className="mt-3 space-y-1.5">
        {rules.map((r) => (
          <li key={r.rule} className="flex items-start gap-2 text-sm">
            <span aria-hidden className={cn("mt-0.5", r.passed ? "text-emerald-600" : "text-amber-600")}>
              <Icon name={r.passed ? "check-circle" : "alert-triangle"} size={16} />
            </span>
            <span className="text-slate-700">
              <span className="font-semibold">{r.rule}</span> · {r.text}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 border-t border-paper-100 pt-3 text-sm font-semibold text-slate-800">
        → {conclusion}
      </p>
      <p className="mt-2 text-xs text-slate-400">
        Ambang pemahaman {THRESHOLDS.comprehension}%, akurasi{" "}
        {THRESHOLDS.accuracy.low}–{THRESHOLDS.accuracy.high}% (aturan MVP, bukan standar
        nasional).
      </p>
    </div>
  );
}
