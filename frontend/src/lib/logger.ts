// ─────────────────────────────────────────────────────────────
// 前端日志回收：捕获浏览器运行时错误/警告，批量回传后端落盘 logs/frontend.log
// 失败静默（后端不可达时不影响页面）。USE_MOCK 时不回传。
// ─────────────────────────────────────────────────────────────
import { API_BASE, USE_MOCK } from "@/api/client";

type Level = "debug" | "info" | "warn" | "error";

interface Entry {
  level: Level;
  message: string;
  url: string;
  stack?: string;
  ts: string;
}

const buffer: Entry[] = [];
let installed = false;

function flush() {
  if (!buffer.length) return;
  const entries = buffer.splice(0, buffer.length);
  try {
    fetch(`${API_BASE}/client-logs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entries }),
      keepalive: true,
    }).catch(() => {
      /* 后端不可达：丢弃，不阻塞页面 */
    });
  } catch {
    /* ignore */
  }
}

function push(level: Level, message: string, stack?: string) {
  buffer.push({
    level,
    message: message.slice(0, 4000),
    url: location.href,
    stack: stack?.slice(0, 8000),
    ts: new Date().toISOString(),
  });
  if (buffer.length >= 20) flush();
}

function fmt(args: unknown[]): string {
  return args
    .map((a) => {
      if (a instanceof Error) return `${a.name}: ${a.message}`;
      if (typeof a === "object") {
        try {
          return JSON.stringify(a);
        } catch {
          return String(a);
        }
      }
      return String(a);
    })
    .join(" ");
}

export function installLogger() {
  if (installed || USE_MOCK) return;
  installed = true;

  window.addEventListener("error", (e) => {
    push("error", e.message || "window error", (e.error as Error | undefined)?.stack);
  });
  window.addEventListener("unhandledrejection", (e) => {
    const r = e.reason;
    push(
      "error",
      `未处理的 Promise 拒绝: ${r instanceof Error ? r.message : String(r)}`,
      r instanceof Error ? r.stack : undefined,
    );
  });

  const origError = console.error.bind(console);
  console.error = (...args: unknown[]) => {
    push("error", fmt(args));
    origError(...args);
  };
  const origWarn = console.warn.bind(console);
  console.warn = (...args: unknown[]) => {
    push("warn", fmt(args));
    origWarn(...args);
  };

  setInterval(flush, 5000);
  window.addEventListener("beforeunload", flush);
}
