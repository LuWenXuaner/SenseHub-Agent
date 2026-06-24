import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { ConsolePageFrame } from "@/components/mimo/ConsolePageFrame";
import { useLocale } from "@/context/LocaleContext";
import { API_INTEGRATIONS } from "@/lib/integrationCatalog";

type ProviderRow = {
  id: string;
  label: string;
  base_url: string;
  api_key: string;
  configured: boolean;
  source: string;
  roles: string[];
  default_base_url: string;
};

type RoleRow = { role: string; provider: string; provider_label: string; model: string };

function rolesFromConfig(models: unknown): RoleRow[] {
  const roles = (models as { roles?: Record<string, { provider?: string; model?: string }> }).roles;
  if (!roles || typeof roles !== "object") return [];
  return Object.entries(roles).map(([role, row]) => ({
    role,
    provider: String(row?.provider ?? ""),
    provider_label: String(row?.provider ?? ""),
    model: String(row?.model ?? ""),
  }));
}

export function ConsoleApiKeysPage() {
  const { t, locale } = useLocale();
  const k = t.apiKeys;
  const [providers, setProviders] = useState<ProviderRow[]>([]);
  const [roles, setRoles] = useState<RoleRow[]>([]);
  const [draft, setDraft] = useState<Record<string, { base_url: string; api_key: string }>>({});
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = () =>
    Promise.all([api.getApiConfig(), api.modelsConfig()])
      .then(([c, models]) => {
        const list = (c as { providers?: ProviderRow[] }).providers || [];
        setProviders(list);
        setRoles(rolesFromConfig(models));
        const init: Record<string, { base_url: string; api_key: string }> = {};
        for (const p of list) {
          init[p.id] = { base_url: p.base_url || p.default_base_url || "", api_key: "" };
        }
        setDraft(init);
      });

  useEffect(() => {
    load().catch(() => {});
  }, []);

  const save = async () => {
    setErr("");
    try {
      const payload: Record<string, { base_url: string; api_key: string }> = {};
      for (const [id, row] of Object.entries(draft)) {
        if (row.base_url.trim() || row.api_key.trim()) {
          payload[id] = { base_url: row.base_url.trim(), api_key: row.api_key.trim() };
        }
      }
      await api.saveApiConfig({ providers: payload });
      setMsg(k.saved);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : k.saveFailed);
    }
  };

  const integrationLabel = (id: string) => providers.find((p) => p.id === id)?.label || id;

  return (
    <ConsolePageFrame title={t.console.apiKeys} subtitle={k.subtitle}>
      {(msg || err) && (
        <p className={`mb-4 text-sm ${err ? "text-danger" : "text-mimo-accent"}`}>{err || msg}</p>
      )}

      <h3 className="text-lg font-semibold">{k.integrationsTitle}</h3>
      <p className="mt-1 text-sm text-mimo-muted">{k.integrationsDesc}</p>
      <div className="mt-4 overflow-x-auto">
        <table className="mimo-console-table w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr>
              <th>{k.colProvider}</th>
              <th>{k.colModels}</th>
              <th>{k.colRoles}</th>
              <th>{k.colStyle}</th>
              <th>{t.console.apiKeys}</th>
            </tr>
          </thead>
          <tbody>
            {API_INTEGRATIONS.map((row) => (
              <tr key={row.id}>
                <td className="font-medium">{integrationLabel(row.id)}</td>
                <td className="text-mimo-muted">{locale === "zh" ? row.modelsZh : row.modelsEn}</td>
                <td className="text-xs">{locale === "zh" ? row.rolesZh : row.rolesEn}</td>
                <td className="font-mono text-xs">{row.style}</td>
                <td>
                  {providers.find((p) => p.id === row.id)?.configured ? (
                    <span className="mimo-status-ok">
                      <span className="mimo-status-dot" />
                      {k.configured}
                    </span>
                  ) : (
                    <span className="text-mimo-muted">{k.notConfigured}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {roles.length > 0 && (
        <>
          <h3 className="mt-10 text-lg font-semibold">{k.roleRouting}</h3>
          <p className="mt-1 text-sm text-mimo-muted">{k.roleRoutingDesc}</p>
          <div className="mimo-console-panel mt-4 overflow-x-auto p-0">
            <table className="mimo-console-table w-full text-sm">
              <thead>
                <tr>
                  <th>Role</th>
                  <th>Provider</th>
                  <th>Model</th>
                </tr>
              </thead>
              <tbody>
                {roles.map((r) => (
                  <tr key={r.role}>
                    <td className="font-mono text-xs">{r.role}</td>
                    <td>{r.provider_label || r.provider}</td>
                    <td className="max-w-xs truncate font-mono text-xs text-mimo-muted">{r.model}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <h3 className="mt-10 text-lg font-semibold">{k.configuredProviders}</h3>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {providers.map((p) => (
          <div key={p.id} className="mimo-console-provider-card">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-sm font-medium">{p.label}</span>
              <span className="text-[11px] text-mimo-muted">{p.configured ? k.configured : k.notConfigured}</span>
            </div>
            <label className="mimo-console-field-label">{k.baseUrl}</label>
            <input
              className="mimo-console-input mimo-console-input-compact mb-2"
              placeholder={p.default_base_url}
              value={draft[p.id]?.base_url ?? ""}
              onChange={(e) =>
                setDraft((d) => ({ ...d, [p.id]: { ...d[p.id], base_url: e.target.value } }))
              }
            />
            <label className="mimo-console-field-label">{k.apiKey}</label>
            <input
              className="mimo-console-input mimo-console-input-compact"
              type="password"
              placeholder={p.api_key ? `${k.keyMasked} ${p.api_key}` : k.keyPlaceholder}
              value={draft[p.id]?.api_key ?? ""}
              onChange={(e) =>
                setDraft((d) => ({ ...d, [p.id]: { ...d[p.id], api_key: e.target.value } }))
              }
            />
          </div>
        ))}
      </div>
      <div className="mt-6 flex flex-wrap gap-3">
        <button type="button" className="mimo-console-primary-btn" onClick={() => void save()}>
          {k.save}
        </button>
        <button
          type="button"
          className="mimo-console-outline-btn"
          onClick={() =>
            void api.resetApiConfig().then(() => {
              setMsg(k.resetDone);
              return load();
            })
          }
        >
          {k.reset}
        </button>
        <Link to="/product/api" className="mimo-console-outline-btn">
          {t.nav.docs}
        </Link>
      </div>
    </ConsolePageFrame>
  );
}
