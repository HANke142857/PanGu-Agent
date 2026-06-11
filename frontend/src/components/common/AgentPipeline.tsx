import { CheckCircle2, CircleDashed, Loader2, PauseCircle, XCircle } from "lucide-react";
import type { PipelineStage, StageStatus } from "@/types";
import { AGENT_META } from "@/lib/constants";
import { cx, fmtMs } from "@/lib/format";

const STATUS_STYLE: Record<
  StageStatus,
  { ring: string; text: string; line: string; Icon: typeof CheckCircle2 }
> = {
  waiting: { ring: "border-line bg-panel text-ink-4", text: "text-ink-4", line: "bg-line", Icon: CircleDashed },
  running: { ring: "border-proc bg-proc-50 text-proc glow-ring animate-pulse-glow", text: "text-proc", line: "bg-line", Icon: Loader2 },
  success: { ring: "border-ok bg-ok-50 text-ok", text: "text-ink-2", line: "bg-ok/40", Icon: CheckCircle2 },
  review: { ring: "border-warn bg-warn-50 text-warn", text: "text-warn", line: "bg-line", Icon: PauseCircle },
  failed: { ring: "border-danger bg-danger-50 text-danger", text: "text-danger", line: "bg-line", Icon: XCircle },
};

// 工程流水线（Pipeline）—— 横向节点 + 连接线，状态色编码
export function AgentPipeline({ stages, compact = false }: { stages: PipelineStage[]; compact?: boolean }) {
  return (
    <div className="flex items-start overflow-x-auto">
      {stages.map((stage, i) => {
        const s = STATUS_STYLE[stage.status];
        const meta = AGENT_META[stage.agent];
        const last = i === stages.length - 1;
        return (
          <div key={stage.agent} className="flex items-start">
            <div className="flex w-[88px] flex-col items-center text-center">
              <div className={cx("flex items-center justify-center rounded-full border", compact ? "h-7 w-7" : "h-9 w-9", s.ring)}>
                <s.Icon className={cx(compact ? "h-4 w-4" : "h-5 w-5", stage.status === "running" && "animate-spin")} />
              </div>
              <div className={cx("mt-1.5 text-2xs font-medium leading-tight", s.text)}>{meta.short}</div>
              {!compact && <div className="mt-0.5 text-2xs text-ink-4">{stage.detail ?? fmtMs(stage.duration_ms)}</div>}
            </div>
            {!last && (
              <div
                className={cx(
                  "mt-3.5 h-0.5 w-6 shrink-0 overflow-hidden rounded-full md:w-10",
                  stage.status === "running" ? "flow-line" : s.line,
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
