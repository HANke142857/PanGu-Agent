import { NavLink } from "react-router-dom";
import { Boxes, FileStack, LayoutGrid, ListChecks, Search, UploadCloud } from "lucide-react";
import { cx } from "@/lib/format";
import { useUpload } from "@/components/upload/UploadProvider";

const NAV = [
  { to: "/", label: "工作台", icon: LayoutGrid, end: true },
  { to: "/drawings", label: "图纸库", icon: FileStack },
  { to: "/tasks", label: "任务中心", icon: ListChecks },
  { to: "/knowledge", label: "知识检索", icon: Search },
  { to: "/plm", label: "PLM 回写", icon: Boxes },
];

// 左侧导航：图标 + 文字，工程工具风
export function SideNav() {
  const { open } = useUpload();
  return (
    <nav className="flex w-[180px] shrink-0 flex-col border-r border-line bg-panel">
      <div className="p-2">
        <button className="btn btn-primary w-full justify-center" onClick={open}>
          <UploadCloud className="h-4 w-4" />
          上传图纸
        </button>
      </div>
      <div className="flex flex-col gap-0.5 px-2">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            className={({ isActive }) =>
              cx(
                "flex h-9 items-center gap-2.5 rounded-md px-2.5 text-sm font-medium transition-colors",
                isActive ? "bg-industrial-50 text-industrial-600" : "text-ink-2 hover:bg-canvas",
              )
            }
          >
            <n.icon className="h-4 w-4" />
            {n.label}
          </NavLink>
        ))}
      </div>

      <div className="mt-auto border-t border-line p-3">
        <div className="mb-1.5 text-2xs font-semibold uppercase tracking-wide text-ink-4">系统状态</div>
        <div className="space-y-1 text-2xs text-ink-3">
          <Row label="Vision Agent" ok />
          <Row label="Knowledge Agent" ok />
          <Row label="PLM 连接器" ok />
          <Row label="向量库" ok />
        </div>
      </div>
    </nav>
  );
}

function Row({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span>{label}</span>
      <span className={cx("h-1.5 w-1.5 rounded-full", ok ? "bg-ok" : "bg-danger")} />
    </div>
  );
}
