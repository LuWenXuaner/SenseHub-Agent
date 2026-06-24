import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import { useLocale } from "@/context/LocaleContext";
import type { TokenUsageSummary } from "@/lib/api";
import {
  defaultExportOptions,
  exportTokenUsageExcel,
  type TokenUsageExportOptions,
} from "@/lib/exportTokenUsage";

type Props = {
  open: boolean;
  data: TokenUsageSummary | null;
  onClose: () => void;
};

const EMPTY_EXPORT_OPTIONS: TokenUsageExportOptions = {
  includeSummary: true,
  summaryScope: "range",
  includeDaily: true,
  selectedDays: [],
  includeByModel: true,
};

export function TokenUsageExportDialog({ open, data, onClose }: Props) {
  const { t, locale, fmt } = useLocale();
  const tp = t.tokenPlan;
  const [options, setOptions] = useState<TokenUsageExportOptions>(EMPTY_EXPORT_OPTIONS);

  useEffect(() => {
    if (open && data) {
      setOptions(defaultExportOptions(data));
    }
  }, [open, data]);

  const sortedDays = useMemo(() => {
    if (!data) return [];
    return [...data.daily].sort((a, b) => b.day.localeCompare(a.day));
  }, [data]);

  const selectedSet = useMemo(() => new Set(options.selectedDays), [options.selectedDays]);

  const canExport = useMemo(() => {
    if (!data) return false;
    const hasSection = options.includeSummary || options.includeDaily || options.includeByModel;
    if (!hasSection) return false;
    if (options.includeDaily && options.selectedDays.length === 0) return false;
    if (
      options.includeSummary &&
      options.summaryScope === "selected" &&
      options.selectedDays.length === 0
    ) {
      return false;
    }
    return true;
  }, [data, options]);

  if (!open || !data) return null;

  const toggleDay = (day: string) => {
    setOptions((prev) => {
      const next = new Set(prev.selectedDays);
      if (next.has(day)) next.delete(day);
      else next.add(day);
      return { ...prev, selectedDays: [...next].sort() };
    });
  };

  const selectAllDays = () => {
    setOptions((prev) => ({ ...prev, selectedDays: data.daily.map((row) => row.day) }));
  };

  const clearDays = () => {
    setOptions((prev) => ({ ...prev, selectedDays: [] }));
  };

  const handleExport = () => {
    if (!canExport) return;
    exportTokenUsageExcel(data, options, locale);
    onClose();
  };

  const showDayPicker = options.includeDaily || options.summaryScope === "selected";

  return (
    <div className="mimo-modal-overlay" onClick={onClose} role="presentation">
      <div
        className="mimo-token-export-dialog"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="token-export-title"
      >
        <button type="button" className="mimo-modal-close" onClick={onClose} aria-label={t.common.cancel}>
          <X size={18} />
        </button>

        <h2 id="token-export-title" className="text-lg font-semibold">
          {tp.exportTitle}
        </h2>
        <p className="mt-1 text-sm text-mimo-muted">{tp.exportSubtitle}</p>

        <div className="mimo-token-export-section">
          <label className="mimo-token-export-check">
            <input
              type="checkbox"
              checked={options.includeSummary}
              onChange={(e) => setOptions((prev) => ({ ...prev, includeSummary: e.target.checked }))}
            />
            <span>{tp.exportIncludeSummary}</span>
          </label>
          {options.includeSummary && (
            <div className="mimo-token-export-sub">
              <label className="mimo-token-export-radio">
                <input
                  type="radio"
                  name="summaryScope"
                  checked={options.summaryScope === "range"}
                  onChange={() => setOptions((prev) => ({ ...prev, summaryScope: "range" }))}
                />
                <span>{tp.exportSummaryRange}</span>
              </label>
              <label className="mimo-token-export-radio">
                <input
                  type="radio"
                  name="summaryScope"
                  checked={options.summaryScope === "selected"}
                  onChange={() => setOptions((prev) => ({ ...prev, summaryScope: "selected" }))}
                />
                <span>{tp.exportSummarySelected}</span>
              </label>
            </div>
          )}
        </div>

        <div className="mimo-token-export-section">
          <label className="mimo-token-export-check">
            <input
              type="checkbox"
              checked={options.includeDaily}
              onChange={(e) => setOptions((prev) => ({ ...prev, includeDaily: e.target.checked }))}
            />
            <span>{tp.exportIncludeDaily}</span>
          </label>
        </div>

        <div className="mimo-token-export-section">
          <label className="mimo-token-export-check">
            <input
              type="checkbox"
              checked={options.includeByModel}
              onChange={(e) => setOptions((prev) => ({ ...prev, includeByModel: e.target.checked }))}
            />
            <span>{tp.exportIncludeModel}</span>
          </label>
        </div>

        {showDayPicker && sortedDays.length > 0 && (
          <div className="mimo-token-export-section">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium">{tp.exportPickDays}</p>
              <div className="flex gap-2">
                <button type="button" className="mimo-token-export-link" onClick={selectAllDays}>
                  {tp.exportSelectAll}
                </button>
                <button type="button" className="mimo-token-export-link" onClick={clearDays}>
                  {tp.exportClearDays}
                </button>
              </div>
            </div>
            <p className="mt-1 text-xs text-mimo-muted">
              {fmt(tp.exportSelectedCount, { n: options.selectedDays.length, total: sortedDays.length })}
            </p>
            <div className="mimo-token-export-day-list">
              {sortedDays.map((row) => (
                <label key={row.day} className="mimo-token-export-day-item">
                  <input
                    type="checkbox"
                    checked={selectedSet.has(row.day)}
                    onChange={() => toggleDay(row.day)}
                  />
                  <span className="mimo-token-export-day-date">{row.day}</span>
                  <span className="mimo-token-export-day-meta">
                    {row.total_tokens.toLocaleString()} {tp.tokensUnit} · {row.request_count} {tp.timesUnit}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="mt-6 flex gap-2">
          <button type="button" className="mimo-console-outline-btn mimo-btn-block" onClick={onClose}>
            {t.common.cancel}
          </button>
          <button
            type="button"
            className="mimo-console-primary-btn mimo-btn-block"
            disabled={!canExport}
            onClick={handleExport}
          >
            {tp.exportConfirm}
          </button>
        </div>
      </div>
    </div>
  );
}
