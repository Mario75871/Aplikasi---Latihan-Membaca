"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * InfoTip — ikon info kecil dengan tooltip.
 *
 * Dipakai untuk menaruh istilah teknis (mis. "INTERVENE", "WCPM") di balik tooltip
 * sehingga UI guru tetap berbahasa Indonesia sederhana (design-system §10).
 * Aksesibel: dapat difokus via keyboard dan memakai aria-describedby.
 */
export function InfoTip({
  text,
  label = "Info",
  className,
  iconClassName,
}: {
  text: string;
  label?: string;
  className?: string;
  iconClassName?: string;
}) {
  const id = React.useId();
  return (
    <span className={cn("group relative inline-flex items-center", className)}>
      <button
        type="button"
        aria-label={label}
        aria-describedby={id}
        className={cn(
          "inline-flex h-6 w-6 items-center justify-center rounded-full text-slate-400",
          "hover:text-slate-600 focus-visible:outline-none",
          iconClassName
        )}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
      </button>
      <span
        id={id}
        role="tooltip"
        className={cn(
          "pointer-events-none absolute bottom-full left-1/2 z-dropdown mb-2 w-60 -translate-x-1/2",
          "rounded-md bg-slate-800 px-3 py-2 text-left text-xs font-normal leading-snug text-white shadow-lg",
          "opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
        )}
      >
        {text}
      </span>
    </span>
  );
}
