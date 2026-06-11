import { useState } from "react";
import {
  AlertTriangle,
  Check,
  FileText,
  Pencil,
  ScrollText,
  Tags,
  X,
} from "lucide-react";
import type { ConflictInfo, Label, ReviewAction } from "@/types";
import { Tag } from "@/components/common/Tag";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import { cx, fmtPct } from "@/lib/format";

type TabKey = "labels" | "conflicts" | "knowledge" | "report";

interface Props {
  labels: Label[];
  conflicts: ConflictInfo[];
  reviews: Record<string, ReviewAction>;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onReview: (id: string, action: ReviewAction) => void;
}

export function ResultsPanel({
  labels,
  conflicts,
  reviews,
  selectedId,
  onSelect,
  onReview,
}: Props) {
  const [tab, setTab] = useState<TabKey>("labels");
  const reviewedCount = Object.keys(reviews).length;
  const needReview = labels.filter((l) => l.needs_review).length;

  const tabs: { key: TabKey; label: string; icon: typeof Tags; badge?: number }[] =
    [
      { key: "labels", label: "识别结果", icon: Tags, badge: labels.length },
      {
        key: "conflicts",
        label: "冲突检测",
        icon: AlertTriangle,
        badge: conflicts.length,
      },
      { key: "knowledge", label: "知识引用", icon: ScrollText },
      { key: "report", label: "报告", icon: FileText },
    ];

  return (
    <div className="flex h-full flex-col">
      {/* Tabs */}
      <div className="flex h-10 shrink-0 items-stretch border-b border-line bg-panel">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cx(
              "relative flex items-center gap-1.5 px-3 text-xs font-medium transition-colors",
              tab === t.key
                ? "text-industrial-600"
                : "text-ink-3 hover:text-ink-2",
            )}
          >
            <t.icon className="h-3.5 w-3.5" />
            {t.label}
            {t.badge != null && t.badge > 0 && (
              <span
                className={cx(
                  "rounded px-1 text-[10px] font-semibold tabular-nums",
                  t.key === "conflicts"
                    ? "bg-danger-50 text-danger"
                    : "bg-canvas text-ink-3",
                )}
              >
                {t.badge}
              </span>
            )}
            {tab === t.key && (
              <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-industrial" />
            )}
          </button>
        ))}
      </div>

      {/* 复核进度条 */}
      {tab === "labels" && (
        <div className="flex shrink-0 items-center gap-2 border-b border-line bg-canvas px-3 py-1.5 text-2xs text-ink-3">
          <span>
            复核进度{" "}
            <span className="font-mono font-semibold text-ink-2">
              {reviewedCount}/{labels.length}
            </span>
          </span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
            <div
              className="h-full rounded-full bg-industrial transition-all"
              style={{
                width: `${labels.length ? (reviewedCount / labels.length) * 100 : 0}%`,
              }}
            />
          </div>
          {needReview > 0 && (
            <Tag tone="warn" dot>
              {needReview} 待复核
            </Tag>
          )}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {tab === "labels" && (
          <LabelList
            labels={labels}
            reviews={reviews}
            selectedId={selectedId}
            onSelect={onSelect}
            onReview={onReview}
          />
        )}
        {tab === "conflicts" && <ConflictList conflicts={conflicts} onSelect={onSelect} />}
        {tab === "knowledge" && <KnowledgeRefs />}
        {tab === "report" && <ReportTab labels={labels} reviews={reviews} />}
      </div>
    </div>
  );
}

