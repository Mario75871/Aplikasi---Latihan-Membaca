import { cn, formatNumber } from "@/lib/utils";

/**
 * StatTile — kartu metrik (WCPM, Akurasi, Pemahaman, dst.).
 *
 * Tenang: cukup angka besar + label, tanpa garis warna di atas maupun bayangan.
 * Angka metrik NETRAL (tanpa warna merah) — warna hanya dipakai untuk status.
 * `empty` menampilkan "–" netral untuk siswa tanpa data.
 */
export function StatTile({
  label,
  value,
  unit,
  delta,
  empty = false,
  hint,
  className,
}: {
  label: string;
  value: number | string;
  unit?: string;
  delta?: { value: number; direction: "up" | "down" };
  /** Diterima untuk kompatibilitas; warna tidak lagi dipakai di angka metrik. */
  accent?: "brand" | "accuracy" | "competency" | "neutral";
  /** Bila true: tampilkan state netral "–" tanpa warna menghakimi. */
  empty?: boolean;
  hint?: string;
  className?: string;
}) {
  return (
    <div className={cn("rounded-lg border border-paper-200 bg-white p-4", className)}>
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p
        className={cn(
          "tabular mt-1 text-metric font-bold tracking-tight",
          empty ? "text-slate-300" : "text-slate-900"
        )}
      >
        {empty ? "–" : typeof value === "number" ? formatNumber(value) : value}
        {!empty && unit && (
          <span className="ml-1 text-base font-semibold text-slate-400">{unit}</span>
        )}
      </p>
      {!empty && delta && (
        <p className="tabular mt-1 text-xs font-semibold text-slate-500">
          <span aria-hidden>{delta.direction === "up" ? "▲" : "▼"}</span>{" "}
          {Math.abs(delta.value)}
          {unit}
        </p>
      )}
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}
