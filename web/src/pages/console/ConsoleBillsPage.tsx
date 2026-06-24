import { useEffect, useState } from "react";
import { ConsolePageFrame } from "@/components/mimo/ConsolePageFrame";
import { FileText } from "lucide-react";
import { useLocale } from "@/context/LocaleContext";
import { useWallet } from "@/hooks/useWallet";
import { api, type BillRow } from "@/lib/api";
import { formatPoints } from "@/lib/pointsCatalog";

export function ConsoleBillsPage() {
  const { t, locale } = useLocale();
  const b = t.billsPage;
  const [tab, setTab] = useState<"detail" | "monthly">("detail");
  const [summary, setSummary] = useState({ total_spent: 0, token_usage: 0, asr_seconds: 0, plugin_calls: 0 });
  const [rows, setRows] = useState<BillRow[]>([]);
  const { balance } = useWallet();

  useEffect(() => {
    api.walletBills().then((r) => {
      setSummary(r.summary);
      setRows(r.items);
    }).catch(() => {});
  }, []);

  const zero = formatPoints(summary.total_spent, locale);

  return (
    <ConsolePageFrame title={t.console.bills} subtitle={b.subtitle}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: b.totalSpent, value: zero },
          { label: b.tokenUsage, value: String(summary.token_usage) },
          { label: b.asrDuration, value: `${summary.asr_seconds} s` },
          { label: b.pluginCalls, value: String(summary.plugin_calls) },
        ].map((c) => (
          <div key={c.label} className="mimo-balance-summary-card">
            <p className="text-sm text-mimo-muted">{c.label}</p>
            <p className="mt-2 text-2xl font-semibold">{c.value}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-xl border border-mimo-border bg-white px-4 py-3 text-sm">
        <span className="text-mimo-muted">{b.currentBalance}</span>
        <span className="ml-2 font-semibold">{formatPoints(balance, locale)}</span>
      </div>

      <div className="mt-8 flex gap-6 border-b border-mimo-border">
        {(
          [
            { id: "detail", label: b.tabDetail },
            { id: "monthly", label: b.tabMonthly },
          ] as const
        ).map((item) => (
          <button
            key={item.id}
            type="button"
            className={`mimo-console-tab ${tab === item.id ? "mimo-console-tab-active" : ""}`}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="mimo-console-info-banner mt-4">{t.points.rule4}</div>

      <div className="mimo-console-panel mt-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-medium">{b.usageBill}</h3>
          <p className="text-sm text-mimo-muted">
            {b.totalLabel} {zero}
          </p>
        </div>
        {rows.length === 0 ? (
          <div className="mimo-console-empty mt-10">
            <FileText size={48} className="text-mimo-border" />
            <p className="mt-4 text-sm text-mimo-muted">{t.common.noData}</p>
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="mimo-console-table w-full text-left text-sm">
              <thead>
                <tr>
                  <th>{b.colDate}</th>
                  <th>{b.colCategory}</th>
                  <th>{b.colDesc}</th>
                  <th className="text-right">{b.colCost}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td className="text-mimo-muted">{r.bill_date}</td>
                    <td>{r.category}</td>
                    <td>{r.description}</td>
                    <td className="text-right">{formatPoints(r.points_cost, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </ConsolePageFrame>
  );
}
