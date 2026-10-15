import * as React from "react";
import { cn } from "@/lib/utils";

export type ReadingLevel = 1 | 2 | 3;

/**
 * Ukuran teks default (design-system §7.4): dipakai di S-02.
 * reading-1/2/3 = 32px/28px/24px, line-height 1.9 dari token Tailwind.
 */
const SIZE: Record<ReadingLevel, string> = {
  1: "text-reading-1",
  2: "text-reading-2",
  3: "text-reading-3",
};

/**
 * Ukuran teks BESAR (legacy, dipakai bila layar butuh fokus penuh).
 * Line-height 1.9 (dari class `.passage`), lebar baris maks 60ch.
 */
const SIZE_LARGE: Record<ReadingLevel, string> = {
  1: "text-[1.75rem] sm:text-[2rem] lg:text-[2.25rem]",
  2: "text-[1.75rem] sm:text-[2.25rem] lg:text-[2.5rem]",
  3: "text-[1.75rem] sm:text-[2rem] lg:text-[2.5rem]",
};

/**
 * ReadingPassage — tampilan bacaan siswa (design-system §7.4).
 * Font Andika, line-height ≥ 1.9, lebar maks 60ch, kontras tinggi (§3.8).
 * Setiap kata diberi data-word-idx untuk highlight sinkron timestamp (§12).
 *
 * `size="record"` (layar rekam S-03): teks lebih ringkas (clamp 22–28px,
 * line-height 1.65, ~65ch) agar banyak baris terlihat sambil merekam.
 * `size="large"` = teks besar fokus penuh. Teks tetap statis (tanpa highlight
 * real-time) sesuai batasan PRD.
 */
export function ReadingPassage({
  title,
  content,
  level = 2,
  highlightIndex,
  className,
  size = "default",
  titleVariant = "default",
}: {
  title: string;
  content: string;
  level?: ReadingLevel;
  highlightIndex?: number;
  className?: string;
  /** "record" = ringkas untuk layar rekam; "large" = besar; "default" = S-02. */
  size?: "default" | "large" | "record";
  /** "small" = judul kecil di atas teks (layar rekam). */
  titleVariant?: "default" | "small";
}) {
  const words = React.useMemo(() => content.split(/\s+/), [content]);
  const textSize =
    size === "record" ? undefined : size === "large" ? SIZE_LARGE[level] : SIZE[level];

  return (
    <article
      className={cn(
        "passage mx-auto",
        size === "record" && "passage-record",
        className
      )}
    >
      <h1
        className={cn(
          "text-center font-serif font-semibold text-slate-800",
          titleVariant === "small" ? "mb-3 text-base sm:text-lg" : "mb-6 text-2xl sm:text-3xl"
        )}
      >
        {title}
      </h1>
      <p className={cn("font-reading text-slate-800", textSize)}>
        {words.map((w, i) => (
          <React.Fragment key={i}>
            <span
              data-word-idx={i}
              className={cn(
                "rounded-sm transition-colors",
                highlightIndex === i && "bg-brand-100 text-brand-800"
              )}
            >
              {w}
            </span>{" "}
          </React.Fragment>
        ))}
      </p>
    </article>
  );
}
