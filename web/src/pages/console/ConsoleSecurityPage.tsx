import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { api, AuditEntry } from "@/lib/api";
import { ConsolePageFrame } from "@/components/mimo/ConsolePageFrame";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { Globe, FolderLock, ScrollText, Shield, ShieldCheck } from "lucide-react";

function SecurityPanels() {
  const { t } = useLocale();
  const s = t.securityPage;
  const [ipsText, setIpsText] = useState("");
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [sandbox, setSandbox] = useState<{ workspace: string; policy_whitelist: string[] } | null>(null);
  const [allowLan, setAllowLan] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = async () => {
    const [st, a, sb] = await Promise.all([
      api.securityStatus(),
      api.auditSummary(),
      api.sandboxStatus().catch(() => null),
    ]);
    setAllowLan(st.allow_lan);
    setIpsText(st.ip_whitelist.join("\n"));
    setAudit(a.recent.slice(0, 12));
    if (sb) setSandbox({ workspace: sb.workspace, policy_whitelist: sb.policy_whitelist || [] });
  };

  useEffect(() => {
    load().catch((e) => setErr(e instanceof Error ? e.message : s.loadFailed));
  }, [s.loadFailed]);

  const saveWhitelist = async () => {
    setErr("");
    try {
      const ips = ipsText
        .split(/[\n,;]+/)
        .map((x) => x.trim())
        .filter(Boolean);
      await api.updateWhitelist(ips);
      setMsg(s.saved);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : s.loadFailed);
    }
  };

  const whitelistCount = ipsText.split(/[\n,;]+/).map((x) => x.trim()).filter(Boolean).length;

  return (
    <>
      {(msg || err) && (
        <p className={`mb-4 text-sm ${err ? "text-danger" : "text-mimo-accent"}`}>{err || msg}</p>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="mimo-console-stat-card">
          <Globe size={18} className="text-mimo-accent" />
          <p className="mt-2 text-xs text-mimo-muted">{s.network}</p>
          <p className="mt-1 text-lg font-semibold">{allowLan ? s.lanOn : s.lanOff}</p>
        </div>
        <div className="mimo-console-stat-card">
          <ShieldCheck size={18} className="text-mimo-accent" />
          <p className="mt-2 text-xs text-mimo-muted">{s.ipWhitelist}</p>
          <p className="mt-1 text-lg font-semibold">{whitelistCount}</p>
        </div>
        <div className="mimo-console-stat-card">
          <ScrollText size={18} className="text-mimo-accent" />
          <p className="mt-2 text-xs text-mimo-muted">{s.audit}</p>
          <p className="mt-1 text-lg font-semibold">{audit.length}</p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="mimo-console-panel">
          <div className="flex items-center gap-2">
            <Shield size={18} className="text-mimo-accent" />
            <h3 className="font-medium">{s.network}</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-mimo-muted">{s.networkDesc}</p>
          <label className="mimo-console-field-label mt-5">{s.ipWhitelist}</label>
          <textarea
            className="mimo-console-input mt-1 min-h-[140px] resize-y font-mono text-xs"
            value={ipsText}
            onChange={(e) => setIpsText(e.target.value)}
            placeholder={s.ipPlaceholder}
          />
          <button type="button" className="mimo-console-primary-btn mt-4" onClick={() => void saveWhitelist()}>
            {s.saveWhitelist}
          </button>
        </div>

        <div className="mimo-console-panel">
          <div className="flex items-center gap-2">
            <FolderLock size={18} className="text-mimo-accent" />
            <h3 className="font-medium">{s.sandbox}</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-mimo-muted">{s.sandboxHint}</p>
          <div className="mt-4 rounded-lg border border-mimo-border bg-[#fafafa] px-3 py-2.5">
            <p className="text-[10px] uppercase tracking-wide text-mimo-muted">{s.workspacePath}</p>
            <p className="mt-1 break-all font-mono text-xs">{sandbox?.workspace || "—"}</p>
          </div>
          <p className="mt-4 text-sm">
            <span className="text-mimo-muted">{s.policyCount}</span>{" "}
            <span className="font-semibold">{sandbox?.policy_whitelist?.length ?? 0}</span>{" "}
            <span className="text-mimo-muted">{s.policyItems}</span>
          </p>
          {(sandbox?.policy_whitelist?.length ?? 0) > 0 && (
            <ul className="mt-2 max-h-24 space-y-1 overflow-y-auto font-mono text-[11px] text-mimo-muted">
              {sandbox!.policy_whitelist.map((p) => (
                <li key={p} className="truncate">
                  {p}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="mimo-console-panel mt-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <ScrollText size={18} className="text-mimo-accent" />
            <h3 className="font-medium">{s.audit}</h3>
          </div>
          <span className="text-xs text-mimo-muted">{s.auditRecent}</span>
        </div>
        {audit.length === 0 ? (
          <p className="mt-6 text-center text-sm text-mimo-muted">{s.noAudit}</p>
        ) : (
          <ul className="mt-4 divide-y divide-mimo-border/60">
            {audit.map((row) => (
              <li key={row.id} className="flex gap-4 py-3 text-sm first:pt-0 last:pb-0">
                <time className="w-24 shrink-0 text-xs text-mimo-muted">{row.timestamp.slice(5, 16)}</time>
                <span className="min-w-0 flex-1 font-medium">{row.action}</span>
                {row.result ? (
                  <span className="hidden max-w-[40%] truncate text-xs text-mimo-muted md:inline">{row.result}</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}

export function ConsoleSecurityPage() {
  const { user } = useAuth();
  const { t } = useLocale();

  if (user && user.username !== "admin") {
    return <Navigate to="/console/account" replace />;
  }

  return (
    <ConsolePageFrame title={t.console.security} subtitle={t.securityPage.subtitle}>
      <SecurityPanels />
    </ConsolePageFrame>
  );
}
