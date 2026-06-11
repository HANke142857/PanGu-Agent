import { Filter, Search } from "lucide-react";
import { useState } from "react";
import type { Drawing } from "@/types";
import { DRAWING_TYPE_LABEL, LIFECYCLE_META } from "@/lib/constants";
import { Tag } from "@/components/common/Tag";
import { cx, relTime } from "@/lib/format";

interface Props {
  drawings: Drawing[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

// 左侧图纸库：紧凑列表，状态/类型标签
export function DrawingLibrary({ drawings, selectedId, onSelect }: Props) {
  const [q, setQ] = useState("");
  const filtered = drawings.filter(
    (d) => !q || d.title.includes(q) || d.id.includes(q),
  );

  return (
    <div className="flex h-full flex-col">
      <div className="panel-title">
        图纸库
        <span className="font-mono text-2xs font-normal text-ink-4">
          {filtered.length}
        </span>
      </div>
      <div className="flex items-center gap-1.5 border-b border-line p-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-4" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="h-7 w-full rounded-md border border-line bg-canvas pl-7 pr-2 text-xs text-ink placeholder:text-ink-4 focus:border-industrial focus:bg-panel focus:outline-none"
            placeholder="图号 / 名称"
          />
        </div>
        <button className="btn-icon h-7 w-7" title="筛选">
          <Filter className="h-3.5 w-3.5" />
        </button>
      </div>

      <ul className="min-h-0 flex-1 overflow-y-auto">
        {filtered.map((d) => {
          const active = d.id === selectedId;
          const life = LIFECYCLE_META[d.lifecycle_state];
          return (
            <li
              key={d.id}
              onClick={() => onSelect(d.id)}
              className={cx(
                "cursor-pointer border-b border-line px-3 py-2.5 transition-colors",
                active
                  ? "bg-industrial-50 shadow-[inset_2px_0_0_0_#2563EB]"
                  : "hover:bg-canvas",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-2xs text-ink-4">{d.id}</span>
                <Tag tone={life.tone}>{life.label}</Tag>
              </div>
              <div className="mt-0.5 truncate text-sm font-medium text-ink">
                {d.title}
              </div>
              <div className="mt-1 flex items-center gap-2 text-2xs text-ink-4">
                <span className="rounded bg-canvas px-1 py-px text-ink-3">
                  {DRAWING_TYPE_LABEL[d.drawing_type]}
                </span>
                <span className="uppercase">{d.file_format}</span>
                {d.label_count > 0 && <span>· {d.label_count} 标号</span>}
                <span className="ml-auto">{relTime(d.updated_at)}</span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
