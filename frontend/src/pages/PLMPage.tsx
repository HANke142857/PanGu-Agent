import { useEffect, useState } from "react";
import { ArrowUpRight, Boxes, CheckCircle2, X } from "lucide-react";
import type { PLMSystem, PLMWritebackResult, Task } from "@/types";
import { listTasks, writebackPLM } from "@/api/resources";
import { TASK_STATUS_META } from "@/lib/constants";
import { Tag } from "@/components/common/Tag";
import { cx, fmtTime } from "@/lib/format";

const SYSTEMS: { key: PLMSystem; label: string }[] = [
  { key: "teamcenter", label: "Teamcenter" },
  { key: "enovia", label: "ENOVIA" },
  { key: "inteplm", label: "IntePLM" },
];

export function PLMPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [confirm, setConfirm] = useState<Task | null>(null);

  useEffect(() => {
    listTasks().then((t) =>
      setTasks(t.filter((x) => x.status === "completed" || x.status === "waiting_review")),
    );
  }, []);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex h-12 shrink-0 items-center gap-3 border-b border-line bg-panel px-4">
        <Boxes className="h-4 w-4 text-industrial" />
        <h1 className="text-base font-semibold text-ink">PLM 回写</h1>
        <span className="text-xs text-ink-4">
          将复核确认的解析结果回写至 PLM
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        <div className="panel overflow-hidden">
          <table className="w-full border-collapse">
            <thead className="border-b border-line bg-canvas">
              <tr>
                <th className="th">任务 / 图纸</th>
                <th className="th">状态</th>
                <th className="th">复核结论</th>
                <th className="th">完成时间</th>
                <th className="th text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => {
                const meta = TASK_STATUS_META[t.status];
                const ready = t.status === "completed";
                return (
                  <tr key={t.id} className="border-b border-line hover:bg-canvas">
                    <td className="td">
                      <div className="font-medium text-ink">
                        {t.drawing_title}
                      </div>
                      <div className="font-mono text-2xs text-ink-4">{t.id}</div>
                    </td>
                    <td className="td">
                      <Tag tone={meta.tone} dot>
                        {meta.label}
                      </Tag>
                    </td>
                    <td className="td text-2xs text-ink-3">
                      {t.human_decision ?? "—"}
                    </td>
                    <td className="td text-2xs text-ink-3">
                      {fmtTime(t.updated_at)}
                    </td>
                    <td className="td text-right">
                      <button
                        disabled={!ready}
                        onClick={() => setConfirm(t)}
                        className={cx(
                          "btn ml-auto",
                          ready && "btn-primary",
                        )}
                        title={ready ? "回写到 PLM" : "需先完成复核"}
                      >
                        回写
                        <ArrowUpRight className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!tasks.length && (
            <p className="py-12 text-center text-xs text-ink-4">
              暂无可回写任务
            </p>
          )}
        </div>
      </div>

      {confirm && (
        <WritebackModal task={confirm} onClose={() => setConfirm(null)} />
      )}
    </div>
  );
}

function WritebackModal({
  task,
  onClose,
}: {
  task: Task;
  onClose: () => void;
}) {
  const [target, setTarget] = useState<PLMSystem>("teamcenter");
  const [state, setState] = useState<"idle" | "running" | "done">("idle");
  const [result, setResult] = useState<PLMWritebackResult | null>(null);

  const submit = async () => {
    setState("running");
    const r = await writebackPLM(task.id, target);
    setResult(r);
    setState("done");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 p-4">
      <div className="w-full max-w-md rounded-xl border border-line bg-panel shadow-pop">
        <div className="flex h-11 items-center justify-between border-b border-line px-4">
          <span className="text-sm font-semibold text-ink">PLM 回写确认</span>
          <button className="btn-icon h-7 w-7" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </div>

        {state === "done" && result ? (
          <div className="p-5 text-center">
            <CheckCircle2 className="mx-auto h-10 w-10 text-ok" />
            <p className="mt-2 text-sm font-medium text-ink">回写成功</p>
            <p className="mt-1 text-xs text-ink-3">{result.message}</p>
            <div className="mt-3 rounded-md border border-line bg-canvas px-3 py-2 font-mono text-2xs text-ink-2">
              {result.target_system} · {result.doc_id}
            </div>
            <button className="btn btn-primary mt-4 w-full justify-center" onClick={onClose}>
              完成
            </button>
          </div>
        ) : (
          <div className="p-4">
            <div className="rounded-lg border border-line bg-canvas p-3 text-xs">
              <Row k="任务 ID" v={task.id} mono />
              <Row k="图纸" v={task.drawing_title} />
              <Row k="复核结论" v={task.human_decision ?? "—"} />
            </div>
            <div className="mt-3">
              <div className="mb-1.5 text-2xs font-semibold uppercase tracking-wide text-ink-4">
                目标系统
              </div>
              <div className="flex gap-1.5">
                {SYSTEMS.map((s) => (
                  <button
                    key={s.key}
                    onClick={() => setTarget(s.key)}
                    className={cx(
                      "flex-1 rounded-md border px-2 py-2 text-xs font-medium transition-colors",
                      target === s.key
                        ? "border-industrial bg-industrial-50 text-industrial-600"
                        : "border-line text-ink-3 hover:bg-canvas",
                    )}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-3 rounded-md border border-warn/30 bg-warn-50 px-3 py-2 text-2xs text-warn">
              回写将创建/更新 PLM 文档对象并写入标号与复核结论，操作可在 PLM 审计日志中追溯。
            </div>
            <div className="mt-4 flex gap-2">
              <button className="btn flex-1 justify-center" onClick={onClose}>
                取消
              </button>
              <button
                className="btn btn-primary flex-1 justify-center"
                disabled={state === "running"}
                onClick={submit}
              >
                {state === "running" ? "回写中…" : "确认回写"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-3 py-0.5">
      <span className="text-ink-4">{k}</span>
      <span className={cx("text-ink-2", mono && "font-mono text-2xs")}>{v}</span>
    </div>
  );
}
