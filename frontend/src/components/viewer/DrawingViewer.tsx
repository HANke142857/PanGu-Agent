import { useRef, useState } from "react";
import { Eye, EyeOff, Maximize2, Minus, Plus, RotateCcw, ScanLine } from "lucide-react";
import type { Label } from "@/types";
import { confLevel } from "@/lib/constants";
import { cx } from "@/lib/format";
import { DrawingArtwork } from "./DrawingArtwork";

// 标注框配色：高=蓝，低=琥珀，冲突=红，选中=加粗外环
function boxColor(label: Label): { border: string; tag: string } {
  if (label.has_conflict) return { border: "border-danger", tag: "bg-danger text-white" };
  const lvl = confLevel(label.confidence);
  if (lvl === "low") return { border: "border-warn", tag: "bg-warn text-white" };
  return { border: "border-industrial", tag: "bg-industrial text-white" };
}

interface Props {
  title: string;
  labels: Label[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function DrawingViewer({ title, labels, selectedId, onSelect }: Props) {
  const [zoom, setZoom] = useState(1);
  const [showLabels, setShowLabels] = useState(true);
  const [onlyReview, setOnlyReview] = useState(false);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);

  const visible = labels.filter((l) => (onlyReview ? l.needs_review : true));

  const clampZoom = (z: number) => Math.min(3, Math.max(0.4, z));
  const reset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const onWheel = (e: React.WheelEvent) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    setZoom((z) => clampZoom(z - e.deltaY * 0.0015));
  };

  return (
    <div className="flex h-full flex-col">
      {/* 工具栏 */}
      <div className="flex h-10 shrink-0 items-center gap-2 border-b border-line bg-panel px-2.5">
        <span className="truncate text-sm font-semibold text-ink-2">{title}</span>
        <span className="rounded bg-canvas px-1.5 py-0.5 font-mono text-2xs text-ink-3">
          {visible.length}/{labels.length} 标号
        </span>

        <div className="ml-auto flex items-center gap-1">
          <button
            className={cx("btn-icon", onlyReview && "bg-warn-50 text-warn")}
            title="只看待复核标号"
            onClick={() => setOnlyReview((v) => !v)}
          >
            <ScanLine className="h-4 w-4" />
          </button>
          <button
            className="btn-icon"
            title={showLabels ? "隐藏标注" : "显示标注"}
            onClick={() => setShowLabels((v) => !v)}
          >
            {showLabels ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
          </button>
          <div className="mx-1 h-5 w-px bg-line" />
          <button className="btn-icon" title="缩小" onClick={() => setZoom((z) => clampZoom(z - 0.2))}>
            <Minus className="h-4 w-4" />
          </button>
          <span className="w-12 text-center font-mono text-2xs text-ink-3">{Math.round(zoom * 100)}%</span>
          <button className="btn-icon" title="放大" onClick={() => setZoom((z) => clampZoom(z + 0.2))}>
            <Plus className="h-4 w-4" />
          </button>
          <button className="btn-icon" title="适应屏幕" onClick={reset}>
            <Maximize2 className="h-4 w-4" />
          </button>
          <button className="btn-icon" title="重置视图" onClick={reset}>
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* 画布 */}
      <div
        className="cad-grid relative min-h-0 flex-1 cursor-grab overflow-hidden active:cursor-grabbing"
        onWheel={onWheel}
        onMouseDown={(e) => {
          drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
        }}
        onMouseMove={(e) => {
          if (!drag.current) return;
          setPan({
            x: drag.current.px + (e.clientX - drag.current.x),
            y: drag.current.py + (e.clientY - drag.current.y),
          });
        }}
        onMouseUp={() => (drag.current = null)}
        onMouseLeave={() => (drag.current = null)}
      >
        <div
          className="absolute inset-0 flex items-center justify-center"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "center center",
            transition: drag.current ? "none" : "transform 120ms ease-out",
          }}
        >
          <div className="relative aspect-[10/7] w-[78%] bg-white shadow-pop">
            <DrawingArtwork />

            {showLabels &&
              visible.map((l) => {
                if (!l.bounding_box) return null;
                const b = l.bounding_box;
                const c = boxColor(l);
                const active = l.label_id === selectedId;
                return (
                  <button
                    key={l.label_id}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect(l.label_id);
                    }}
                    className={cx(
                      "group absolute border-[1.5px] bg-transparent transition-all",
                      c.border,
                      active ? "glow-ring z-10 ring-2 ring-offset-1 ring-current" : "hover:bg-current/5",
                    )}
                    style={{
                      left: `${b.x * 100}%`,
                      top: `${b.y * 100}%`,
                      width: `${b.w * 100}%`,
                      height: `${b.h * 100}%`,
                      borderWidth: active ? 2.5 : 1.5,
                    }}
                  >
                    <span
                      className={cx(
                        "absolute -top-[18px] left-0 flex items-center gap-1 whitespace-nowrap rounded-sm px-1 py-px font-mono text-[10px] leading-none shadow-sm",
                        c.tag,
                      )}
                    >
                      {l.label_id} | {l.confidence.toFixed(2)}
                    </span>
                  </button>
                );
              })}
          </div>
        </div>

        {/* 图例 */}
        <div className="glass pointer-events-none absolute bottom-2 left-2 flex gap-3 rounded-md border border-line px-2.5 py-1.5 text-2xs text-ink-3">
          <Legend color="bg-industrial" label="高置信" />
          <Legend color="bg-warn" label="低置信/待复核" />
          <Legend color="bg-danger" label="冲突" />
        </div>
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1">
      <span className={cx("h-2 w-2.5 rounded-sm", color)} />
      {label}
    </span>
  );
}
