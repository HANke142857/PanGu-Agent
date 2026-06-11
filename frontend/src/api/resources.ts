// ─────────────────────────────────────────────────────────────
// 资源 API —— 默认 mock；USE_MOCK=false 时打到真实 FastAPI(:8080)
// 真实端点对应后端 idmas/api/routes/{drawings,tasks,knowledge,plm}.py
// 含一层适配：对齐后端 schema 与前端展示模型的差异
// ─────────────────────────────────────────────────────────────
import { API_BASE, ApiError, http, USE_MOCK } from "./client";
import { MOCK_DRAWINGS, MOCK_KNOWLEDGE, MOCK_TASKS } from "@/mock/data";
import { AGENT_ORDER } from "@/lib/constants";
import type {
  BoundingBox,
  Drawing,
  DrawingType,
  KnowledgeResult,
  Label,
  PipelineStage,
  PromptMode,
  PLMSystem,
  PLMWritebackResult,
  SearchType,
  StageStatus,
  Task,
  TaskStatus,
} from "@/types";

const delay = (ms = 280) => new Promise((r) => setTimeout(r, ms));

// 上传/复核成功后广播，让各页面自动刷新
export const DATA_CHANGED = "idmas:data-changed";
function notifyChanged() {
  window.dispatchEvent(new Event(DATA_CHANGED));
}

// ── 适配：后端 → 前端展示模型 ───────────────────────────────
type RawBBox = { x: number; y: number; w?: number; h?: number; width?: number; height?: number };

function normBBox(bb: RawBBox | null | undefined): BoundingBox | null {
  if (!bb) return null;
  return { x: bb.x, y: bb.y, w: bb.w ?? bb.width ?? 0, h: bb.h ?? bb.height ?? 0 };
}

function normLabel(l: Record<string, unknown>): Label {
  return {
    label_id: String(l.label_id),
    name: String(l.name ?? ""),
    confidence: Number(l.confidence ?? 0),
    needs_review: Boolean(l.needs_review),
    spatial_description: (l.spatial_description as string) ?? null,
    quadrant: (l.quadrant as Label["quadrant"]) ?? null,
    bounding_box: normBBox(l.bounding_box as RawBBox),
    has_conflict: Boolean(l.has_conflict),
  };
}

function normDrawing(d: Record<string, any>): Drawing {
  const labels = Array.isArray(d.labels) ? d.labels.map(normLabel) : [];
  return {
    ...(d as Drawing),
    id: String(d.id),
    labels,
    label_count: d.label_count ?? labels.length,
  };
}

// 后端 TaskDetailResponse 没有逐 Agent 链路，按状态推导一个近似 pipeline 用于可视化
function derivePipeline(status: TaskStatus, errorCode?: string | null): PipelineStage[] {
  const presets: Record<TaskStatus, StageStatus[]> = {
    // upload preprocess vision ocr knowledge conflict review report
    created:        ["success", "waiting", "waiting", "waiting", "waiting", "waiting", "waiting", "waiting"],
    processing:     ["success", "success", "running", "waiting", "waiting", "waiting", "waiting", "waiting"],
    waiting_review: ["success", "success", "success", "success", "success", "success", "review", "waiting"],
    completed:      ["success", "success", "success", "success", "success", "success", "success", "success"],
    failed:         ["success", "success", "failed", "waiting", "waiting", "waiting", "waiting", "waiting"],
  };
  const row = presets[status] ?? presets.created;
  return AGENT_ORDER.map((agent, i) => ({
    agent,
    status: row[i],
    detail: row[i] === "failed" && errorCode ? errorCode : undefined,
  }));
}

function normTask(t: Record<string, any>, titleById: Record<string, string>): Task {
  const drawingId = String(t.drawing_id);
  return {
    id: String(t.id),
    status: t.status,
    drawing_id: drawingId,
    drawing_title: titleById[drawingId] ?? drawingId,
    task_type: t.task_type,
    prompt_mode: t.prompt_mode,
    question: t.question ?? "",
    conflicts: Array.isArray(t.conflicts) ? t.conflicts : [],
    human_decision: t.human_decision ?? null,
    inference_time_ms: t.inference_time_ms ?? null,
    total_tokens: t.total_tokens ?? 0,
    error_code: t.error_code ?? null,
    error_message: t.error_message ?? null,
    created_at: t.created_at,
    updated_at: t.updated_at,
    pipeline: derivePipeline(t.status, t.error_code),
  };
}

