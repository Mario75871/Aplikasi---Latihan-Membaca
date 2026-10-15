import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * PageHeader — judul seksi + deskripsi + aksi (satu CTA utama per layar).
 * Dipakai di dalam TeacherShell content area agar hierarki halaman konsisten.
 */
export function PageHeader({
  title,
  description,
  action,
  className,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-4", className)}>
      <div className="min-w-0">
        <h2 className="font-serif text-h2 font-semibold text-slate-900">{title}</h2>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

/** SectionTitle — label kecil uppercase untuk memisahkan bagian di dalam halaman. */
export function SectionTitle({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <h3
      className={cn(
        "text-xs font-semibold uppercase tracking-wide text-slate-500",
        className
      )}
    >
      {children}
    </h3>
  );
}
