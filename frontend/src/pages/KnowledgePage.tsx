import { useEffect, useState } from "react";
import { Boxes, Network, Search, Tag as TagIcon } from "lucide-react";
import type { KnowledgeResult, SearchType } from "@/types";
import { searchKnowledge } from "@/api/resources";
import { SEARCH_TYPE_LABEL } from "@/lib/constants";
import { Tag } from "@/components/common/Tag";
import { cx, fmtPct } from "@/lib/format";

const SOURCE_META: Record<
  KnowledgeResult["source"],
  { label: string; tone: "industrial" | "ok" | "warn"; Icon: typeof Network }
> = {
  vector: { label: "向量", tone: "industrial", Icon: Boxes },
  keyword: { label: "关键词", tone: "ok", Icon: TagIcon },
  graph: { label: "图谱", tone: "warn", Icon: Network },
};

const TYPES: SearchType[] = ["hybrid", "vector", "keyword", "graph"];

export function KnowledgePage() {
  const [query, setQuery] = useState("减速机 轴承");
  const [type, setType] = useState<SearchType>("hybrid");
  const [results, setResults] = useState<KnowledgeResult[]>([]);
  const [loading, setLoading] = useState(false);

  const run = async (q = query, t = type) => {
    setLoading(true);
    const r = await searchKnowledge(q, t);
    setResults(r);
    setLoading(false);
  };

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex h-12 shrink-0 items-center gap-3 border-b border-line bg-panel px-4">
        <h1 className="text-base font-semibold text-ink">知识检索</h1>
        <span className="text-xs text-ink-4">
          向量 / 关键词 / 知识图谱混合检索
        </span>
      </div>

      <div className="border-b border-line bg-panel px-4 py-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            run();
          }}
          className="flex items-center gap-2"
        >
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-4" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="h-9 w-full rounded-md border border-line bg-canvas pl-9 pr-3 text-sm text-ink placeholder:text-ink-4 focus:border-industrial focus:bg-panel focus:outline-none focus:ring-2 focus:ring-industrial/20"
              placeholder="检索标准、工艺规范、术语、BOM…"
            />
          </div>
          <button type="submit" className="btn btn-primary">
            检索
          </button>
        </form>
        <div className="mt-2.5 flex items-center gap-1">
          {TYPES.map((t) => (
            <button
              key={t}
              onClick={() => {
                setType(t);
                run(query, t);
              }}
              className={cx(
                "h-7 rounded-md px-3 text-xs font-medium transition-colors",
                type === t
                  ? "bg-industrial-50 text-industrial-600"
                  : "text-ink-3 hover:bg-canvas",
              )}
            >
              {SEARCH_TYPE_LABEL[t]}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        <div className="mb-2 text-2xs text-ink-4">
          {loading
            ? "检索中…"
            : `命中 ${results.length} 条 · ${SEARCH_TYPE_LABEL[type]}`}
        </div>
        <div className="space-y-2">
          {results.map((r) => {
            const s = SOURCE_META[r.source];
            return (
              <article
                key={r.doc_id}
                className="panel p-3.5 transition-shadow hover:shadow-pop"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-2xs text-industrial-600">
                    {r.doc_id}
                  </span>
                  <Tag tone={s.tone}>
                    <s.Icon className="h-3 w-3" />
                    {s.label}
                  </Tag>
                  <span className="ml-auto flex items-center gap-1.5">
                    <span className="text-2xs text-ink-4">相关度</span>
                    <span className="h-1.5 w-16 overflow-hidden rounded-full bg-line">
                      <span
                        className="block h-full rounded-full bg-industrial"
                        style={{ width: `${r.score * 100}%` }}
                      />
                    </span>
                    <span className="font-mono text-2xs tabular-nums text-ink-2">
                      {fmtPct(r.score)}
                    </span>
                  </span>
                </div>
                <h3 className="mt-1.5 text-sm font-semibold text-ink">
                  {r.title}
                </h3>
                <p className="mt-1 text-sm leading-relaxed text-ink-3">
                  {r.content}
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {r.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded bg-canvas px-1.5 py-0.5 text-2xs text-ink-3"
                    >
                      #{t}
                    </span>
                  ))}
                </div>
              </article>
            );
          })}
          {!loading && !results.length && (
            <div className="flex flex-col items-center gap-2 py-12 text-ink-4">
              <Search className="h-8 w-8" />
              <p className="text-xs">未命中结果，换个关键词或检索类型试试</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
