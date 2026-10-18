"use client";

import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Icon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

export interface ClassOption {
  id: string;
  name: string;
  /** Jumlah siswa — dari GET /dashboard/class/{id}. */
  studentCount: number;
}

/**
 * ClassSwitcher — pemilih kelas aktif untuk guru yang mengelola beberapa kelas.
 * Mengubah query `?class=` tanpa berpindah halaman (FR-02, persona Pak Yusuf).
 * Aksesibel: <select> native dengan label tersembunyi + ikon sekolah.
 */
export function ClassSwitcher({
  classes,
  activeClassId,
  className,
}: {
  classes: ClassOption[];
  activeClassId: string;
  className?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function onChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("class", e.target.value);
    router.replace(`${pathname}?${params.toString()}`);
  }

  const active = classes.find((c) => c.id === activeClassId);

  return (
    <div className={cn("relative inline-flex items-center", className)}>
      <Icon
        name="school"
        size={18}
        className="pointer-events-none absolute left-3 text-slate-400"
      />
      <label htmlFor="class-switcher" className="sr-only">
        Pilih kelas
      </label>
      <select
        id="class-switcher"
        value={activeClassId}
        onChange={onChange}
        className={cn(
          "h-11 appearance-none rounded-md border border-slate-200 bg-white pl-10 pr-10 text-sm font-semibold text-slate-800",
          "hover:border-brand-300 focus-visible:outline-none"
        )}
      >
        {classes.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name} · {c.studentCount} siswa
          </option>
        ))}
      </select>
      <Icon
        name="chevron-down"
        size={18}
        className="pointer-events-none absolute right-3 text-slate-400"
      />
      {/* Label aktif untuk screen reader (mis. "Kelas 2A · 28 siswa") */}
      <span className="sr-only" aria-live="polite">
        {active ? `Kelas aktif: ${active.name}` : ""}
      </span>
    </div>
  );
}