// ── 图纸 ────────────────────────────────────────────────────
export async function listDrawings(): Promise<Drawing[]> {
  if (USE_MOCK) {
    await delay();
    return MOCK_DRAWINGS;
  }
  const res = await http.get<{ items: Record<string, any>[] }>("/drawings");
  return res.items.map(normDrawing);
}

export async function getDrawing(id: string): Promise<Drawing | undefined> {
  if (USE_MOCK) {
    await delay(120);
    return MOCK_DRAWINGS.find((d) => d.id === id);
  }
  return normDrawing(await http.get<Record<string, any>>(`/drawings/${id}`));
}

export interface DrawingUploadInput {
  file: File;
  title: string;
  drawing_type: DrawingType;
  prompt_mode: PromptMode;
  source_system?: string;
}

// 上传图纸（multipart）→ 后端同步触发 Vision Agent 解析，返回带标号的图纸
export async function uploadDrawing(input: DrawingUploadInput): Promise<Drawing> {
  if (USE_MOCK) {
    await delay(800);
    const now = new Date().toISOString();
    const stub: Drawing = {
      id: `drw-${Math.floor(Math.random() * 9000 + 1000)}`,
      title: input.title,
      drawing_type: input.drawing_type,
      file_format: "png",
      file_url: "",
      file_size_bytes: input.file.size,
      lifecycle_state: "draft",
      source_system: input.source_system ?? "",
      labels: [],
      label_count: 0,
      created_at: now,
      updated_at: now,
    };
    notifyChanged();
    return stub;
  }
  const fd = new FormData();
  fd.append("file", input.file);
  fd.append("title", input.title);
  fd.append("drawing_type", input.drawing_type);
  fd.append("prompt_mode", input.prompt_mode);
  fd.append("source_system", input.source_system ?? "");
  const res = await fetch(`${API_BASE}/drawings`, { method: "POST", body: fd });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const b = await res.json();
      // 后端错误结构：{ error: { message, detail, request_id } }
      msg =
        b.error?.detail ??
        b.error?.message ??
        b.error_message ??
        b.detail ??
        msg;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, msg);
  }
  const data = await res.json();
  notifyChanged();
  return normDrawing(data);
}

// ── 任务 ────────────────────────────────────────────────────
async function drawingTitleMap(): Promise<Record<string, string>> {
  try {
    const res = await http.get<{ items: Record<string, any>[] }>("/drawings");
    return Object.fromEntries(res.items.map((d) => [String(d.id), String(d.title)]));
  } catch {
    return {};
  }
}

export async function listTasks(): Promise<Task[]> {
  if (USE_MOCK) {
    await delay();
    return MOCK_TASKS;
  }
  const [res, titleById] = await Promise.all([
    http.get<{ items: Record<string, any>[] }>("/tasks"),
    drawingTitleMap(),
  ]);
  return res.items.map((t) => normTask(t, titleById));
}

export async function getTask(id: string): Promise<Task | undefined> {
  if (USE_MOCK) {
    await delay(120);
    return MOCK_TASKS.find((t) => t.id === id);
  }
  const [t, titleById] = await Promise.all([
    http.get<Record<string, any>>(`/tasks/${id}`),
    drawingTitleMap(),
  ]);
  return normTask(t, titleById);
}

// ── 知识检索 ────────────────────────────────────────────────
export async function searchKnowledge(query: string, searchType: SearchType): Promise<KnowledgeResult[]> {
  if (USE_MOCK) {
    await delay(420);
    const q = query.trim();
    let pool = MOCK_KNOWLEDGE;
    if (searchType !== "hybrid") pool = pool.filter((r) => r.source === searchType);
    if (!q) return pool;
    return pool.filter(
      (r) => r.title.includes(q) || r.content.includes(q) || r.tags.some((t) => t.includes(q)),
    );
  }
  const res = await http.post<{ results: KnowledgeResult[] }>("/knowledge/search", {
    query,
    search_type: searchType,
    top_k: 8,
  });
  return res.results;
}

// ── PLM 回写 ────────────────────────────────────────────────
export async function writebackPLM(taskId: string, target: PLMSystem): Promise<PLMWritebackResult> {
  if (USE_MOCK) {
    await delay(600);
    return {
      success: true,
      doc_id: `${target.toUpperCase()}-DOC-${taskId.slice(-5)}`,
      target_system: target,
      skipped: false,
      message: "已回写标号识别结果与复核结论",
    };
  }
  return http.post<PLMWritebackResult>("/plm/writeback", { task_id: taskId, target_system: target });
}
