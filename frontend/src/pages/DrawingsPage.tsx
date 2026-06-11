import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileStack } from "lucide-react";
import type { Drawing } from "@/types";
import { DATA_CHANGED, listDrawings } from "@/api/resources";
import { DRAWING_TYPE_LABEL, LIFECYCLE_META } from "@/lib/constants";
import { Tag } from "@/components/common/Tag";
import { fmtBytes, fmtTime } from "@/lib/format";

export function DrawingsPage() {
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const nav = useNavigate();

  useEffect(() => {
    const load = () => listDrawings().then(setDrawings);
    load();
    window.addEventListener(DATA_CHANGED, load);
    return () => window.removeEventListener(DATA_CHANGED, load);
  }, []);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex h-12 shrink-0 items-center gap-3 border-b border-line bg-panel px-4">
        <FileStack className="h-4 w-4 text-industrial" />
        <h1 className="text-base font-semibold text-ink">图纸库</h1>
        <span className="text-xs text-ink-4">{drawings.length} 张图纸</span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        <div className="panel overflow-hidden">
          <table className="w-full border-collapse">
            <thead className="border-b border-line bg-canvas">
              <tr>
                <th className="th">图号</th>
                <th className="th">名称</th>
                <th className="th">类型</th>
                <th className="th">格式</th>
                <th className="th">标号</th>
                <th className="th">来源系统</th>
                <th className="th">状态</th>
                <th className="th">大小</th>
                <th className="th">更新时间</th>
              </tr>
            </thead>
            <tbody>
              {drawings.map((d) => {
                const life = LIFECYCLE_META[d.lifecycle_state];
                return (
                  <tr
                    key={d.id}
                    onClick={() => nav("/")}
                    className="cursor-pointer border-b border-line transition-colors hover:bg-canvas"
                  >
                    <td className="td font-mono text-2xs text-ink-3">{d.id}</td>
                    <td className="td font-medium text-ink">{d.title}</td>
                    <td className="td text-ink-2">{DRAWING_TYPE_LABEL[d.drawing_type]}</td>
                    <td className="td uppercase text-ink-3">{d.file_format}</td>
                    <td className="td font-mono text-2xs text-ink-3">{d.label_count}</td>
                    <td className="td text-ink-3">{d.source_system}</td>
                    <td className="td"><Tag tone={life.tone}>{life.label}</Tag></td>
                    <td className="td font-mono text-2xs text-ink-3">{fmtBytes(d.file_size_bytes)}</td>
                    <td className="td text-2xs text-ink-3">{fmtTime(d.updated_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!drawings.length && (
            <p className="py-12 text-center text-xs text-ink-4">暂无图纸，点击左上「上传图纸」添加</p>
          )}
        </div>
      </div>
    </div>
  );
}
