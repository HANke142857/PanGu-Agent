import { useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileUp,
  Loader2,
  Sparkles,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import type { DrawingType, PromptMode } from "@/types";
import { DRAWING_TYPE_LABEL } from "@/lib/constants";
import { uploadDrawing } from "@/api/resources";
import { cx, fmtBytes } from "@/lib/format";

const PROMPT_MODES: { key: PromptMode; label: string; hint: string }[] = [
  { key: "standard_visual", label: "标准视觉", hint: "通用标号识别" },
  { key: "cot_visual", label: "CoT 视觉", hint: "链式推理，复杂装配" },
  { key: "few_shot_visual", label: "Few-Shot", hint: "示例引导，专业图纸" },
];

export function UploadDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState("");
  const [dtype, setDtype] = useState<DrawingType>("assembly");
  const [source, setSource] = useState("Teamcenter");
  const [mode, setMode] = useState<PromptMode>("cot_visual");
  const [drag, setDrag] = useState(false);
  const [phase, setPhase] = useState<"idle" | "submitting" | "done" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    const picked = Array.from(list);
    setFiles((prev) => [...prev, ...picked]);
    if (!title && picked[0]) setTitle(picked[0].name.replace(/\.[^.]+$/, ""));
  };

  const reset = () => {
    setFiles([]);
    setTitle("");
    setPhase("idle");
    setErrorMsg("");
  };

  const submit = async () => {
    setPhase("submitting");
    setErrorMsg("");
    try {
      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        await uploadDrawing({
          file: f,
          title: files.length > 1 ? `${title} (${f.name})` : title,
          drawing_type: dtype,
          prompt_mode: mode,
          source_system: source,
        });
      }
      setPhase("done");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "上传失败，请检查后端是否可达");
      setPhase("error");
    }
  };

  const canSubmit = files.length > 0 && title.trim() && phase !== "submitting";

  return (
    <div className={cx("fixed inset-0 z-50", open ? "pointer-events-auto" : "pointer-events-none")}>
      <div
        className={cx(
          "absolute inset-0 bg-canvas/60 backdrop-blur-[2px] transition-opacity",
          open ? "opacity-100" : "opacity-0",
        )}
        onClick={onClose}
      />
      <aside
        className={cx(
          "absolute right-0 top-0 flex h-full w-full max-w-[440px] flex-col border-l border-line bg-panel shadow-drawer transition-transform duration-300",
          open ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="relative flex h-12 shrink-0 items-center justify-between border-b border-line px-4">
          <div className="topbar-sheen pointer-events-none absolute inset-x-0 bottom-0 h-px opacity-70" />
          <div className="flex items-center gap-2">
            <UploadCloud className="h-4 w-4 text-industrial" />
            <span className="text-sm font-semibold text-ink">上传图纸 · 发起解析</span>
          </div>
          <button className="btn-icon h-7 w-7" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </div>

        {phase === "done" ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
            <div className="glow-ring flex h-14 w-14 items-center justify-center rounded-full bg-ok-50 text-ok">
              <CheckCircle2 className="h-8 w-8" />
            </div>
            <p className="text-sm font-semibold text-ink">已上传 {files.length} 张图纸并触发解析</p>
            <p className="max-w-[260px] text-xs text-ink-3">
              {DRAWING_TYPE_LABEL[dtype]} · {mode} —— Vision Agent 已解析标号，可在「工作台」查看识别结果与置信度。
            </p>
            <div className="mt-2 flex gap-2">
              <button className="btn" onClick={reset}>继续上传</button>
              <button className="btn btn-primary" onClick={onClose}>完成</button>
            </div>
          </div>
        ) : (
          <>
            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDrag(true);
                }}
                onDragLeave={() => setDrag(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDrag(false);
                  addFiles(e.dataTransfer.files);
                }}
                onClick={() => inputRef.current?.click()}
                className={cx(
                  "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors",
                  drag ? "border-industrial bg-industrial-50" : "border-line-strong bg-canvas hover:border-industrial/60",
                )}
              >
                <FileUp className="h-7 w-7 text-industrial" />
                <div className="text-sm font-medium text-ink-2">拖拽图纸到此，或点击选择</div>
                <div className="text-2xs text-ink-4">支持 PNG / JPG / PDF / DWG / DXF，单文件 ≤ 50MB</div>
                <input
                  ref={inputRef}
                  type="file"
                  multiple
                  accept=".png,.jpg,.jpeg,.pdf,.dwg,.dxf"
                  className="hidden"
                  onChange={(e) => addFiles(e.target.files)}
                />
              </div>

              {files.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {files.map((f, i) => (
                    <li key={i} className="flex items-center gap-2 rounded-md border border-line bg-canvas px-2.5 py-2">
                      <FileUp className="h-3.5 w-3.5 shrink-0 text-ink-3" />
                      <span className="min-w-0 flex-1 truncate text-xs text-ink-2">{f.name}</span>
                      <span className="font-mono text-2xs text-ink-4">{fmtBytes(f.size)}</span>
                      <button className="text-ink-4 hover:text-danger" onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              <div className="mt-5 space-y-3.5">
                <Field label="标题">
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="如：减速机总装配图 ZJ-200"
                    className="h-8 w-full rounded-md border border-line bg-canvas px-2.5 text-sm text-ink placeholder:text-ink-4 focus:border-industrial focus:bg-panel focus:outline-none focus:ring-2 focus:ring-industrial/25"
                  />
                </Field>

                <Field label="图纸类型">
                  <div className="grid grid-cols-3 gap-1.5">
                    {(Object.keys(DRAWING_TYPE_LABEL) as DrawingType[]).map((t) => (
                      <button
                        key={t}
                        onClick={() => setDtype(t)}
                        className={cx(
                          "h-8 rounded-md border text-xs font-medium transition-colors",
                          dtype === t ? "border-industrial bg-industrial-50 text-industrial-600" : "border-line text-ink-3 hover:bg-canvas",
                        )}
                      >
                        {DRAWING_TYPE_LABEL[t]}
                      </button>
                    ))}
                  </div>
                </Field>

                <Field label="来源系统">
                  <div className="flex gap-1.5">
                    {["Teamcenter", "ENOVIA", "IntePLM"].map((s) => (
                      <button
                        key={s}
                        onClick={() => setSource(s)}
                        className={cx(
                          "h-8 flex-1 rounded-md border text-xs font-medium transition-colors",
                          source === s ? "border-industrial bg-industrial-50 text-industrial-600" : "border-line text-ink-3 hover:bg-canvas",
                        )}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </Field>

                <Field label="Prompt 模式">
                  <div className="space-y-1.5">
                    {PROMPT_MODES.map((m) => (
                      <button
                        key={m.key}
                        onClick={() => setMode(m.key)}
                        className={cx(
                          "flex w-full items-center gap-2 rounded-md border px-2.5 py-2 text-left transition-colors",
                          mode === m.key ? "border-industrial bg-industrial-50" : "border-line hover:bg-canvas",
                        )}
                      >
                        <Sparkles className={cx("h-3.5 w-3.5 shrink-0", mode === m.key ? "text-industrial" : "text-ink-4")} />
                        <span className={cx("text-xs font-medium", mode === m.key ? "text-industrial-600" : "text-ink-2")}>{m.label}</span>
                        <span className="ml-auto text-2xs text-ink-4">{m.hint}</span>
                      </button>
                    ))}
                  </div>
                </Field>

                {phase === "error" && (
                  <div className="flex items-start gap-2 rounded-md border border-danger/30 bg-danger-50 px-2.5 py-2 text-2xs text-danger">
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>{errorMsg}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="shrink-0 border-t border-line p-3">
              <div className="flex gap-2">
                <button className="btn flex-1 justify-center" onClick={onClose}>取消</button>
                <button className="btn btn-primary flex-1 justify-center" disabled={!canSubmit} onClick={submit}>
                  {phase === "submitting" ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      上传解析中…
                    </>
                  ) : phase === "error" ? (
                    "重试"
                  ) : (
                    "发起解析任务"
                  )}
                </button>
              </div>
            </div>
          </>
        )}
      </aside>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-2xs font-semibold uppercase tracking-wide text-ink-4">{label}</div>
      {children}
    </div>
  );
}
