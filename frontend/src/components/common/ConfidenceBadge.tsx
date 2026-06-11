import { confLevel } from "@/lib/constants";
import { cx, fmtPct } from "@/lib/format";

const LEVEL_STYLE = {
  high: { bar: "bg-industrial", text: "text-industrial-600" },
  mid: { bar: "bg-ink-4", text: "text-ink-2" },
  low: { bar: "bg-warn", text: "text-warn" },
} as const;

// 置信度：迷你进度条 + 百分比，工程化呈现
export function ConfidenceBadge({
  value,
  className,
}: {
  value: number;
  className?: string;
}) {
  const lvl = confLevel(value);
  const s = LEVEL_STYLE[lvl];
  return (
    <span className={cx("inline-flex items-center gap-1.5", className)}>
      <span className="h-1.5 w-10 overflow-hidden rounded-full bg-line">
        <span
          className={cx("block h-full rounded-full", s.bar)}
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </span>
      <span className={cx("font-mono text-2xs tabular-nums", s.text)}>
        {fmtPct(value)}
      </span>
    </span>
  );
}
