import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { STATUS_META, type AdaptiveStatus } from "@/lib/tokens";
import { cn } from "@/lib/utils";

export interface AttentionItem {
  id: string;
  name: string;
  classLabel: string;
  status: AdaptiveStatus;
  /** Satu kalimat alasan — diambil dari `recommendation` yang sudah ada. */
  reason: string;
}

/** Urutan prioritas: Perlu Intervensi dulu, lalu Kandidat Naik. */
const ATTENTION_PRIORITY: Partial<Record<AdaptiveStatus, number>> = {
  INTERVENE: 0,
  PROMOTION_CANDIDATE: 1,
};

/** Ambil maksimum 3 siswa yang butuh perhatian, urut prioritas. */
export function pickAttention<T extends { status: AdaptiveStatus | null }>(
  rows: T[],
  max = 3
): T[] {
  return rows
    .filter((r) => r.status !== null && r.status in ATTENTION_PRIORITY)
    .sort(
      (a, b) =>
        (ATTENTION_PRIORITY[a.status as AdaptiveStatus] ?? 99) -
        (ATTENTION_PRIORITY[b.status as AdaptiveStatus] ?? 99)
    )
    .slice(0, max);
}

/**
 * AttentionList — "Perlu perhatian hari ini": maks 3 siswa prioritas.
 * Tiap baris: nama, satu kalimat alasan (dari rekomendasi), satu tombol.
 */
export function AttentionList({ items }: { items: AttentionItem[] }) {
  if (items.length === 0) {
    return (
      <section className="rounded-lg border border-paper-200 bg-white p-5">
        <h2 className="font-serif text-h3 font-semibold text-slate-800">
          Perlu perhatian hari ini
        </h2>
        <p className="mt-2 flex items-center gap-2 text-sm text-slate-500">
          <Icon name="check-circle" size={18} className="text-emerald-600" />
          Tidak ada yang mendesak. Semua siswa berjalan baik hari ini.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-paper-200 bg-white">
      <div className="border-b border-paper-100 px-5 py-3.5">
        <h2 className="font-serif text-h3 font-semibold text-slate-800">
          Perlu perhatian hari ini
        </h2>
        <p className="mt-0.5 text-sm text-slate-500">
          Mulai dari siswa yang paling butuh dukungan.
        </p>
      </div>

      <ul className="divide-y divide-paper-100">
        {items.map((it) => {
          const meta = STATUS_META[it.status];
          return (
            <li key={it.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3.5">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-800">{it.name}</span>
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600">
                    <span aria-hidden className={cn("inline-block h-2 w-2 rounded-full", meta.dot)} />
                    {meta.label}
                  </span>
                  <span className="text-xs text-slate-400">{it.classLabel}</span>
                </div>
                <p className="mt-0.5 text-sm text-slate-500">{it.reason}</p>
              </div>

              <Link
                href={`/students/${it.id}`}
                className="shrink-0"
              >
                <Button variant="secondary" size="md">
                  Lihat siswa
                </Button>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
