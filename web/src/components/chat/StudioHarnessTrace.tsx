import type { HarnessTrace } from "@/lib/harnessTrace";

const ROLE_LABEL: Record<string, string> = {
  memory: "记忆脑",
  router: "深度路由",
  analyzer: "分析脑",
  planner: "规划脑",
  generator: "生成脑",
  critic: "质检脑",
  refiner: "精炼脑",
};

const STRATEGY_LABEL: Record<string, string> = {
  direct: "直答（1 跳）",
  guided: "引导生成（2 跳）",
  decompose: "拆解协作（3+ 跳）",
};

export function StudioHarnessTrace({ trace }: { trace: HarnessTrace }) {
  if (!trace?.passes?.length) return null;

  return (
    <details className="mimo-studio-harness mt-2 text-xs text-mimo-muted">
      <summary className="cursor-pointer select-none hover:text-mimo-text">
        Chat Harness · {STRATEGY_LABEL[trace.strategy] ?? trace.strategy}
        {trace.complexity_score != null ? ` · 复杂度 ${trace.complexity_score}` : ""}
      </summary>
      <ol className="mt-2 space-y-1.5 border-l border-mimo-border pl-3">
        {trace.passes.map((p, i) => (
          <li key={`${p.role}-${i}`}>
            <span className="font-medium text-mimo-text">{ROLE_LABEL[p.role] ?? p.role}</span>
            <span className="text-mimo-muted"> · {p.model}</span>
            <div>{p.summary}</div>
          </li>
        ))}
      </ol>
    </details>
  );
}
