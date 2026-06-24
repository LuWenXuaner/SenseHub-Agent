import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ConsolePageFrame } from "@/components/mimo/ConsolePageFrame";
import { RulesPage } from "@/pages/RulesPage";
import { useLocale } from "@/context/LocaleContext";
import { api, type PluginRow } from "@/lib/api";

export function ConsolePluginsPage() {
  const { t } = useLocale();
  const p = t.pluginsPage;
  const [plugins, setPlugins] = useState<PluginRow[]>([]);
  const [msg, setMsg] = useState("");

  const load = () =>
    api.pluginsList().then((r) => setPlugins(r.items)).catch(() => setPlugins([]));

  useEffect(() => {
    void load();
  }, []);

  const toggle = async (row: PluginRow) => {
    try {
      await api.pluginToggle(row.id, !row.enabled);
      setMsg(row.enabled ? p.disabledMsg : p.enabledMsg);
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : p.toggleFailed);
    }
  };

  return (
    <ConsolePageFrame title={t.console.pluginMgmt} subtitle={p.subtitle}>
      {msg && <p className="mb-4 text-sm text-mimo-accent">{msg}</p>}
      <div className="mimo-console-panel overflow-x-auto p-0">
        <table className="mimo-console-table w-full text-left text-sm">
          <thead>
            <tr>
              <th>{p.colName}</th>
              <th>{p.colDesc}</th>
              <th>{p.colStatus}</th>
              <th>{p.colAction}</th>
            </tr>
          </thead>
          <tbody>
            {plugins.map((row) => (
              <tr key={row.id}>
                <td className="font-medium">{row.name}</td>
                <td className="max-w-xs text-mimo-muted">{row.desc}</td>
                <td>
                  <span className={row.enabled ? "mimo-status-ok" : "text-mimo-muted"}>
                    {row.enabled && <span className="mimo-status-dot" />}
                    {row.enabled ? p.statusOn : p.statusOff}
                  </span>
                </td>
                <td>
                  <button type="button" className="text-[#1677ff] hover:underline" onClick={() => void toggle(row)}>
                    {row.enabled ? p.disable : p.enable}
                  </button>
                  <Link to="/product/api" className="ml-3 text-[#1677ff] hover:underline">
                    {p.apiDoc}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="mt-10 text-lg font-semibold">{p.voiceRules}</h3>
      <p className="mt-1 text-sm text-mimo-muted">{p.voiceRulesDesc}</p>
      <div className="mimo-console-plugins-embed mt-4">
        <RulesPage embedded />
      </div>
    </ConsolePageFrame>
  );
}
