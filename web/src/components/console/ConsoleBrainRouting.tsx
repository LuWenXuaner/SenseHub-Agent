import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Brain, ChevronDown, RotateCcw, X } from "lucide-react";
import { api, type ApiConfigPublic, type BrainPreset, type RoleConfigPublic } from "@/lib/api";
import { useLocale } from "@/context/LocaleContext";

type RoleDraft = { provider: string; model: string };

type Props = {
  variant?: "full" | "compact";
  onSaved?: () => void;
  reloadKey?: number;
};

function draftFromConfig(cfg: ApiConfigPublic): Record<string, RoleDraft> {
  const out: Record<string, RoleDraft> = {};
  for (const r of cfg.roles ?? []) {
    out[r.role] = { provider: r.provider, model: r.model };
  }
  return out;
}

function modelDisplay(
  row: RoleDraft | undefined,
  presets: BrainPreset[],
  fallback = "—"
): string {
  if (!row?.model) return fallback;
  const preset = presets.find((p) => p.provider === row.provider && p.model === row.model);
  return preset?.label || row.model;
}

export function ConsoleBrainRouting({ variant = "full", onSaved, reloadKey = 0 }: Props) {
  const { t, locale } = useLocale();
  const k = t.apiKeys;
  const b = t.brainRouting;
  const [open, setOpen] = useState(false);
  const [roles, setRoles] = useState<RoleConfigPublic[]>([]);
  const [presets, setPresets] = useState<BrainPreset[]>([]);
  const [providers, setProviders] = useState<{ id: string; label: string; configured: boolean }[]>([]);
  const [draft, setDraft] = useState<Record<string, RoleDraft>>({});
  const [defaults, setDefaults] = useState<Record<string, RoleDraft>>({});
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    const cfg = await api.getApiConfig();
    setRoles(cfg.roles ?? []);
    setPresets(cfg.brain_presets ?? []);
    setProviders(
      (cfg.providers ?? []).map((p) => ({
        id: p.id,
        label: p.label,
        configured: p.configured,
      }))
    );
    const d = draftFromConfig(cfg);
    setDraft(d);
    const def: Record<string, RoleDraft> = {};
    for (const r of cfg.roles ?? []) {
      def[r.role] = {
        provider: r.default_provider || "",
        model: r.default_model || "",
      };
    }
    setDefaults(def);
  }, []);

  useEffect(() => {
    void load().catch(() => {});
  }, [load, reloadKey]);

  const providerOptions = useMemo(() => {
    const ids = new Set(providers.map((p) => p.id));
    for (const r of roles) {
      if (r.provider) ids.add(r.provider);
      if (r.default_provider) ids.add(r.default_provider);
    }
    for (const p of presets) ids.add(p.provider);
    return [...ids].map((id) => {
      const row = providers.find((p) => p.id === id);
      return { id, label: row?.label || id, configured: row?.configured ?? false };
    });
  }, [providers, roles, presets]);

  const applyPreset = (role: string, presetId: string) => {
    const preset = presets.find((p) => p.id === presetId);
    if (!preset) return;
    setDraft((d) => ({
      ...d,
      [role]: { provider: preset.provider, model: preset.model },
    }));
  };

  const resetRole = (role: string) => {
    const def = defaults[role];
    if (!def) return;
    setDraft((d) => ({ ...d, [role]: { ...def } }));
  };

  const isCustom = (role: string) => {
    const row = draft[role];
    const def = defaults[role];
    if (!row || !def) return false;
    return row.provider !== def.provider || row.model !== def.model;
  };

  const save = async () => {
    setErr("");
    setMsg("");
    setLoading(true);
    try {
      const role_routes: Record<string, { provider: string; model: string }> = {};
      for (const r of roles) {
        const row = draft[r.role];
        const def = defaults[r.role];
        if (!row?.provider || !row?.model) continue;
        const isDefault = def && row.provider === def.provider && row.model === def.model;
        role_routes[r.role] = isDefault
          ? { provider: "", model: "" }
          : { provider: row.provider, model: row.model };
      }
      await api.saveApiConfig({ role_routes });
      setMsg(b.saved);
      await load();
      onSaved?.();
    } catch (e) {
      setErr(e instanceof Error ? e.message : b.saveFailed);
    } finally {
      setLoading(false);
    }
  };

  const providerConfigured = (providerId: string, roleName: string) => {
    const prov = providerOptions.find((p) => p.id === providerId);
    const roleRow = roles.find((r) => r.role === roleName);
    return Boolean(prov?.configured || roleRow?.configured);
  };

  const roleLabel = (r: RoleConfigPublic) =>
    locale === "zh" ? r.label_zh || r.role : r.label_en || r.role;
  const roleDesc = (r: RoleConfigPublic) =>
    locale === "zh" ? r.description_zh || r.description : r.description_en || r.description;

  const customCount = roles.filter((r) => isCustom(r.role)).length;

  const compactSummary = useMemo(() => {
    const planner = roles.find((r) => r.role === "planner");
    const intent = roles.find((r) => r.role === "intent");
    const parts: string[] = [];
    if (intent) parts.push(modelDisplay(draft[intent.role], presets, intent.role));
    if (planner) parts.push(modelDisplay(draft[planner.role], presets, planner.role));
    return parts.join(" / ");
  }, [roles, draft, presets]);

  const roleTableRows = roles.map((r) => {
    const row = draft[r.role] ?? { provider: "", model: "" };
    const prov = providerOptions.find((p) => p.id === row.provider);
    const unconfigured = Boolean(row.provider) && !providerConfigured(row.provider, r.role);
    const presetId =
      presets.find((p) => p.provider === row.provider && p.model === row.model)?.id ?? "";
    const custom = isCustom(r.role);

    return (
      <tr key={r.role} className={unconfigured ? "bg-amber-500/[0.06]" : undefined}>
        <td className="min-w-[7rem] align-middle">
          <div className="flex items-center gap-2">
            <span className="font-medium">{roleLabel(r)}</span>
            {custom && (
              <span className="rounded-full bg-primary/15 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                {b.customBadge}
              </span>
            )}
          </div>
          {roleDesc(r) && (
            <p className="mt-0.5 max-w-[12rem] text-xs leading-snug text-mimo-muted">{roleDesc(r)}</p>
          )}
        </td>
        <td className="align-middle">
          <select
            className="mimo-console-input mimo-console-input-compact w-full min-w-[8rem]"
            value={presetId}
            onChange={(e) => {
              if (e.target.value) applyPreset(r.role, e.target.value);
            }}
          >
            <option value="">{b.custom}</option>
            {presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </td>
        <td className="align-middle">
          <select
            className="mimo-console-input mimo-console-input-compact w-full min-w-[7rem]"
            value={row.provider}
            onChange={(e) =>
              setDraft((d) => ({
                ...d,
                [r.role]: { ...row, provider: e.target.value },
              }))
            }
          >
            {providerOptions.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
                {!p.configured ? ` (${b.noKey})` : ""}
              </option>
            ))}
          </select>
        </td>
        <td className="align-middle">
          <input
            className="mimo-console-input mimo-console-input-compact w-full min-w-[10rem] font-mono text-xs"
            value={row.model}
            onChange={(e) =>
              setDraft((d) => ({
                ...d,
                [r.role]: { ...row, model: e.target.value },
              }))
            }
            placeholder={defaults[r.role]?.model}
          />
          {unconfigured && (
            <p className="mt-1 text-[11px] text-amber-600 dark:text-amber-400">{b.keyRequired}</p>
          )}
        </td>
        <td className="align-middle text-center">
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-md p-1.5 text-mimo-muted transition hover:bg-border/40 hover:text-text-primary"
            onClick={() => resetRole(r.role)}
            title={b.resetRole}
          >
            <RotateCcw size={14} aria-hidden />
          </button>
        </td>
      </tr>
    );
  });

  const compactRoleRows = roles.map((r) => {
    const row = draft[r.role] ?? { provider: "", model: "" };
    const prov = providerOptions.find((p) => p.id === row.provider);
    const unconfigured = Boolean(row.provider) && !providerConfigured(row.provider, r.role);
    const presetId =
      presets.find((p) => p.provider === row.provider && p.model === row.model)?.id ?? "";
    const custom = isCustom(r.role);
    const display = modelDisplay(row, presets);

    return (
      <div
        key={r.role}
        className={`rounded-lg border p-2.5 ${
          unconfigured
            ? "border-amber-500/30 bg-amber-500/[0.04]"
            : custom
              ? "border-primary/25 bg-primary/[0.03]"
              : "border-border/80 bg-surface/60"
        }`}
      >
        <div className="mb-2 flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-sm font-medium text-text-primary">{roleLabel(r)}</span>
              {custom && (
                <span className="rounded-full bg-primary/15 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                  {b.customBadge}
                </span>
              )}
            </div>
            {roleDesc(r) && (
              <p className="mt-0.5 text-[11px] leading-snug text-text-secondary">{roleDesc(r)}</p>
            )}
          </div>
          <button
            type="button"
            className="shrink-0 rounded-md p-1 text-text-secondary transition hover:bg-border/40 hover:text-text-primary"
            onClick={() => resetRole(r.role)}
            title={b.resetRole}
          >
            <RotateCcw size={13} aria-hidden />
          </button>
        </div>
        <div className="space-y-1.5">
          <select
            className="w-full rounded-md border border-border bg-surface px-2 py-1.5 text-xs text-text-primary outline-none focus:border-primary/50"
            value={presetId}
            onChange={(e) => {
              if (e.target.value) applyPreset(r.role, e.target.value);
            }}
          >
            <option value="">{b.presetCustom}</option>
            {presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
          <div className="grid grid-cols-2 gap-1.5">
            <select
              className="min-w-0 rounded-md border border-border bg-surface px-2 py-1.5 text-xs text-text-primary outline-none focus:border-primary/50"
              value={row.provider}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  [r.role]: { ...row, provider: e.target.value },
                }))
              }
            >
              {providerOptions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                  {!p.configured ? ` · ${b.noKey}` : ""}
                </option>
              ))}
            </select>
            <input
              className="min-w-0 rounded-md border border-border bg-surface px-2 py-1.5 font-mono text-[11px] text-text-primary outline-none focus:border-primary/50"
              value={row.model}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  [r.role]: { ...row, model: e.target.value },
                }))
              }
              placeholder={defaults[r.role]?.model}
              title={display}
            />
          </div>
          {unconfigured && (
            <p className="text-[11px] leading-snug text-amber-600 dark:text-amber-400">{b.keyRequiredCompact}</p>
          )}
        </div>
      </div>
    );
  });

  const saveBar = (
    <div className={`flex flex-wrap items-center gap-2 ${variant === "compact" ? "pt-1" : "mt-4"}`}>
      <button
        type="button"
        className={variant === "compact" ? "btn-primary px-3 py-1.5 text-xs" : "mimo-console-primary-btn"}
        disabled={loading}
        onClick={() => void save()}
      >
        {loading ? b.saving : b.save}
      </button>
      {variant === "compact" && (
        <Link
          to="/console/api-keys"
          className="text-xs text-text-secondary underline-offset-2 hover:text-primary hover:underline"
          onClick={() => setOpen(false)}
        >
          {b.settingsLink}
        </Link>
      )}
      {(msg || err) && (
        <span className={`text-xs ${err ? "text-danger" : "text-mimo-accent"}`}>{err || msg}</span>
      )}
    </div>
  );

  if (variant === "compact") {
    return (
      <div className="relative">
        <button
          type="button"
          className={`inline-flex max-w-[11rem] items-center gap-1.5 rounded-lg border px-2 py-1 text-xs transition ${
            open
              ? "border-primary bg-primary/15 font-medium text-primary ring-1 ring-primary/35"
              : "border-border bg-surface text-text-secondary hover:border-primary/30 hover:text-text-primary"
          }`}
          onClick={() => setOpen((v) => !v)}
          title={compactSummary ? `${b.compactHint}: ${compactSummary}` : b.compactHint}
        >
          <Brain size={12} className="shrink-0" aria-hidden />
          <span className="flex min-w-0 flex-col items-start leading-tight">
            <span className="font-medium">{b.compactLabel}</span>
            {compactSummary && (
              <span className="max-w-[8rem] truncate text-[10px] opacity-80">{compactSummary}</span>
            )}
          </span>
          {customCount > 0 && (
            <span className="rounded-full bg-primary/20 px-1 text-[10px] font-medium text-primary">
              {customCount}
            </span>
          )}
          <ChevronDown size={12} className={`shrink-0 transition ${open ? "rotate-180" : ""}`} aria-hidden />
        </button>
        {open && (
          <>
            <button
              type="button"
              className="fixed inset-0 z-40 cursor-default bg-black/20 backdrop-blur-[1px] dark:bg-black/40"
              aria-label="close"
              onClick={() => setOpen(false)}
            />
            <div className="absolute right-0 z-50 mt-1.5 flex w-[min(100vw-1.5rem,22rem)] flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-xl ring-1 ring-black/5 dark:ring-white/10">
              <div className="flex items-start justify-between gap-2 border-b border-border/80 bg-muted/30 px-3 py-2.5">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-text-primary">{b.panelTitle}</p>
                  <p className="mt-0.5 text-[11px] leading-snug text-text-secondary">{b.panelDesc}</p>
                </div>
                <button
                  type="button"
                  className="shrink-0 rounded-md p-1 text-text-secondary hover:bg-border/50 hover:text-text-primary"
                  onClick={() => setOpen(false)}
                  aria-label="close"
                >
                  <X size={14} />
                </button>
              </div>
              <div className="max-h-[min(60vh,20rem)] space-y-2 overflow-y-auto p-2.5">{compactRoleRows}</div>
              <div className="border-t border-border/80 bg-muted/20 px-2.5 py-2">{saveBar}</div>
            </div>
          </>
        )}
      </div>
    );
  }

  return (
    <section>
      <h3 className="text-lg font-semibold">{k.roleRouting}</h3>
      <p className="mt-1 text-sm text-mimo-muted">{k.roleRoutingDesc}</p>
      <div className="mimo-console-panel mt-4 overflow-x-auto p-0">
        <table className="mimo-console-table w-full min-w-[720px] text-sm">
          <thead>
            <tr>
              <th>{b.colBrain}</th>
              <th>{b.preset}</th>
              <th>{b.provider}</th>
              <th>{b.model}</th>
              <th className="w-10" aria-hidden />
            </tr>
          </thead>
          <tbody>{roleTableRows}</tbody>
        </table>
      </div>
      {saveBar}
    </section>
  );
}
