import { useEffect, useMemo, useState } from "react";
import { api, type PointsLedgerRow } from "@/lib/api";
import { ConsolePageFrame } from "@/components/mimo/ConsolePageFrame";
import { useLocale } from "@/context/LocaleContext";
import { useWallet } from "@/hooks/useWallet";
import { formatPoints } from "@/lib/pointsCatalog";
import { ArrowDownRight, ArrowUpRight, Gift, Receipt, Wallet } from "lucide-react";

type Filter = "all" | "earn" | "spend";

function ledgerTypeLabel(type: string, t: ReturnType<typeof useLocale>["t"]) {
  const map: Record<string, string> = {
    checkin: t.points.historyTypeSignIn,
    checkin_bonus: t.points.historyTypeBonus,
    invite_signup: t.points.historyTypeInvite,
    invite_rebate: t.pointsHistory.noteInviteRebate,
    redeem: t.points.historyTypeRedeem,
    subscribe: t.tokenPlan.subscribePlan,
  };
  return map[type] ?? type;
}

export function ConsolePointsHistoryPage() {
  const { t, locale } = useLocale();
  const ph = t.pointsHistory;
  const { balance, totalEarned, summary } = useWallet();
  const [filter, setFilter] = useState<Filter>("all");
  const [rows, setRows] = useState<PointsLedgerRow[]>([]);

  useEffect(() => {
    api.walletLedger(filter).then((r) => setRows(r.items)).catch(() => setRows([]));
  }, [filter]);

  const spent = summary?.total_spent ?? 0;

  return (
    <ConsolePageFrame title={t.console.pointsHistory} subtitle={ph.subtitle}>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="mimo-console-stat-card">
          <Wallet size={18} className="text-mimo-accent" />
          <p className="mt-2 text-xs text-mimo-muted">{ph.currentBalance}</p>
          <p className="mt-1 text-xl font-semibold">{formatPoints(balance, locale)}</p>
        </div>
        <div className="mimo-console-stat-card">
          <ArrowUpRight size={18} className="text-[#389e0d]" />
          <p className="mt-2 text-xs text-mimo-muted">{ph.totalIn}</p>
          <p className="mt-1 text-xl font-semibold text-[#389e0d]">+{formatPoints(totalEarned, locale)}</p>
        </div>
        <div className="mimo-console-stat-card">
          <ArrowDownRight size={18} className="text-mimo-muted" />
          <p className="mt-2 text-xs text-mimo-muted">{ph.totalOut}</p>
          <p className="mt-1 text-xl font-semibold">-{formatPoints(spent, locale)}</p>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {(
          [
            { id: "all", label: ph.filterAll },
            { id: "earn", label: ph.filterEarn },
            { id: "spend", label: ph.filterSpend },
          ] as const
        ).map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`mimo-console-outline-btn text-sm ${filter === tab.id ? "border-mimo-text bg-white" : ""}`}
            onClick={() => setFilter(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="mimo-console-panel mt-4 overflow-x-auto p-0">
        <table className="mimo-console-table w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr>
              <th>{ph.colTime}</th>
              <th>{ph.colType}</th>
              <th>{ph.colNote}</th>
              <th className="text-right">{ph.colChange}</th>
              <th className="text-right">{ph.colBalance}</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-10 text-center text-mimo-muted">
                  {t.common.noData}
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id}>
                  <td className="whitespace-nowrap text-mimo-muted">{r.created_at}</td>
                  <td>
                    <span className="inline-flex items-center gap-1.5">
                      {r.delta > 0 ? <Gift size={12} className="text-[#389e0d]" /> : <Receipt size={12} className="text-mimo-muted" />}
                      {ledgerTypeLabel(r.entry_type, t)}
                    </span>
                  </td>
                  <td className="max-w-xs text-mimo-muted">{r.note || "—"}</td>
                  <td className={`text-right font-medium ${r.delta > 0 ? "text-[#389e0d]" : "text-mimo-text"}`}>
                    {r.delta > 0 ? "+" : ""}
                    {r.delta} {t.common.pointsUnit}
                  </td>
                  <td className="text-right text-mimo-muted">{r.balance_after.toLocaleString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </ConsolePageFrame>
  );
}

export function ConsoleExchangeLogPage() {
  const { t, locale } = useLocale();
  const ph = t.pointsHistory;
  const [rows, setRows] = useState<Awaited<ReturnType<typeof api.walletExchanges>>["items"]>([]);

  useEffect(() => {
    api.walletExchanges().then((r) => setRows(r.items)).catch(() => setRows([]));
  }, []);

  return (
    <ConsolePageFrame title={t.console.exchange} subtitle={t.points.exchangeTitle}>
      <div className="mimo-console-panel overflow-x-auto p-0">
        <table className="mimo-console-table w-full text-left text-sm">
          <thead>
            <tr>
              <th>{ph.colTime}</th>
              <th>{ph.colType}</th>
              <th>{ph.colNote}</th>
              <th className="text-right">{ph.colChange}</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-10 text-center text-mimo-muted">
                  {ph.emptyExchange}
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id}>
                  <td className="text-mimo-muted">{r.created_at}</td>
                  <td>{t.points.historyTypeRedeem}</td>
                  <td>{r.item_label}</td>
                  <td className="text-right">-{formatPoints(r.cost, locale)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </ConsolePageFrame>
  );
}
