import { useCallback, useEffect, useState } from "react";
import { FolderOpen, Loader2, X } from "lucide-react";
import { api } from "@/lib/api";
import { useLocale } from "@/context/LocaleContext";

type Props = {
  scope: string;
};

const STORAGE_KEY = "hub_default_save_path";

function persistLocal(scope: string, path: string) {
  try {
    if (path) localStorage.setItem(`${STORAGE_KEY}:${scope}`, path);
    else localStorage.removeItem(`${STORAGE_KEY}:${scope}`);
  } catch {
    /* ignore */
  }
}

export function ConsoleSavePathPicker({ scope }: Props) {
  const { t } = useLocale();
  const s = t.claw;
  const [path, setPath] = useState("");
  const [open, setOpen] = useState(false);
  const [picking, setPicking] = useState(false);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    try {
      const res = await api.getConsoleSettings();
      const effective = res.default_save_path || "";
      setPath(effective);
      persistLocal(scope, effective);
    } catch {
      try {
        setPath(localStorage.getItem(`${STORAGE_KEY}:${scope}`) || "");
      } catch {
        setPath("");
      }
    }
  }, [scope]);

  useEffect(() => {
    void load();
  }, [load]);

  const pickFolder = async () => {
    setMsg("");
    setPicking(true);
    try {
      const res = await api.pickConsoleSaveFolder();
      if (res.cancelled) {
        if (res.error) setMsg(res.error);
        return;
      }
      const next = res.default_save_path || "";
      setPath(next);
      persistLocal(scope, next);
      setMsg(s.savePathSaved);
      setOpen(false);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : s.savePathFailed);
    } finally {
      setPicking(false);
    }
  };

  const clearPath = async () => {
    setMsg("");
    setPicking(true);
    try {
      await api.saveConsoleSettings({ default_save_path: "" });
      setPath("");
      persistLocal(scope, "");
      setMsg(s.savePathCleared);
      setOpen(false);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : s.savePathFailed);
    } finally {
      setPicking(false);
    }
  };

  const short = path
    ? path.length > 28
      ? `…${path.slice(-26)}`
      : path
    : s.savePathUnset;

  return (
    <div className="relative">
      <button
        type="button"
        className="inline-flex max-w-[12rem] items-center gap-1.5 rounded-lg border border-border bg-surface px-2 py-1 text-xs text-text-secondary transition hover:border-primary/30 hover:text-text-primary"
        onClick={() => setOpen((v) => !v)}
        title={path ? `${s.savePathLabel}: ${path}` : s.savePathHint}
      >
        <FolderOpen size={12} className="shrink-0 text-primary" aria-hidden />
        <span className="truncate">{short}</span>
      </button>
      {open && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 cursor-default"
            aria-label="close"
            onClick={() => setOpen(false)}
          />
          <div className="absolute left-0 z-50 mt-1.5 w-[min(100vw-2rem,22rem)] rounded-xl border border-border bg-surface p-3 shadow-lg">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-medium text-text-primary">{s.savePathLabel}</p>
                <p className="mt-1 text-[11px] leading-snug text-text-secondary">{s.savePathHint}</p>
              </div>
              <button
                type="button"
                className="shrink-0 rounded-md p-1 text-text-secondary hover:bg-border/50"
                onClick={() => setOpen(false)}
              >
                <X size={14} />
              </button>
            </div>
            {path ? (
              <p className="mt-2 break-all rounded-lg border border-border/80 bg-surface-elevated px-2.5 py-2 font-mono text-[11px] text-text-primary">
                {path}
              </p>
            ) : (
              <p className="mt-2 text-xs text-text-secondary">{s.savePathUnset}</p>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-primary inline-flex items-center gap-1.5 px-3 py-1.5 text-xs"
                disabled={picking}
                onClick={() => void pickFolder()}
              >
                {picking ? <Loader2 size={14} className="animate-spin" /> : <FolderOpen size={14} />}
                {s.savePathPick}
              </button>
              {path && (
                <button
                  type="button"
                  className="btn-secondary px-3 py-1.5 text-xs"
                  disabled={picking}
                  onClick={() => void clearPath()}
                >
                  {s.savePathClear}
                </button>
              )}
            </div>
            {msg && <p className="mt-2 text-xs text-mimo-accent">{msg}</p>}
          </div>
        </>
      )}
    </div>
  );
}
