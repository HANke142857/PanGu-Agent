import { useEffect, useMemo, useState } from "react";
import { Cpu, Clock, Hash } from "lucide-react";
import type { Task, TaskStatus } from "@/types";
import { DATA_CHANGED, listTasks } from "@/api/resources";
import { TASK_STATUS_META, TASK_TYPE_LABEL } from "@/lib/constants";
import { AgentPipeline } from "@/components/common/AgentPipeline";
import { Tag } from "@/components/common/Tag";
import { cx, fmtMs, fmtTime } from "@/lib/format";

const FILTERS: { key: TaskStatus | "all"; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "processing", label: "处理中" },
  { key: "waiting_review", label: "待复核" },
  { key: "completed", label: "已完成" },
  { key: "failed", label: "失败" },
];

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<TaskStatus | "all">("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    const load = () =>
      listTasks().then((t) => {
        setTasks(t);
        setExpanded((cur) => cur ?? t[0]?.id ?? null);
      });
    load();
    window.addEventListener(DATA_CHANGED, load);
    return () => window.removeEventListener(DATA_CHANGED, load);
  }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: tasks.length };
    for (const t of tasks) c[t.status] = (c[t.status] ?? 0) + 1;
    return c;
  }, [tasks]);

  const filtered = tasks.filter((t) => filter === "all" || t.status === filter);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex h-12 shrink-0 items-center gap-3 border-b border-line bg-panel px-4">
        <h1 className="text-base font-semibold text-ink">任务中心</h1>
        <span className="text-xs text-ink-4">多 Agent 解析任务流水线监控</span>
        <div className="ml-auto flex items-center gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={cx(
                "flex h-7 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium transition-colors",
                filter === f.key ? "bg-industrial-50 text-industrial-600" : "text-ink-3 hover:bg-canvas",
              )}
            >
              {f.label}
              <span className="font-mono text-2xs text-ink-4">{counts[f.key] ?? 0}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        <div className="panel overflow-hidden">
          <table className="w-full border-collapse">
            <thead className="border-b border-line bg-canvas">
              <tr>
                <th className="th w-8"></th>
                <th className="th">任务 / 图纸</th>
                <th className="th">类型</th>
                <th className="th">状态</th>
                <th className="th">耗时</th>
                <th className="th">Tokens</th>
                <th className="th">创建时间</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => {
                const meta = TASK_STATUS_META[t.status];
                const open = expanded === t.id;
                return (
                  <>
                    <tr
                      key={t.id}
                      onClick={() => setExpanded(open ? null : t.id)}
                      className={cx(
                        "cursor-pointer border-b border-line transition-colors",
                        open ? "bg-industrial-50/40" : "hover:bg-canvas",
                      )}
                    >
                      <td className="td"><StatusGlyph status={t.status} /></td>
                      <td className="td">
                        <div className="font-medium text-ink">{t.drawing_title}</div>
                        <div className="font-mono text-2xs text-ink-4">{t.id} · {t.drawing_id}</div>
                      </td>
                      <td className="td"><span className="text-ink-2">{TASK_TYPE_LABEL[t.task_type]}</span></td>
                      <td className="td"><Tag tone={meta.tone} dot>{meta.label}</Tag></td>
                      <td className="td font-mono text-2xs text-ink-3">{fmtMs(t.inference_time_ms)}</td>
                      <td className="td font-mono text-2xs text-ink-3">{t.total_tokens.toLocaleString()}</td>
                      <td className="td text-2xs text-ink-3">{fmtTime(t.created_at)}</td>
                    </tr>
                    {open && (
                      <tr key={`${t.id}-detail`} className="border-b border-line bg-canvas/60">
                        <td colSpan={7} className="px-4 py-3">
                          <div className="mb-2 flex flex-wrap items-center gap-2 text-2xs text-ink-3">
                            <span className="font-medium text-ink-2">{t.question || "—"}</span>
                            <Tag>{t.prompt_mode}</Tag>
                            <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{fmtMs(t.inference_time_ms)}</span>
                            <span className="flex items-center gap-1"><Hash className="h-3 w-3" />{t.total_tokens.toLocaleString()} tokens</span>
                          </div>
                          {t.error_message && (
                            <div className="mb-2 rounded border border-danger/30 bg-danger-50 px-2.5 py-1.5 text-2xs text-danger">
                              <span className="font-mono font-semibold">{t.error_code}</span> · {t.error_message}
                            </div>
                          )}
                          <div className="rounded-lg border border-line bg-panel p-3">
                            <AgentPipeline stages={t.pipeline} />
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
          {!filtered.length && (
            <div className="flex flex-col items-center gap-2 py-12 text-ink-4">
              <Cpu className="h-8 w-8" />
              <p className="text-xs">该筛选下暂无任务</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusGlyph({ status }: { status: TaskStatus }) {
  const tone = TASK_STATUS_META[status].tone;
  const color = {
    neutral: "bg-ink-4",
    industrial: "bg-industrial",
    ok: "bg-ok",
    warn: "bg-warn",
    danger: "bg-danger",
    proc: "bg-proc",
  }[tone];
  return (
    <span className="flex items-center justify-center">
      <span className={cx("h-2 w-2 rounded-full", color, status === "processing" && "animate-pulse")} />
    </span>
  );
}