// ── 标号列表 ────────────────────────────────────────────────
function LabelList({
  labels,
  reviews,
  selectedId,
  onSelect,
  onReview,
}: Omit<Props, "conflicts">) {
  if (!labels.length)
    return <Empty text="该图纸尚无识别结果，请先发起解析任务。" />;
  return (
    <ul className="divide-y divide-line">
      {labels.map((l) => {
        const active = l.label_id === selectedId;
        const decided = reviews[l.label_id];
        return (
          <li
            key={l.label_id}
            onClick={() => onSelect(l.label_id)}
            className={cx(
              "cursor-pointer px-3 py-2.5 transition-colors",
              active ? "bg-industrial-50" : "hover:bg-canvas",
            )}
          >
            <div className="flex items-start gap-2">
              <span
                className={cx(
                  "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded font-mono text-2xs font-bold",
                  l.has_conflict
                    ? "bg-danger text-white"
                    : l.needs_review
                      ? "bg-warn text-white"
                      : "bg-industrial text-white",
                )}
              >
                {l.label_id}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-sm font-medium text-ink">
                    {l.name}
                  </span>
                  {l.has_conflict && (
                    <Tag tone="danger">冲突</Tag>
                  )}
                </div>
                <div className="mt-0.5 truncate text-2xs text-ink-4">
                  {l.spatial_description ?? "—"}
                </div>
                <div className="mt-1.5 flex items-center justify-between">
                  <ConfidenceBadge value={l.confidence} />
                  {decided ? (
                    <DecisionTag action={decided} />
                  ) : (
                    <div className="flex items-center gap-1">
                      <ReviewBtn
                        title="确认"
                        tone="ok"
                        onClick={(e) => {
                          e.stopPropagation();
                          onReview(l.label_id, "confirm");
                        }}
                      >
                        <Check className="h-3.5 w-3.5" />
                      </ReviewBtn>
                      <ReviewBtn
                        title="修正"
                        tone="industrial"
                        onClick={(e) => {
                          e.stopPropagation();
                          onReview(l.label_id, "correct");
                        }}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </ReviewBtn>
                      <ReviewBtn
                        title="拒绝"
                        tone="danger"
                        onClick={(e) => {
                          e.stopPropagation();
                          onReview(l.label_id, "reject");
                        }}
                      >
                        <X className="h-3.5 w-3.5" />
                      </ReviewBtn>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function ReviewBtn({
  children,
  title,
  tone,
  onClick,
}: {
  children: React.ReactNode;
  title: string;
  tone: "ok" | "industrial" | "danger";
  onClick: (e: React.MouseEvent) => void;
}) {
  const styles = {
    ok: "hover:bg-ok-50 hover:text-ok hover:border-ok/40",
    industrial: "hover:bg-industrial-50 hover:text-industrial hover:border-industrial/40",
    danger: "hover:bg-danger-50 hover:text-danger hover:border-danger/40",
  }[tone];
  return (
    <button
      title={title}
      onClick={onClick}
      className={cx(
        "flex h-6 w-6 items-center justify-center rounded border border-line text-ink-3 transition-colors",
        styles,
      )}
    >
      {children}
    </button>
  );
}

function DecisionTag({ action }: { action: ReviewAction }) {
  const meta = {
    confirm: { tone: "ok" as const, label: "已确认" },
    correct: { tone: "industrial" as const, label: "已修正" },
    reject: { tone: "danger" as const, label: "已拒绝" },
  }[action];
  return (
    <Tag tone={meta.tone} dot>
      {meta.label}
    </Tag>
  );
}

// ── 冲突检测 ────────────────────────────────────────────────
function ConflictList({
  conflicts,
  onSelect,
}: {
  conflicts: ConflictInfo[];
  onSelect: (id: string) => void;
}) {
  if (!conflicts.length)
    return <Empty text="未检测到 Vision 与 Knowledge Agent 的冲突。" />;
  return (
    <div className="space-y-2 p-3">
      {conflicts.map((c) => (
        <div
          key={c.label_id}
          className="rounded-lg border border-danger/30 bg-danger-50/40 p-3"
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-danger" />
            <span className="text-sm font-semibold text-ink">
              标号 {c.label_id} 判定冲突
            </span>
            <button
              className="ml-auto text-2xs text-industrial-600 hover:underline"
              onClick={() => onSelect(c.label_id)}
            >
              定位
            </button>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <Side
              tag="Vision"
              name={c.vision_name}
              conf={c.vision_confidence}
            />
            <Side
              tag="Knowledge"
              name={c.knowledge_name}
              conf={c.knowledge_confidence}
            />
          </div>
          <div className="mt-2 rounded border border-line bg-panel px-2 py-1.5 text-2xs text-ink-3">
            {c.resolution
              ? `裁决：${c.resolution}`
              : "待对抗辩论裁决 / 人工复核确认。"}
          </div>
        </div>
      ))}
    </div>
  );
}

function Side({
  tag,
  name,
  conf,
}: {
  tag: string;
  name: string;
  conf: number;
}) {
  return (
    <div className="rounded border border-line bg-panel p-2">
      <div className="text-2xs font-semibold uppercase tracking-wide text-ink-4">
        {tag}
      </div>
      <div className="mt-0.5 text-sm font-medium text-ink">{name}</div>
      <div className="mt-0.5 font-mono text-2xs text-ink-3">
        置信度 {fmtPct(conf)}
      </div>
    </div>
  );
}

// ── 知识引用 ────────────────────────────────────────────────
function KnowledgeRefs() {
  const refs = [
    {
      id: "GB/T 276-2013",
      title: "深沟球轴承 6208 外形尺寸",
      note: "支撑标号 3 命名依据",
    },
    {
      id: "QY-WI-0312",
      title: "箱体油封装配工艺规范",
      note: "支撑标号 6 命名依据",
    },
    {
      id: "KG-NODE-2291",
      title: "调整垫片 ↔ 止推垫圈 术语关系",
      note: "标号 8 冲突消歧参考",
    },
  ];
  return (
    <div className="space-y-2 p-3">
      {refs.map((r) => (
        <div key={r.id} className="rounded-lg border border-line bg-panel p-2.5">
          <div className="flex items-center gap-1.5">
            <ScrollText className="h-3.5 w-3.5 text-industrial" />
            <span className="font-mono text-2xs text-industrial-600">
              {r.id}
            </span>
          </div>
          <div className="mt-1 text-sm font-medium text-ink">{r.title}</div>
          <div className="mt-0.5 text-2xs text-ink-4">{r.note}</div>
        </div>
      ))}
    </div>
  );
}

// ── 报告 ────────────────────────────────────────────────────
function ReportTab({
  labels,
  reviews,
}: {
  labels: Label[];
  reviews: Record<string, ReviewAction>;
}) {
  const high = labels.filter((l) => l.confidence >= 0.85).length;
  const low = labels.filter((l) => l.confidence < 0.6).length;
  return (
    <div className="space-y-3 p-3">
      <div className="grid grid-cols-2 gap-2">
        <Stat label="标号总数" value={labels.length} />
        <Stat label="已复核" value={Object.keys(reviews).length} />
        <Stat label="高置信" value={high} tone="text-ok" />
        <Stat label="低置信" value={low} tone="text-warn" />
      </div>
      <div className="rounded-lg border border-line bg-panel p-3 text-sm leading-relaxed text-ink-2">
        本次解析共识别 {labels.length} 个标号，其中 {high} 个为高置信结果，
        {low} 个低于复核阈值需人工确认。冲突标号经知识图谱消歧后建议进入对抗辩论流程。复核完成后可一键生成结构化报告并回写 PLM。
      </div>
      <button className="btn btn-primary w-full justify-center">
        生成解析报告
      </button>
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "text-ink",
}: {
  label: string;
  value: number;
  tone?: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-panel p-2.5">
      <div className="text-2xs text-ink-4">{label}</div>
      <div className={cx("mt-0.5 font-mono text-xl font-semibold", tone)}>
        {value}
      </div>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
      <Tags className="h-8 w-8 text-ink-4" />
      <p className="max-w-[200px] text-xs text-ink-4">{text}</p>
    </div>
  );
}
