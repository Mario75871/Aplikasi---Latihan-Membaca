import { cn } from "@/lib/utils";

/**
 * Meter — bar progres dengan penanda ambang batas (threshold marker).
 * Dipakai untuk pemahaman (marker 80%) dan akurasi (marker 90/95%).
 *
 * Nilai selalu ditampilkan (tabular) agar tidak bergantung pada warna saja
 * (aksesibilitas). `label` opsional untuk teks di kiri.
 */
export function Meter({
  value,
  max = 100,
  color = "bg-brand-500",
  markers = [],
  label,
  showValue = true,
  className,
}: {
  value: number;
  max?: number;
  color?: string;
  markers?: number[];
  label?: string;
  showValue?: boolean;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));

  return (
    <div className={cn("w-full", className)}>
      {(label || showValue) && (
        <div className="mb-1 flex justify-between text-xs font-medium text-slate-500">
          <span>{label}</span>
          {showValue && (
            <span className="tabular font-semibold text-slate-700">
              {Math.round(value)}%
            </span>
          )}
        </div>
      )}
      <div
        className="relative h-2.5 w-full overflow-hidden rounded-full bg-slate-100"
        role="progressbar"
        aria-valuenow={Math.round(value)}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label}
      >
        <div
          className={cn("h-full rounded-full transition-[width] duration-minor ease-out", color)}
          style={{ width: `${pct}%` }}
        />
        {markers.map((m) => (
          <span
            key={m}
            aria-hidden
            className="absolute top-0 h-full w-0.5 bg-slate-400/70"
            style={{ left: `${(m / max) * 100}%` }}
          />
        ))}
      </div>
    </div>
  );
}
