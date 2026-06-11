import { Bell, Moon, Search, Settings, Sun } from "lucide-react";
import { Tag } from "@/components/common/Tag";
import { useTheme } from "@/lib/useTheme";

// 顶栏：品牌 / 全局搜索 / 当前任务态 / 主题切换 / 用户
export function TopBar() {
  const { theme, toggle } = useTheme();
  return (
    <header className="relative z-20 flex h-12 shrink-0 items-center gap-4 border-b border-line bg-panel px-4">
      <div className="topbar-sheen pointer-events-none absolute inset-x-0 bottom-0 h-px opacity-70" />

      <div className="flex items-center gap-2">
        <div className="brand-cube flex h-6 w-6 items-center justify-center rounded font-bold text-white">
          <span className="text-2xs tracking-tight">ID</span>
        </div>
        <span className="text-base font-semibold tracking-tight text-ink">IDMAS</span>
        <span className="hidden text-xs text-ink-4 sm:inline">工业图纸智能解析系统</span>
      </div>

      <div className="relative ml-2 hidden max-w-md flex-1 md:block">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-4" />
        <input
          className="h-8 w-full rounded-md border border-line bg-canvas pl-8 pr-3 text-sm text-ink placeholder:text-ink-4 focus:border-industrial focus:bg-panel focus:outline-none focus:ring-2 focus:ring-industrial/25"
          placeholder="搜索图纸编号 / 标号 / 任务 ID…"
        />
      </div>

      <div className="ml-auto flex items-center gap-3">
        <div className="hidden items-center gap-2 lg:flex">
          <span className="text-2xs text-ink-4">当前队列</span>
          <Tag tone="proc" dot>1 处理中</Tag>
          <Tag tone="warn" dot>1 待复核</Tag>
        </div>
        <button className="btn-icon" title={theme === "dark" ? "切换浅色" : "切换深色"} onClick={toggle}>
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
        <button className="btn-icon" title="通知"><Bell className="h-4 w-4" /></button>
        <button className="btn-icon" title="设置"><Settings className="h-4 w-4" /></button>
        <div className="flex items-center gap-2 border-l border-line pl-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-industrial text-2xs font-semibold text-white">KZ</div>
          <div className="hidden leading-tight sm:block">
            <div className="text-xs font-medium text-ink-2">康工</div>
            <div className="text-2xs text-ink-4">机械设计 · 复核员</div>
          </div>
        </div>
      </div>
    </header>
  );
}
