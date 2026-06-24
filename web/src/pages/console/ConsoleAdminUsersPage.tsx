import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { ConsolePageFrame } from "@/components/mimo/ConsolePageFrame";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { api, type AdminUserRow } from "@/lib/api";
import { formatPoints } from "@/lib/pointsCatalog";

export function ConsoleAdminUsersPage() {
  const { user } = useAuth();
  const { t, locale, fmt } = useLocale();
  const ap = t.adminPage;

  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<AdminUserRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [grantUser, setGrantUser] = useState<AdminUserRow | null>(null);
  const [amount, setAmount] = useState("1000");
  const [note, setNote] = useState("");
  const [granting, setGranting] = useState(false);

  const load = async (q = query) => {
    setLoading(true);
    setErr("");
    try {
      const res = await api.adminSearchUsers(q.trim());
      setRows(res.items);
    } catch (e) {
      setErr(e instanceof Error ? e.message : t.common.noData);
      setRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.username === "admin") void load("");
  }, [user?.username]);

  if (user && user.username !== "admin") {
    return <Navigate to="/console/account" replace />;
  }

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault();
    void load(query);
  };

  const onGrant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!grantUser) return;
    const n = parseInt(amount, 10);
    if (!Number.isFinite(n) || n <= 0) {
      setErr(ap.amountInvalid);
      return;
    }
    setGranting(true);
    setErr("");
    setMsg("");
    try {
      const res = await api.adminGrantPoints(grantUser.user_id, n, note.trim());
      setMsg(fmt(ap.grantSuccess, { amount: res.amount, username: res.username, balance: res.balance }));
      setGrantUser(null);
      setNote("");
      await load(query);
    } catch (e) {
      setErr(e instanceof Error ? e.message : ap.grantFailed);
    } finally {
      setGranting(false);
    }
  };

  return (
    <ConsolePageFrame title={ap.title} subtitle={ap.subtitle}>
      <form className="flex flex-wrap items-end gap-3" onSubmit={onSearch}>
        <div className="min-w-[280px] flex-1">
          <label className="mb-1 block text-xs text-mimo-muted">{ap.searchLabel}</label>
          <input
            className="mimo-console-input w-full"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={ap.searchPlaceholder}
          />
        </div>
        <button type="submit" className="mimo-btn-cta mimo-btn-sm" disabled={loading}>
          {loading ? "…" : ap.search}
        </button>
      </form>

      {msg ? <p className="mt-4 text-sm text-green-700">{msg}</p> : null}
      {err ? <p className="mt-4 text-sm text-red-600">{err}</p> : null}

      <div className="mimo-console-panel mt-6 overflow-x-auto p-0">
        <table className="mimo-console-table w-full text-left text-sm">
          <thead>
            <tr>
              <th>{ap.colUserId}</th>
              <th>{ap.colPublicId}</th>
              <th>{ap.colUsername}</th>
              <th>{ap.colEmail}</th>
              <th>{ap.colBalance}</th>
              <th>{ap.colTier}</th>
              <th>{ap.colExpires}</th>
              <th>{ap.colActions}</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-6 text-center text-mimo-muted">
                  {loading ? "…" : t.common.noData}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.user_id}>
                  <td className="font-mono text-xs">{row.user_id}</td>
                  <td>{row.public_id ?? "—"}</td>
                  <td>{row.username}</td>
                  <td>{row.email || "—"}</td>
                  <td>{formatPoints(row.points_balance ?? 0, locale)}</td>
                  <td>{(row.tier ?? "lite").toUpperCase()}</td>
                  <td>{row.tier_expires_at ?? "—"}</td>
                  <td>
                    <button
                      type="button"
                      className="mimo-btn-sm text-mimo-accent"
                      onClick={() => {
                        setGrantUser(row);
                        setAmount("1000");
                        setNote("");
                        setMsg("");
                        setErr("");
                      }}
                    >
                      {ap.grant}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {grantUser ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form
            className="mimo-console-panel w-full max-w-md space-y-4 p-6"
            onSubmit={(e) => void onGrant(e)}
          >
            <h3 className="text-base font-medium">{ap.grantTitle}</h3>
            <p className="text-sm text-mimo-muted">
              {grantUser.username} · {ap.colPublicId} {grantUser.public_id ?? "—"}
            </p>
            <div>
              <label className="mb-1 block text-xs text-mimo-muted">{ap.amount}</label>
              <input
                className="mimo-console-input w-full"
                type="number"
                min={1}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-mimo-muted">{ap.note}</label>
              <input
                className="mimo-console-input w-full"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={ap.notePlaceholder}
              />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="mimo-btn-sm" onClick={() => setGrantUser(null)}>
                {t.common.cancel}
              </button>
              <button type="submit" className="mimo-btn-cta mimo-btn-sm" disabled={granting}>
                {granting ? "…" : ap.grant}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </ConsolePageFrame>
  );
}
