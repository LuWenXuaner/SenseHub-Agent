import { useMemo } from "react";
import type { TokenUsageDailyRow, TokenUsageModelRow } from "@/lib/api";

function formatDayLabel(day: string) {
  const parts = day.split("-");
  if (parts.length < 3) return day;
  return `${parts[1]}/${parts[2]}`;
}

function formatCompact(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 10_000) return `${(n / 1_000).toFixed(0)}k`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toLocaleString();
}

type BarChartProps = {
  daily: TokenUsageDailyRow[];
  valueKey: "total_tokens" | "request_count";
  variant: "token" | "request";
  unit: string;
  emptyLabel: string;
};

function UsageBarChart({ daily, valueKey, variant, unit, emptyLabel }: BarChartProps) {
  if (!daily.length) {
    return <p className="mimo-token-chart-empty">{emptyLabel}</p>;
  }

  const max = Math.max(1, ...daily.map((d) => d[valueKey]));
  const labelEvery = daily.length > 12 ? Math.ceil(daily.length / 8) : 1;

  return (
    <div className={`mimo-usage-bars mimo-usage-bars-${variant}`} data-count={daily.length}>
      {daily.map((row, index) => {
        const value = row[valueKey];
        const isZero = value === 0;
        const pct = isZero ? 0 : (value / max) * 100;
        const showLabel = index % labelEvery === 0 || index === daily.length - 1;
        return (
          <div
            key={row.day}
            className={`mimo-usage-bar-item${isZero ? " mimo-usage-bar-item-zero" : ""}`}
            title={`${row.day}: ${value.toLocaleString()} ${unit}`}
          >
            <span className={`mimo-usage-bar-value${isZero ? " mimo-usage-bar-value-zero" : ""}`}>
              {isZero ? "—" : formatCompact(value)}
            </span>
            <div className={`mimo-usage-bar-track${isZero ? " mimo-usage-bar-track-zero" : ""}`}>
              {!isZero ? (
                <div className="mimo-usage-bar-fill" style={{ height: `${Math.max(pct, 12)}%` }} />
              ) : (
                <div className="mimo-usage-bar-zero-mark" />
              )}
            </div>
            {showLabel ? <span className="mimo-usage-bar-label">{formatDayLabel(row.day)}</span> : <span className="mimo-usage-bar-label" aria-hidden>&nbsp;</span>}
          </div>
        );
      })}
    </div>
  );
}

function PromptCompletionCards({
  promptTokens,
  completionTokens,
}: {
  promptTokens: number;
  completionTokens: number;
}) {
  const total = promptTokens + completionTokens;
  if (total <= 0) return null;
  const promptPct = Math.round((promptTokens / total) * 100);
  const completionPct = 100 - promptPct;

  return (
    <div className="mimo-usage-metric-grid">
      <div className="mimo-usage-metric-card mimo-usage-metric-prompt">
        <span className="mimo-usage-metric-label">Prompt</span>
        <span className="mimo-usage-metric-value">{promptTokens.toLocaleString()}</span>
        <span className="mimo-usage-metric-pct">{promptPct}%</span>
      </div>
      <div className="mimo-usage-metric-card mimo-usage-metric-completion">
        <span className="mimo-usage-metric-label">Completion</span>
        <span className="mimo-usage-metric-value">{completionTokens.toLocaleString()}</span>
        <span className="mimo-usage-metric-pct">{completionPct}%</span>
      </div>
    </div>
  );
}

