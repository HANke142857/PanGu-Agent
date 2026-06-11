import type { ReactNode } from "react";
import type { Tone } from "@/lib/constants";
import { cx } from "@/lib/format";

const TONE: Record<Tone, string> = {
  neutral: "bg-canvas text-ink-3 border-line",
  industrial: "bg-industrial-50 text-industrial-600 border-industrial/30",
  ok: "bg-ok-50 text-ok border-ok/30",
  warn: "bg-warn-50 text-warn border-warn/30",
  danger: "bg-danger-50 text-danger border-danger/30",
  proc: "bg-proc-50 text-proc border-proc/30",
};

export function Tag({
  tone = "neutral",
  children,
  className,
  dot = false,
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
  dot?: boolean;
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-2xs font-medium whitespace-nowrap",
        TONE[tone],
        className,
      )}
    >
      {dot && (
        <span
          className={cx(
            "h-1.5 w-1.5 rounded-full",
            tone === "neutral" ? "bg-ink-4" : "bg-current",
          )}
        />
      )}
      {children}
    </span>
  );
}
