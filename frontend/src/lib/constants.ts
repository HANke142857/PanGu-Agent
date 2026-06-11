import type {
  AgentId,
  DrawingType,
  LifecycleState,
  SearchType,
  StageStatus,
  TaskStatus,
  TaskType,
} from "@/types";

// ── 置信度分级 ──────────────────────────────────────────────
// 高 ≥0.85 蓝/绿，中 0.6~0.85 默认，低 <0.6 琥珀（待复核）
export type ConfLevel = "high" | "mid" | "low";

export function confLevel(c: number): ConfLevel {
  if (c >= 0.85) return "high";
  if (c >= 0.6) return "mid";
  return "low";
}

// ── 任务状态 ────────────────────────────────────────────────
export const TASK_STATUS_META: Record<
  TaskStatus,
  { label: string; tone: Tone }
> = {
  created: { label: "已创建", tone: "neutral" },
  processing: { label: "处理中", tone: "proc" },
  waiting_review: { label: "待复核", tone: "warn" },
  completed: { label: "已完成", tone: "ok" },
  failed: { label: "失败", tone: "danger" },
};

export type Tone = "neutral" | "industrial" | "ok" | "warn" | "danger" | "proc";

// ── 任务类型 ────────────────────────────────────────────────
export const TASK_TYPE_LABEL: Record<TaskType, string> = {
  label_recognition: "标号识别",
  design_analysis: "设计分析",
  process_check: "工艺校验",
  knowledge_query: "知识问答",
  comprehensive: "综合解析",
};

// ── 图纸类型 / 生命周期 ─────────────────────────────────────
export const DRAWING_TYPE_LABEL: Record<DrawingType, string> = {
  assembly: "装配图",
  part: "零件图",
  process: "工艺图",
  schematic: "原理图",
  patent: "专利附图",
  other: "其他",
};

export const LIFECYCLE_META: Record<LifecycleState, { label: string; tone: Tone }> =
  {
    draft: { label: "草稿", tone: "neutral" },
    released: { label: "已发布", tone: "ok" },
    obsolete: { label: "已废弃", tone: "danger" },
  };

// ── Agent 链路 ──────────────────────────────────────────────
export const AGENT_META: Record<AgentId, { label: string; short: string }> = {
  upload: { label: "上传完成", short: "Upload" },
  preprocess: { label: "预处理", short: "Pre" },
  vision: { label: "Vision Agent", short: "Vision" },
  ocr: { label: "OCR", short: "OCR" },
  knowledge: { label: "Knowledge Agent", short: "Know" },
  conflict: { label: "冲突检测", short: "Conflict" },
  review: { label: "人工复核", short: "Review" },
  report: { label: "Report Agent", short: "Report" },
};

export const AGENT_ORDER: AgentId[] = [
  "upload",
  "preprocess",
  "vision",
  "ocr",
  "knowledge",
  "conflict",
  "review",
  "report",
];

export const STAGE_STATUS_META: Record<
  StageStatus,
  { label: string; tone: Tone }
> = {
  waiting: { label: "等待", tone: "neutral" },
  running: { label: "执行中", tone: "proc" },
  success: { label: "成功", tone: "ok" },
  review: { label: "待复核", tone: "warn" },
  failed: { label: "失败", tone: "danger" },
};

// ── 检索类型 ────────────────────────────────────────────────
export const SEARCH_TYPE_LABEL: Record<SearchType, string> = {
  hybrid: "混合检索",
  vector: "向量",
  keyword: "关键词",
  graph: "知识图谱",
};