function ModelBreakdownChart({ rows, emptyLabel }: { rows: TokenUsageModelRow[]; emptyLabel: string }) {
  const top = rows.slice(0, 8);
  const max = Math.max(1, ...top.map((r) => r.total_tokens));

  if (!top.length) {
    return <p className="mimo-token-chart-empty">{emptyLabel}</p>;
  }

  return (
    <div className="mimo-token-model-chart">
      {top.map((row, i) => {
        const pct = (row.total_tokens / max) * 100;
        return (
          <div key={`${row.role}-${row.provider}-${row.model}`} className="mimo-token-model-row">
            <div className="mimo-token-model-meta">
              <span className="mimo-token-model-name">{row.model}</span>
              <span className="mimo-token-model-sub">
                {row.role} · {row.provider}
              </span>
            </div>
            <div className="mimo-token-model-bar-track">
              <div
                className="mimo-token-model-bar-fill"
                style={{ width: `${Math.max(pct, row.total_tokens > 0 ? 8 : 0)}%`, opacity: 1 - i * 0.04 }}
              />
            </div>
            <div className="mimo-token-model-stats">
              <span>{row.total_tokens.toLocaleString()}</span>
              <span className="text-mimo-muted">{row.request_count}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

type TokenUsageChartsProps = {
  daily: TokenUsageDailyRow[];
  byModel: TokenUsageModelRow[];
  mode: "total" | "perModel";
  view: "chart" | "list";
  tokensUnit: string;
  requestLabel: string;
  dayLabel: string;
  emptyLabel: string;
  promptTokens: number;
  completionTokens: number;
};

export function TokenUsageCharts({
  daily,
  byModel,
  mode,
  view,
  tokensUnit,
  requestLabel,
  dayLabel,
  emptyLabel,
  promptTokens,
  completionTokens,
}: TokenUsageChartsProps) {
  const hasData = daily.length > 0 || byModel.length > 0;
  const listRows = useMemo(() => [...daily].reverse(), [daily]);

  if (!hasData) {
    return <p className="mimo-token-chart-empty">{emptyLabel}</p>;
  }

  if (view === "list") {
    return (
      <div className="overflow-x-auto rounded-xl border border-mimo-border">
        <table className="mimo-console-table w-full text-sm">
          <thead>
            <tr>
              <th className="text-left">{dayLabel}</th>
              <th className="text-right">{tokensUnit}</th>
              <th className="text-right">{requestLabel}</th>
            </tr>
          </thead>
          <tbody>
            {listRows.map((row) => (
              <tr key={row.day}>
                <td className="py-2.5">{row.day}</td>
                <td className="py-2.5 text-right tabular-nums">{row.total_tokens.toLocaleString()}</td>
                <td className="py-2.5 text-right tabular-nums">{row.request_count.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (mode === "perModel" && byModel.length > 0) {
    return <ModelBreakdownChart rows={byModel} emptyLabel={emptyLabel} />;
  }

  return (
    <div className="mimo-usage-chart-panel">
      <UsageBarChart
        daily={daily}
        valueKey="total_tokens"
        variant="token"
        unit={tokensUnit}
        emptyLabel={emptyLabel}
      />
      <PromptCompletionCards promptTokens={promptTokens} completionTokens={completionTokens} />
    </div>
  );
}

export function TokenRequestChart({
  daily,
  view,
  timesUnit,
  dayLabel,
  requestLabel,
  emptyLabel,
}: {
  daily: TokenUsageDailyRow[];
  view: "chart" | "list";
  timesUnit: string;
  dayLabel: string;
  requestLabel: string;
  emptyLabel: string;
}) {
  if (!daily.length) {
    return <p className="mimo-token-chart-empty">{emptyLabel}</p>;
  }

  if (view === "list") {
    return (
      <div className="overflow-x-auto rounded-xl border border-mimo-border">
        <table className="mimo-console-table w-full text-sm">
          <thead>
            <tr>
              <th className="text-left">{dayLabel}</th>
              <th className="text-right">{requestLabel}</th>
            </tr>
          </thead>
          <tbody>
            {[...daily].reverse().map((row) => (
              <tr key={row.day}>
                <td className="py-2.5">{row.day}</td>
                <td className="py-2.5 text-right tabular-nums">
                  {row.request_count.toLocaleString()} {timesUnit}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="mimo-usage-chart-panel">
      <UsageBarChart
        daily={daily}
        valueKey="request_count"
        variant="request"
        unit={timesUnit}
        emptyLabel={emptyLabel}
      />
    </div>
  );
}
