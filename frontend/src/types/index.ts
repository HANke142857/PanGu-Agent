// ─────────────────────────────────────────────────────────────
// IDMAS 前端类型定义 —— 镜像后端 idmas/api/schemas 与领域值对象
// ─────────────────────────────────────────────────────────────

// 图纸
export type DrawingType =
  | "assembly" // 装配图
  | "part" // 零件图
  | "process" // 工艺图
  | "schematic" // 原理图/电路图
  | "patent" // 专利附图
  | "other";

export type FileFormat = "png" | "jpg" | "pdf" | "dwg" | "dxf";

export type LifecycleState = "draft" | "released" | "obsolete";

export type Quadrant =
  | "top_left"
  | "top_right"
  | "bottom_left"
  | "bottom_right"
  | "center";

// 标号识别结果
export interface BoundingBox {
  // 归一化坐标 0~1
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Label {
  label_id: string;
  name: string;
  confidence: number; // 0~1
  needs_review: boolean;
  spatial_description?: string | null;
  quadrant?: Quadrant | null;
  bounding_box?: BoundingBox | null;
  // 复核态（前端本地）
  review?: ReviewAction | null;
  has_conflict?: boolean;
}

export interface Drawing {
  id: string;
  title: string;
  drawing_type: DrawingType;
  file_format: FileFormat;
  file_url: string;
  file_size_bytes: number;
  lifecycle_state: LifecycleState;
  source_system: string;
  labels: Label[];
  label_count: number;
  created_at: string;
  updated_at: string;
}

// 任务
export type TaskType =
  | "label_recognition"
  | "design_analysis"
  | "process_check"
  | "knowledge_query"
  | "comprehensive";

export type TaskStatus =
  | "created"
  | "processing"
  | "waiting_review"
  | "completed"
  | "failed";

export type PromptMode = "standard_visual" | "cot_visual" | "few_shot_visual";

export type ReviewAction = "confirm" | "correct" | "reject";

export interface ConflictInfo {
  label_id: string;
  vision_name: string;
  knowledge_name: string;
  vision_confidence: number;
  knowledge_confidence: number;
  resolution?: string | null;
}

export interface Task {
  id: string;
  status: TaskStatus;
  drawing_id: string;
  drawing_title: string;
  task_type: TaskType;
  prompt_mode: PromptMode;
  question: string;
  conflicts: ConflictInfo[];
  human_decision?: string | null;
  inference_time_ms?: number | null;
  total_tokens: number;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  // 前端展示：Agent 执行链路
  pipeline: PipelineStage[];
}

// Agent 执行链路（pipeline）
export type AgentId =
  | "upload"
  | "preprocess"
  | "vision"
  | "ocr"
  | "knowledge"
  | "conflict"
  | "review"
  | "report";

export type StageStatus =
  | "waiting" // 等待：灰
  | "running" // 执行中：蓝
  | "success" // 成功：绿
  | "review" // 待复核：黄
  | "failed"; // 失败：红

export interface PipelineStage {
  agent: AgentId;
  status: StageStatus;
  duration_ms?: number | null;
  detail?: string;
}

// 知识检索
export type SearchType = "vector" | "keyword" | "graph" | "hybrid";

export interface KnowledgeResult {
  doc_id: string;
  title: string;
  content: string;
  score: number;
  source: "vector" | "keyword" | "graph";
  tags: string[];
}

// PLM 回写
export type PLMSystem = "teamcenter" | "enovia" | "inteplm";

export interface PLMWritebackResult {
  success: boolean;
  doc_id: string;
  target_system: PLMSystem;
  skipped: boolean;
  message: string;
}
