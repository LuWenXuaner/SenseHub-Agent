import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useWallet } from "@/hooks/useWallet";
import { TIER_PLANS, type TierId } from "@/lib/tierCatalog";
import { ConsolePageFrame } from "@/components/mimo/ConsolePageFrame";
import { TokenRequestChart, TokenUsageCharts } from "@/components/console/TokenUsageCharts";
import { TokenUsageExportDialog } from "@/components/console/TokenUsageExportDialog";
import { OfficialQrCode } from "@/components/marketing/OfficialQrCode";
import { ArrowUpRight, Copy, RefreshCw } from "lucide-react";
import { useMemo, useState, useEffect } from "react";
import { useLocale } from "@/context/LocaleContext";
import { api, type TokenUsageSummary } from "@/lib/api";

const BASE_URLS = {
  openai: "https://api.lingshu.ai/v1",
  anthropic: "https://api.lingshu.ai/anthropic",
};

const MODEL_LIST =
  "Qwen3 · DeepSeek-V3 · Doubao · GPT · Claude · Grok · Gemini · Qwen2.5-VL · SenseVoice · CosyVoice";

export function ConsoleTokenPlanPage() {
  const { license, refreshLicense } = useAuth();
  const { summary } = useWallet();
  const { t, fmt } = useLocale();
  const tp = t.tokenPlan;
  const tier = (license?.tier ?? summary?.tier ?? "lite") as TierId;
  const plan = TIER_PLANS.find((p) => p.id === tier);
  const subscribed = license?.subscription_active ?? summary?.subscription_active ?? tier !== "lite";
  const [copied, setCopied] = useState<string | null>(null);
  const [autoRenew, setAutoRenew] = useState(false);
  const [usageTab, setUsageTab] = useState<"llm" | "asr" | "tts">("llm");
  const [granularity, setGranularity] = useState<"year" | "month" | "day">("month");
  const [viewMode, setViewMode] = useState<"chart" | "list">("chart");
  const [tokenMode, setTokenMode] = useState<"total" | "perModel">("total");
  const [tokenUsage, setTokenUsage] = useState<TokenUsageSummary | null>(null);
  const [tokenLoading, setTokenLoading] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);

  const rangeDays = useMemo(() => {
    if (granularity === "day") return 14;
    if (granularity === "month") return 30;
    return 90;
  }, [granularity]);

  useEffect(() => {
    let cancelled = false;
    setTokenLoading(true);
    api
      .walletTokenUsage(rangeDays)
      .then((data) => {
        if (!cancelled) setTokenUsage(data);
      })
      .catch(() => {
        if (!cancelled) setTokenUsage(null);
      })
      .finally(() => {
        if (!cancelled) setTokenLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [rangeDays]);

  const llmTotalTokens = tokenUsage?.total_tokens ?? 0;
  const llmRequestCount = tokenUsage?.request_count ?? 0;

  const chartDaily = tokenUsage?.daily ?? [];

  const maskedKey = `tp-lingshu-${(license?.tier ?? "lite").slice(0, 2)}****${String(license?.text_commands_used ?? 0).slice(-4).padStart(4, "0")}`;
  const used = license?.text_commands_used ?? 0;
  const limit = license?.text_commands_limit;
  const unlimited = license?.text_commands_unlimited ?? limit == null;
  const usagePct = useMemo(() => {
    if (unlimited) return used > 0 ? Math.min(12, used) : 0;
    if (!limit) return 0;
    return Math.min(100, (used / limit) * 100);
  }, [used, limit, unlimited]);

  const validUntil =
    license?.tier_expires_at ?? summary?.tier_expires_at ?? (subscribed ? "—" : "—");

  const usageSummary = useMemo(() => {
    if (!subscribed && tier === "lite") return tp.noSubscription;
    if (unlimited) return fmt(tp.usageUnlimited, { n: used });
    if (limit != null) return fmt(tp.usageLimited, { used, limit });
    return tp.usagePlaceholder;
  }, [subscribed, tier, unlimited, used, limit, tp, fmt]);

  const usageBarWidth = unlimited ? (used > 0 ? `${usagePct}%` : "100%") : `${usagePct}%`;
  const usageBarClass = unlimited ? "mimo-token-plan-bar-unlimited" : "";

  const copyText = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleExport = () => {
    if (!tokenUsage) return;
    setExportOpen(true);
  };

  const benefitRows = [
    { label: tp.models, value: MODEL_LIST },
    { label: tp.quota, value: plan?.highlights.join(" · ") ?? "—" },
    { label: tp.tools, value: "灵枢 Code · OpenCode · Cline · Cursor" },
    { label: tp.other, value: tp.otherDesc },
  ];

  const usageDetailLine = unlimited
    ? fmt(tp.usagePercent, { pct: "∞" })
    : limit != null
      ? fmt(tp.usagePercent, { pct: Math.round(usagePct) })
      : "";

  return (
    <ConsolePageFrame
      title={tp.title}
      actions={
        <Link to="/token-plan" className="mimo-console-primary-btn mimo-btn-sm">
          {tp.subscribePlan}
        </Link>
      }
    >
      <div className="mimo-token-plan-qr-panel">
        <OfficialQrCode label={tp.qrLabel} compact />
        <div className="mimo-token-plan-qr-copy">
          <h3 className="text-sm font-medium">{tp.joinGroup}</h3>
          <p className="mt-0.5 text-xs leading-5 text-mimo-muted">{tp.joinGroupHint}</p>
        </div>
      </div>

      <div className="mimo-token-plan-section">
        <div className="mimo-token-plan-grid-top">
          <div className={`mimo-token-plan-card mimo-token-plan-card-plan mimo-token-plan-card-plan--${tier}`}>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold">
                {plan?.name ?? tier.toUpperCase()} {tp.monthly}
              </h2>
              <span className={`mimo-console-tag ${subscribed ? "mimo-console-tag-active" : ""}`}>
                {subscribed ? tp.active : tp.expired}
              </span>
            </div>
            <p className="mt-3 text-sm text-mimo-muted">
              {subscribed && validUntil !== "—"
                ? `${tp.validUntil} ${validUntil} 23:59 (UTC)`
                : tp.noSubscription}
            </p>
            <div className="mt-auto pt-6">
              <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-mimo-muted">
                <button
                  type="button"
                  role="switch"
                  aria-checked={autoRenew}
                  className={`mimo-token-plan-switch ${autoRenew ? "mimo-token-plan-switch-on" : ""}`}
                  onClick={() => setAutoRenew((v) => !v)}
                >
                  <span className="mimo-token-plan-switch-thumb" />
                </button>
                {tp.autoRenew}
              </label>
            </div>
          </div>

          <div className={`mimo-token-plan-card mimo-token-plan-card-usage mimo-token-plan-card-usage--${tier}`}>
            <p className="text-sm font-medium">{tp.usage}</p>
            <div className="mt-auto space-y-3 pt-8">
              <div className="h-2 overflow-hidden rounded-full bg-mimo-border">
                <div
                  className={`h-full rounded-full bg-[#c9a96e] transition-all ${usageBarClass}`}
                  style={{ width: usageBarWidth }}
                />
              </div>
              <p className="text-center text-sm font-medium text-mimo-text">{usageSummary}</p>
              {usageDetailLine && (
                <p className="text-center text-xs text-mimo-muted">{usageDetailLine}</p>
              )}
            </div>
          </div>
        </div>

        <div className="mimo-token-plan-panel">
          <div className="mimo-token-plan-panel-head">
            <h3 className="text-sm font-medium">{tp.apiKey}</h3>
            <Link to="/code" className="inline-flex items-center gap-1 text-sm text-[#1677ff] hover:underline">
              {tp.importTools}
              <ArrowUpRight size={14} />
            </Link>
          </div>
          <div className="mimo-token-plan-field">
            <code className="min-w-0 flex-1 truncate text-sm">{maskedKey}</code>
            <button
              type="button"
              className="mimo-icon-btn shrink-0"
              onClick={() => void copyText(maskedKey, "key")}
              aria-label={t.common.copy}
            >
              <Copy size={16} />
            </button>
            <button
              type="button"
              className="mimo-icon-btn shrink-0"
              onClick={() => void refreshLicense()}
              aria-label={t.common.refresh}
            >
              <RefreshCw size={16} />
            </button>
          </div>
          {copied === "key" && <p className="mt-2 text-xs text-mimo-accent">{t.common.copied}</p>}
          <p className="mt-3 text-xs leading-6 text-mimo-muted">{tp.keyHint}</p>
        </div>

        <div className="mimo-token-plan-panel">
          <h3 className="text-sm font-medium">{tp.baseUrl}</h3>
          <div className="mt-4">
            {(
              [
                { id: "openai", label: tp.openaiProtocol, url: BASE_URLS.openai },
                { id: "anthropic", label: tp.anthropicProtocol, url: BASE_URLS.anthropic },
              ] as const
            ).map((row) => (
              <div key={row.id} className="mimo-token-plan-url-row">
                <span className="mimo-token-plan-url-label">{row.label}</span>
                <div className="mimo-token-plan-field min-w-0 flex-1">
                  <span className="min-w-0 flex-1 truncate font-mono text-sm">{row.url}</span>
                  <button
                    type="button"
                    className="mimo-icon-btn shrink-0"
                    onClick={() => void copyText(row.url, row.id)}
                    aria-label={t.common.copy}
                  >
                    <Copy size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
          {(copied === "openai" || copied === "anthropic") && (
            <p className="mt-2 text-xs text-mimo-accent">{t.common.copied}</p>
          )}
        </div>

        <div className="mimo-token-plan-panel">
          <div className="mimo-token-plan-panel-head">
            <h3 className="text-sm font-medium">{tp.benefits}</h3>
            <Link to="/pricing" className="inline-flex items-center gap-0.5 text-sm text-mimo-muted hover:text-mimo-text">
              {tp.learnMoreBenefits}
              <span aria-hidden>&gt;</span>
            </Link>
          </div>
          <dl className="mimo-token-plan-benefits">
            {benefitRows.map((row) => (
              <div key={row.label} className="mimo-token-plan-benefit-row">
                <dt>{row.label}</dt>
                <dd>{row.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>

      <h3 className="mt-10 text-base font-semibold">{tp.usageDetail}</h3>
      <div className="mimo-console-info-banner mt-4 text-xs leading-6">{tp.dataNote}</div>

      <div className="mimo-token-plan-usage-toolbar mt-4">
        <div className="mimo-token-plan-segment">
          {(
            [
              { id: "year", label: tp.granularityYear },
              { id: "month", label: tp.granularityMonth },
              { id: "day", label: tp.granularityDay },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              type="button"
              className={`mimo-token-plan-segment-btn ${granularity === item.id ? "mimo-token-plan-segment-btn-active" : ""}`}
              onClick={() => setGranularity(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select className="mimo-console-input w-auto min-w-[120px] py-1.5 text-sm" defaultValue="2026-06">
            <option value="2026-06">2026-06</option>
            <option value="2026-05">2026-05</option>
          </select>
          <div className="mimo-token-plan-segment">
            {(
              [
                { id: "chart", label: tp.chartView },
                { id: "list", label: tp.listView },
              ] as const
            ).map((item) => (
              <button
                key={item.id}
                type="button"
                className={`mimo-token-plan-segment-btn ${viewMode === item.id ? "mimo-token-plan-segment-btn-active" : ""}`}
                onClick={() => setViewMode(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="mimo-console-outline-btn mimo-btn-sm"
            disabled={!tokenUsage || tokenLoading}
            onClick={handleExport}
          >
            {tp.export}
          </button>
        </div>
      </div>

      <div className="mimo-token-plan-panel mt-4">
        <h4 className="mimo-token-plan-subsection-title">{tp.usageStats}</h4>
        <div className="mt-4 flex flex-wrap gap-2 border-b border-mimo-border pb-3">
          {(
            [
              { id: "llm", label: tp.llm },
              { id: "asr", label: tp.asr },
              { id: "tts", label: tp.tts },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              type="button"
              className={`mimo-console-tab ${usageTab === item.id ? "mimo-console-tab-active" : ""}`}
              onClick={() => setUsageTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm">
            <span className="text-mimo-muted">{tp.tokenTotal}</span>
            <span className="mx-2 text-mimo-muted">|</span>
            <span className="font-medium">
              {tokenLoading ? "…" : llmTotalTokens.toLocaleString()} {tp.tokensUnit}
            </span>
          </p>
          <div className="mimo-token-plan-segment">
            {(
              [
                { id: "total", label: tp.tokenTotalMode },
                { id: "perModel", label: tp.tokenPerModelMode },
              ] as const
            ).map((item) => (
              <button
                key={item.id}
                type="button"
                className={`mimo-token-plan-segment-btn text-xs ${tokenMode === item.id ? "mimo-token-plan-segment-btn-active" : ""}`}
                onClick={() => setTokenMode(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {usageTab === "llm" && tokenUsage && (chartDaily.length > 0 || tokenUsage.by_model.length > 0) ? (
          <div className="mt-4 min-h-[220px]">
            <TokenUsageCharts
              daily={chartDaily}
              byModel={tokenUsage.by_model}
              mode={tokenMode}
              view={viewMode}
              tokensUnit={tp.tokensUnit}
              requestLabel={tp.requestTotal}
              dayLabel={tp.granularityDay}
              emptyLabel={t.common.noData}
              promptTokens={tokenUsage.prompt_tokens}
              completionTokens={tokenUsage.completion_tokens}
            />
          </div>
        ) : (
        <div className="mimo-console-empty mt-2 min-h-[220px]">
          <svg width="120" height="96" viewBox="0 0 120 96" fill="none" aria-hidden className="opacity-80">
            <rect x="20" y="12" width="56" height="72" rx="4" fill="#e6f4ff" />
            <rect x="32" y="24" width="56" height="72" rx="4" fill="#bae0ff" />
            <rect x="44" y="36" width="56" height="72" rx="4" fill="#91caff" />
          </svg>
          <p className="mt-4 text-sm text-mimo-muted">{tokenLoading ? "…" : t.common.noData}</p>
        </div>
        )}
      </div>

      <div className="mimo-token-plan-panel mt-4">
        <h4 className="mimo-token-plan-subsection-title">{tp.requestCount}</h4>
        <p className="mt-4 text-sm">
          <span className="text-mimo-muted">{tp.requestTotal}</span>
          <span className="mx-2 text-mimo-muted">|</span>
          <span className="font-medium">
            {tokenLoading ? "…" : llmRequestCount.toLocaleString()} {tp.timesUnit}
          </span>
        </p>
        {chartDaily.length > 0 ? (
          <div className="mt-4 min-h-[200px]">
            <TokenRequestChart
              daily={chartDaily}
              view={viewMode}
              timesUnit={tp.timesUnit}
              dayLabel={tp.granularityDay}
              requestLabel={tp.requestTotal}
              emptyLabel={t.common.noData}
            />
          </div>
        ) : (
        <div className="mimo-console-empty mt-2 min-h-[160px]">
          <svg width="120" height="96" viewBox="0 0 120 96" fill="none" aria-hidden className="opacity-80">
            <rect x="20" y="12" width="56" height="72" rx="4" fill="#e6f4ff" />
            <rect x="32" y="24" width="56" height="72" rx="4" fill="#bae0ff" />
            <rect x="44" y="36" width="56" height="72" rx="4" fill="#91caff" />
          </svg>
          <p className="mt-4 text-sm text-mimo-muted">{tokenLoading ? "…" : t.common.noData}</p>
        </div>
        )}
      </div>
      <TokenUsageExportDialog open={exportOpen} data={tokenUsage} onClose={() => setExportOpen(false)} />
    </ConsolePageFrame>
  );
}
