// ─────────────────────────────────────────────────────────────
// IDMAS API 客户端 —— 薄封装 fetch，统一 baseURL / 错误处理
// 通过 VITE_USE_MOCK=false 切换到真实后端；默认走 mock（离线可预览）
// ─────────────────────────────────────────────────────────────

export const API_BASE = "/api/v1";

export const USE_MOCK =
  (import.meta.env.VITE_USE_MOCK ?? "true").toString() !== "false";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let code: string | undefined;
    let msg = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      // 后端统一错误结构：{ error: { code, message, detail?, request_id } }
      const e = body.error ?? body;
      code = e.code ?? e.error_code;
      msg = e.detail ?? e.message ?? e.error_message ?? msg;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, msg, code);
  }
  return res.json() as Promise<T>;
}

export const http = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "POST", body: JSON.stringify(body ?? {}) }),
  put: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  del: <T>(p: string) => request<T>(p, { method: "DELETE" }),
};

// 任务流式进度（SSE）预留 —— 真实后端返回 stream_url
export function openTaskStream(
  streamUrl: string,
  onEvent: (data: unknown) => void,
): () => void {
  const es = new EventSource(streamUrl);
  es.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data));
    } catch {
      /* ignore */
    }
  };
  return () => es.close();
}
