import { useEffect, useState } from "react";
import { useLocale } from "@/context/LocaleContext";
import { api } from "@/lib/api";
import { POINTS } from "@/lib/pointsCatalog";

export function InviteProgressPanel({ compact = false }: { compact?: boolean }) {
  const { t, fmt } = useLocale();
  const ip = t.inviteProgress;
  const [stats, setStats] = useState({
    invited: 0,
    earned: 0,
    pending: 0,
    rebate_total: 0,
    quota: 30,
  });

  useEffect(() => {
    api.invitesOverview().then((r) => setStats({ ...r.stats, quota: r.stats.quota || 30 })).catch(() => {});
  }, []);

  const pct = Math.min(100, (stats.invited / stats.quota) * 100);
  const remaining = Math.max(0, stats.quota - stats.invited);

  return (
    <div className={compact ? "space-y-4" : "space-y-6"}>
      <div className={`grid gap-3 ${compact ? "grid-cols-2" : "sm:grid-cols-2 lg:grid-cols-4"}`}>
        {[
          { label: ip.invited, value: String(stats.invited), sub: fmt(ip.quota, { max: stats.quota }) },
          { label: ip.earned, value: `${stats.earned}`, sub: ip.earnedUnit },
          { label: ip.pending, value: `${stats.pending}`, sub: ip.pendingHint },
          { label: ip.rebate, value: `${stats.rebate_total}`, sub: ip.rebateHint },
        ].map((c) => (
          <div key={c.label} className="mimo-console-panel">
            <p className="text-xs text-mimo-muted">{c.label}</p>
            <p className={`mt-1 font-semibold ${compact ? "text-xl" : "text-2xl"}`}>{c.value}</p>
            <p className="mt-1 text-[11px] text-mimo-muted">{c.sub}</p>
          </div>
        ))}
      </div>

      <div className="mimo-console-panel">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">{ip.progressTitle}</span>
          <span className="text-mimo-muted">
            {stats.invited}/{stats.quota}
          </span>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-mimo-border">
          <div className="h-full rounded-full bg-mimo-cta transition-all" style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-2 text-xs text-mimo-muted">{fmt(ip.remaining, { n: remaining })}</p>
      </div>
    </div>
  );
}

export function InviteRulesPanel({ compact = false }: { compact?: boolean }) {
  const { t, fmt } = useLocale();
  const ir = t.inviteRules;
  const rules = [
    fmt(ir.ruleSignup, { n: POINTS.inviteRegister, max: POINTS.inviteMax }),
    fmt(ir.ruleBoth, { n: POINTS.inviteRegister }),
    fmt(ir.ruleRebate, { pct: POINTS.inviteRebatePercent }),
    fmt(ir.ruleFriendDiscount, { pct: POINTS.friendFirstRedeemDiscountPercent }),
    fmt(ir.ruleValid, { days: POINTS.rebateValidDays }),
    ir.ruleLimit,
    ir.ruleAbuse,
    ir.ruleSettlement,
  ];

  return (
    <div className="space-y-4">
      <p className="text-sm text-mimo-muted">{ir.intro}</p>
      <ol className={`list-decimal space-y-2 pl-5 text-mimo-muted ${compact ? "text-xs leading-6" : "text-sm leading-7"}`}>
        {rules.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ol>
      {!compact && <div className="mimo-console-info-banner text-xs leading-6">{ir.footer}</div>}
    </div>
  );
}
