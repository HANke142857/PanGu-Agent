import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Database } from "lucide-react";
import type { Drawing, ReviewAction, Task } from "@/types";
import { DATA_CHANGED, listDrawings, listTasks } from "@/api/resources";
import { DrawingLibrary } from "@/components/viewer/DrawingLibrary";
import { DrawingViewer } from "@/components/viewer/DrawingViewer";
import { ResultsPanel } from "@/components/results/ResultsPanel";
import { AgentPipeline } from "@/components/common/AgentPipeline";
import { Tag } from "@/components/common/Tag";
import { TASK_STATUS_META } from "@/lib/constants";
import { cx, fmtMs } from "@/lib/format";

export function WorkbenchPage() {
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedDrawingId, setSelectedDrawingId] = useState<string | null>(null);
  const [selectedLabelId, setSelectedLabelId] = useState<string | null>(null);
  const [reviews, setReviews] = useState<Record<string, ReviewAction>>({});
  const [pipelineOpen, setPipelineOpen] = useState(true);

  const load = useCallback(() => {
    listDrawings().then((d) => {
      setDrawings(d);
      setSelectedDrawingId(
        (cur) => cur ?? d.find((x) => x.labels.length)?.id ?? d[0]?.id ?? null,
      );
    });
    listTasks().then(setTasks);
  }, []);

  useEffect(() => {
    load();
    window.addEventListener(DATA_CHANGED, load);
    return () => window.removeEventListener(DATA_CHANGED, load);
  }, [load]);

  const drawing = useMemo(
    () => drawings.find((d) => d.id === selectedDrawingId) ?? null,
    [drawings, selectedDrawingId],
  );

  const task = useMemo(
    () => tasks.find((t) => t.drawing_id === selectedDrawingId) ?? null,
    [tasks, selectedDrawingId],
  );

  useEffect(() => {
    setSelectedLabelId(null);
    setReviews({});
  }, [selectedDrawingId]);

  const onReview = (id: string, action: ReviewAction) =>
    setReviews((r) => ({ ...r, [id]: action }));

  const statusMeta = task ? TASK_STATUS_META[task.status] : null;

  return (
    <div className="flex h-full flex-col">
      <div className="flex min-h-0 flex-1">
        <aside className="w-[240px] shrink-0 border-r border-line bg-panel">
          <DrawingLibrary drawings={drawings} selectedId={selectedDrawingId} onSelect={setSelectedDrawingId} />
        </aside>

        <section className="min-w-0 flex-1 bg-canvas">
          {drawing ? (
            <DrawingViewer
              title={`${drawing.id} · ${drawing.title}`}
              labels={drawing.labels}
              selectedId={selectedLabelId}
              onSelect={setSelectedLabelId}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-ink-4">
              请选择左侧图纸，或点击左上「上传图纸」发起解析
            </div>
          )}
        </section>

        <aside className="flex w-[320px] shrink-0 flex-col border-l border-line bg-panel">
          {drawing && statusMeta && (
            <div className="flex h-10 shrink-0 items-center justify-between border-b border-line px-3">
              <span className="text-sm font-semibold text-ink-2">识别结果</span>
              {task && (
                <Tag tone={statusMeta.tone} dot>
                  {statusMeta.label}
                </Tag>
              )}
            </div>
          )}
          <div className="min-h-0 flex-1">
            <ResultsPanel
              labels={drawing?.labels ?? []}
              conflicts={task?.conflicts ?? []}
              reviews={reviews}
              selectedId={selectedLabelId}
              onSelect={setSelectedLabelId}
              onReview={onReview}
            />
          </div>
        </aside>
      </div>

      <div className="shrink-0 border-t border-line bg-panel">
        <button
          onClick={() => setPipelineOpen((v) => !v)}
          className="flex h-9 w-full items-center gap-2 px-3 text-xs font-semibold text-ink-2"
        >
          <Database className="h-3.5 w-3.5 text-industrial" />
          Agent 执行链路
          {task && (
            <>
              <span className="font-mono font-normal text-ink-4">{task.id}</span>
              <span className="text-ink-4">·</span>
              <span className="font-normal text-ink-3">
                耗时 {fmtMs(task.inference_time_ms)} · {task.total_tokens.toLocaleString()} tokens
              </span>
            </>
          )}
          <span className="ml-auto text-ink-4">
            {pipelineOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          </span>
        </button>
        <div className={cx("overflow-hidden transition-all", pipelineOpen ? "max-h-40" : "max-h-0")}>
          <div className="px-4 pb-3 pt-1">
            {task ? (
              <AgentPipeline stages={task.pipeline} />
            ) : (
              <p className="py-3 text-xs text-ink-4">该图纸暂无关联解析任务。</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
