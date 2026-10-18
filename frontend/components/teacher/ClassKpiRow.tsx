import { STATUS_META, UNASSESSED_META, type DisplayStatus } from "@/lib/tokens";
import { Icon, type IconName } from "@/components/ui/icons";
import { cn, formatNumber } from "@/lib/utils";

export interface KpiItem {
  key: DisplayStatus | "TOTAL";
  label: string;
  value: number;
  /** Titik penanda kecil (dipertahankan untuk kompatibilitas). */
  dot?: string;
  /** Ikon status (bila ada) — memperkuat makna tanpa bergantung warna. */
  icon?: IconName;
  /** Warna ikon status. */
  iconClass?: string;
}

/**
 * ClassKpiRow — ringkasan kelas memakai SATU kosakata status.
 *
 * Disusun seperti buku-besar (ledger): angka besar rata kanan + label, dipisah
 * garis tipis. Tanpa garis warna di atas kartu, tanpa ikon dekoratif. Makna
 * status dibawa oleh IKON + label (bukan warna saja). Tiap sel dapat difilter.
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
    {
      key: "INTERVENE",
      label: STATUS_META.INTERVENE.label,
      value: intervene,
      dot: STATUS_META.INTERVENE.dot,
      icon: STATUS_META.INTERVENE.icon,
      iconClass: STATUS_META.INTERVENE.text,
    },
    {
      key: "PROMOTION_CANDIDATE",
      label: STATUS_META.PROMOTION_CANDIDATE.label,
      value: candidate,
      dot: STATUS_META.PROMOTION_CANDIDATE.dot,
      icon: STATUS_META.PROMOTION_CANDIDATE.icon,
      iconClass: STATUS_META.PROMOTION_CANDIDATE.text,
    },
    {
      key: "STAY",
      label: STATUS_META.STAY.label,
      value: stay,
      dot: STATUS_META.STAY.dot,
      icon: STATUS_META.STAY.icon,
      iconClass: STATUS_META.STAY.text,
    },
    {
      key: "PROMOTE",
      label: STATUS_META.PROMOTE.label,
      value: promote,
      dot: STATUS_META.PROMOTE.dot,
      icon: STATUS_META.PROMOTE.icon,
      iconClass: STATUS_META.PROMOTE.text,
    },
    {
      key: "UNASSESSED",
      label: UNASSESSED_META.label,
      value: unassessed,
      dot: UNASSESSED_META.dot,
      icon: UNASSESSED_META.icon,
      iconClass: UNASSESSED_META.text,
    },
  ];

  return (
    <div
      className={cn(
        "grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-paper-200 bg-paper-200 sm:grid-cols-3 xl:grid-cols-6",
        className
      )}
    >
      {items.map((it) => {
        const isFilterable = it.key !== "TOTAL" && Boolean(onSelect);
        const active = activeStatus === it.key;
        return (
          <button
            key={it.key}
            type="button"
            disabled={!isFilterable}
            onClick={
              isFilterable
                ? () => onSelect?.(active ? null : (it.key as DisplayStatus))
                : undefined
            }
            aria-pressed={isFilterable ? active : undefined}
            className={cn(
              "relative flex flex-col items-stretch gap-2 px-4 py-3.5 text-left transition-colors",
              active ? "bg-paper-100" : "bg-white",
              isFilterable && "hover:bg-paper-50",
              !isFilterable && "cursor-default"
            )}
          >
            {/* Penanda sel aktif: aturan aksen tipis di tepi kiri, bukan blok warna. */}
            {active && (
              <span aria-hidden className="absolute inset-y-0 left-0 w-0.5 bg-brand-500" />
            )}
            <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
              {it.icon && (
                <Icon
                  name={it.icon}
                  size={13}
                  strokeWidth={2}
                  className={cn("shrink-0", it.iconClass)}
                />
              )}
              {it.label}
            </span>
            <span className="tabular text-right text-3xl font-bold leading-none tracking-tight text-slate-900">
              {formatNumber(it.value)}
            </span>
          </button>
        );
      })}
    </div>
  );
}
