import { DISCLAIMERS } from "@/lib/tokens";
import { Icon } from "./icons";
import { cn } from "@/lib/utils";

type DisclaimerKind = keyof typeof DISCLAIMERS;

/**
 * DisclaimerBanner — komponen wajib untuk klaim eksternal.
 * Jenis: hasbrouck · threshold · medical.
 *
 * Gaya: footnote rapi (ikon shield-alert + teks kecil netral), tetap terbaca
 * tetapi tidak mencolok.
 */
export function DisclaimerBanner({
  kind,
  text,
  className,
}: {
  kind: DisclaimerKind;
  text?: string;
  className?: string;
}) {
  return (
    <div
      role="note"
      className={cn(
        "flex items-start gap-2 rounded-md border border-paper-200 bg-paper-50 px-3 py-2 text-xs leading-relaxed text-slate-500",
        className
      )}
    >
      <Icon name="shield-alert" size={16} className="mt-0.5 text-slate-400" />
      <span>{text ?? DISCLAIMERS[kind]}</span>
    </div>
  );
}
