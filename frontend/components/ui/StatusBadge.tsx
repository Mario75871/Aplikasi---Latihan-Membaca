import { statusMeta, type AdaptiveStatus, STATUS_META, UNASSESSED_META, type DisplayStatus } from "@/lib/tokens";
import { Icon } from "./icons";
import { InfoTip } from "./Tooltip";
import { cn } from "@/lib/utils";

/**
 * StatusText — status sebagai IKON kecil berwarna + teks (bukan pil penuh).
 * Ikon (bukan sekadar titik) memperkuat makna dan mengurangi "pil berdot"
 * seragam; tetap membawa makna lewat teks, bukan warna saja (WCAG 2.1 AA).
 * Dipakai di tabel & daftar guru yang tenang.
 */
export function StatusText({
  status,
  className,
  showDot = true,
}: {
  status: AdaptiveStatus | null | undefined;
  className?: string;
  showDot?: boolean;
}) {
  const meta = statusMeta(status);
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm text-slate-700", className)}>
      {showDot && (
        <Icon
          name={meta.icon}
          size={15}
          strokeWidth={2}
          className={cn("shrink-0", meta.text)}
        />
      )}
      <span className="font-medium">{meta.label}</span>
    </span>
  );
}

/**
 * StatusBadge — pill status (dipakai hemat, mis. profil/ringkasan).
 * Satu-satunya sumber label status di UI; selalu ikon + teks.
 *
 * `status = null` menampilkan state netral "Belum Diases".
 */
export function StatusBadge({
  status,
  className,
}: {
  status: AdaptiveStatus | null | undefined;
  className?: string;
}) {
  const meta = statusMeta(status);
  return (
    <span
      aria-label={`Status: ${meta.label}`}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
        meta.bg,
        meta.text,
        meta.border,
        className
      )}
    >
      <Icon name={meta.icon} size={14} strokeWidth={2.5} />
      {meta.label}
    </span>
  );
}

/** StatusBadgeWithInfo — pill + tooltip penjelasan (bahasa pengguna, tanpa jargon). */
export function StatusBadgeWithInfo({
  status,
  className,
}: {
  status: AdaptiveStatus | null | undefined;
  className?: string;
}) {
  const meta = statusMeta(status);
  return (
    <span className={cn("inline-flex items-center gap-1", className)}>
      <StatusBadge status={status} />
      <InfoTip label={`Penjelasan status ${meta.label}`} text={meta.tooltip} />
    </span>
  );
}

/** Titik status kecil untuk legenda/filter (selalu berdampingan dengan teks). */
export function StatusDot({ status }: { status: AdaptiveStatus | null | undefined }) {
  const meta = statusMeta(status);
  return <span aria-hidden className={cn("inline-block h-2.5 w-2.5 rounded-full", meta.dot)} />;
}

const LEGEND_ORDER: DisplayStatus[] = [
  "INTERVENE",
  "PROMOTION_CANDIDATE",
  "STAY",
  "PROMOTE",
  "UNASSESSED",
];

/**
 * StatusLegend — SATU legenda status untuk footer halaman (menggantikan ikon (i)
 * di setiap baris). Menjelaskan tiap status dalam bahasa pengguna.
 */
export function StatusLegend({ className }: { className?: string }) {
  const items: { key: DisplayStatus; meta: typeof UNASSESSED_META }[] = LEGEND_ORDER.map((k) => ({
    key: k,
    meta: k === "UNASSESSED" ? UNASSESSED_META : STATUS_META[k],
  }));

  return (
    <section
      aria-label="Keterangan status"
      className={cn(
        "rounded-lg border border-paper-200 bg-paper-100/60 px-4 py-3",
        className
      )}
    >
      <p className="mb-2 text-xs font-semibold text-slate-500">
        Keterangan status
      </p>
      <ul className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-600">
        {items.map(({ key, meta }) => (
          <li key={key} className="flex items-center gap-2">
            <Icon
              name={meta.icon}
              size={14}
              strokeWidth={2}
              className={cn("shrink-0", meta.text)}
            />
            <span className="font-semibold text-slate-700">{meta.label}</span>
            <span className="text-slate-500">{meta.tooltip}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
