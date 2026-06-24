import * as XLSX from "xlsx";
import type { TokenUsageDailyRow, TokenUsageSummary } from "@/lib/api";
import type { Locale } from "@/lib/i18n";

export type TokenUsageExportOptions = {
  includeSummary: boolean;
  /** 全周期 API 总量，或仅所选日期按日加总 */
  summaryScope: "range" | "selected";
  includeDaily: boolean;
  selectedDays: string[];
  includeByModel: boolean;
};

const LABELS: Record<
  Locale,
  {
    sheetSummary: string;
    sheetDaily: string;
    sheetModel: string;
    date: string;
    totalTokens: string;
    requestCount: string;
    promptTokens: string;
    completionTokens: string;
    role: string;
    provider: string;
    model: string;
    rangeDays: string;
    dateRange: string;
    selectedDayCount: string;
    summaryScopeRange: string;
    summaryScopeSelected: string;
    modelScopeNote: string;
    partialPromptNote: string;
  }
> = {
  zh: {
    sheetSummary: "汇总",
    sheetDaily: "每日用量",
    sheetModel: "按模型",
    date: "日期",
    totalTokens: "Token 总消耗",
    requestCount: "请求次数",
    promptTokens: "Prompt Tokens",
    completionTokens: "Completion Tokens",
    role: "角色",
    provider: "提供商",
    model: "模型",
    rangeDays: "统计天数",
    dateRange: "日期范围",
    selectedDayCount: "所选天数",
    summaryScopeRange: "全周期",
    summaryScopeSelected: "所选日期",
    modelScopeNote: "说明：按模型为当前查询范围内累计，不受所选日期限制",
    partialPromptNote: "说明：Prompt/Completion 仅全周期汇总时提供",
  },
  en: {
    sheetSummary: "Summary",
    sheetDaily: "Daily usage",
    sheetModel: "By model",
    date: "Date",
    totalTokens: "Total tokens",
    requestCount: "Requests",
    promptTokens: "Prompt tokens",
    completionTokens: "Completion tokens",
    role: "Role",
    provider: "Provider",
    model: "Model",
    rangeDays: "Range (days)",
    dateRange: "Date range",
    selectedDayCount: "Days selected",
    summaryScopeRange: "Full range",
    summaryScopeSelected: "Selected days",
    modelScopeNote: "Note: per-model totals cover the full query range, not only selected days.",
    partialPromptNote: "Note: Prompt/Completion breakdown is only available for full-range summary.",
  },
};

function stamp() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}`;
}

function resolveDailyRows(data: TokenUsageSummary, options: TokenUsageExportOptions): TokenUsageDailyRow[] {
  const selected = new Set(options.selectedDays);
  const pool = selected.size ? data.daily.filter((row) => selected.has(row.day)) : data.daily;
  return [...pool].sort((a, b) => a.day.localeCompare(b.day));
}

function buildSummarySheet(
  data: TokenUsageSummary,
  options: TokenUsageExportOptions,
  labels: (typeof LABELS)["zh"],
  dailyRows: TokenUsageDailyRow[]
) {
  const useSelected =
    options.summaryScope === "selected" && options.selectedDays.length > 0 && dailyRows.length > 0;

  if (useSelected) {
    const totalTokens = dailyRows.reduce((sum, row) => sum + row.total_tokens, 0);
    const requestCount = dailyRows.reduce((sum, row) => sum + row.request_count, 0);
    const days = dailyRows.map((row) => row.day);
    return [
      [labels.sheetSummary],
      [labels.summaryScopeSelected],
      [labels.dateRange, `${days[0]} ~ ${days[days.length - 1]}`],
      [labels.selectedDayCount, days.length],
      [labels.totalTokens, totalTokens],
      [labels.requestCount, requestCount],
      [labels.partialPromptNote],
    ];
  }

  return [
    [labels.sheetSummary],
    [labels.summaryScopeRange],
    [labels.rangeDays, data.range_days ?? ""],
    [labels.totalTokens, data.total_tokens],
    [labels.promptTokens, data.prompt_tokens],
    [labels.completionTokens, data.completion_tokens],
    [labels.requestCount, data.request_count],
  ];
}

export function exportTokenUsageExcel(
  data: TokenUsageSummary,
  options: TokenUsageExportOptions,
  locale: Locale = "zh"
) {
  const labels = LABELS[locale];
  const wb = XLSX.utils.book_new();
  const dailyRows = resolveDailyRows(data, options);
  const partialDays =
    options.selectedDays.length > 0 && options.selectedDays.length < data.daily.length;

  if (options.includeSummary) {
    const summaryRows = buildSummarySheet(data, options, labels, dailyRows);
    if (options.includeByModel && partialDays) {
      summaryRows.push([labels.modelScopeNote]);
    }
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(summaryRows), labels.sheetSummary.slice(0, 31));
  }

  if (options.includeDaily && dailyRows.length > 0) {
    const dailyHeader = [labels.date, labels.totalTokens, labels.requestCount];
    const rows = [dailyHeader, ...dailyRows.map((row) => [row.day, row.total_tokens, row.request_count])];
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rows), labels.sheetDaily.slice(0, 31));
  }

  if (options.includeByModel && data.by_model.length > 0) {
    const modelHeader = [labels.role, labels.provider, labels.model, labels.totalTokens, labels.requestCount];
    const modelRows = [
      modelHeader,
      ...data.by_model.map((row) => [
        row.role,
        row.provider,
        row.model,
        row.total_tokens,
        row.request_count,
      ]),
    ];
    if (partialDays) {
      modelRows.push([], [labels.modelScopeNote]);
    }
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(modelRows), labels.sheetModel.slice(0, 31));
  }

  const filename = `token-usage_${stamp()}.xlsx`;
  XLSX.writeFile(wb, filename);
}

export function defaultExportOptions(data: TokenUsageSummary): TokenUsageExportOptions {
  return {
    includeSummary: true,
    summaryScope: "range",
    includeDaily: true,
    selectedDays: data.daily.map((row) => row.day),
    includeByModel: true,
  };
}
