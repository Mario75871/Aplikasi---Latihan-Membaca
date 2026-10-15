import { STATUS_META, UNASSESSED_META, type DisplayStatus } from "@/lib/tokens";
import { cn, formatNumber } from "@/lib/utils";

export interface KpiItem {
  key: DisplayStatus | "TOTAL";
  label: string;
  value: number;
  /** Titik penanda kecil (hanya untuk status); TOTAL tanpa titik. */
  dot?: string;
}

/**
 * ClassKpiRow — ringkasan kelas (§32) memakai SATU kosakata status.
 *
 * Tenang & rapat: cukup angka besar + label dalam satu baris, tanpa garis warna
 * di atas kartu maupun ikon dekoratif. Makna status dibawa oleh titik kecil
 * berwarna + label (bukan warna saja). Tiap kartu bisa diklik untuk memfilter.
 */
export function ClassKpiRow({
  total,
  unassessed,
  intervene,
  stay,
  candidate,
  promote,
  activeStatus,
  onSelect,
  className,
}: {
  total: number;
  unassessed: number;
  intervene: number;
  stay: number;
  candidate: number;
  promote: number;
  activeStatus?: DisplayStatus | null;
  onSelect?: (status: DisplayStatus | null) => void;
  className?: string;
}) {
  const items: KpiItem[] = [
    { key: "TOTAL", label: "Total siswa", value: total },
    { key: "INTERVENE", label: STATUS_META.INTERVENE.label, value: intervene, dot: STATUS_META.INTERVENE.dot },
    { key: "PROMOTION_CANDIDATE", label: STATUS_META.PROMOTION_CANDIDATE.label, value: candidate, dot: STATUS_META.PROMOTION_CANDIDATE.dot },
    { key: "STAY", label: STATUS_META.STAY.label, value: stay, dot: STATUS_META.STAY.dot },
    { key: "PROMOTE", label: STATUS_META.PROMOTE.label, value: promote, dot: STATUS_META.PROMOTE.dot },
    { key: "UNASSESSED", label: UNASSESSED_META.label, value: unassessed, dot: UNASSESSED_META.dot },
  ];

  return (
    <div className={cn("grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-paper-200 bg-paper-200 sm:grid-cols-3 xl:grid-cols-6", className)}>
      {items.map((it) => {
        const isFilterable = it.key !== "TOTAL" && Boolean(onSelect);
        const active = activeStatus === it.key;
        return (
          <button
            key={it.key}
            type="button"
            disabled={!isFilterable}
            onClick={isFilterable ? () => onSelect?.(active ? null : (it.key as DisplayStatus)) : undefined}
            aria-pressed={isFilterable ? active : undefined}
            className={cn(
              "flex flex-col items-start gap-1 px-4 py-3 text-left transition-colors",
              active ? "bg-brand-50" : "bg-white",
              isFilterable && "hover:bg-paper-50",
              !isFilterable && "cursor-default"
            )}
          >
            <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
              {it.dot && (
                <span aria-hidden className={cn("inline-block h-2 w-2 rounded-full", it.dot)} />
              )}
              {it.label}
            </span>
            <span className="tabular text-3xl font-bold leading-none text-slate-900">
              {formatNumber(it.value)}
            </span>
          </button>
        );
      })}
    </div>
  );
}
