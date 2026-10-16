import * as React from "react";
import { Button } from "./Button";
import { Icon, type IconName } from "./icons";
import { cn } from "@/lib/utils";

/** EmptyState — belum ada data. Ilustrasi ringan + 1 kalimat + CTA. */
export function EmptyState({
  icon = "inbox",
  title,
  description,
  action,
  className,
}: {
  icon?: IconName;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-paper-200 bg-white p-10 text-center",
        className
      )}
    >
      <span className="flex h-14 w-14 items-center justify-center rounded-full bg-paper-100 text-slate-400">
        <Icon name={icon} size={28} />
      </span>
      <h3 className="font-serif text-h3 font-semibold text-slate-800">{title}</h3>
      {description && <p className="max-w-sm text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}

/** ErrorState — error teknis. SELALU sediakan langkah keluar (NFR-03). */
export function ErrorState({
  title = "Terjadi kesalahan.",
  description = "Coba lagi ya.",
  onRetry,
  fallbackAction,
  className,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
  fallbackAction?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-amber-200 bg-amber-50 p-10 text-center",
        className
      )}
    >
      <span className="flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-amber-700">
        <Icon name="alert-triangle" size={28} />
      </span>
      <h3 className="font-display text-lg font-bold text-amber-900">{title}</h3>
      <p className="max-w-sm text-sm text-amber-800">{description}</p>
      <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
        {onRetry && (
          <Button variant="primary" size="md" onClick={onRetry}>
            <Icon name="rotate-ccw" size={18} />
            Coba Lagi
          </Button>
        )}
        {fallbackAction}
      </div>
    </div>
  );
}

/** Skeleton — placeholder loading untuk tabel/kartu. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("animate-pulse rounded-md bg-slate-200/70", className)}
    />
  );
}

export function TableSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2" role="status" aria-label="Memuat data">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

/** CardSkeleton — skeleton grid kartu (mis. daftar kelas / bacaan). */
export function CardSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 md:grid-cols-2" role="status" aria-label="Memuat data">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-lg border border-paper-200 bg-white p-6">
          <Skeleton className="h-5 w-1/2" />
          <Skeleton className="mt-3 h-4 w-1/3" />
          <Skeleton className="mt-2 h-4 w-2/3" />
        </div>
      ))}
    </div>
  );
}
