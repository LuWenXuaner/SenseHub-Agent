import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { StudioModelPicker } from "@/components/mimo/StudioModelPicker";
import { useLocale } from "@/context/LocaleContext";
import { STUDIO_MODELS, type StudioModelItem } from "@/lib/modelCatalog";

/** 工作流：Agent 直接改码 / Plan 先规划再改码 */
export type CodeWorkflowMode = "agent" | "plan";

type Props = {
  mode: CodeWorkflowMode;
  modelId: string;
  onModeChange: (mode: CodeWorkflowMode) => void;
  onModelChange: (id: string) => void;
};

export function CodeAgentToolbar({ mode, modelId, onModeChange, onModelChange }: Props) {
  const { t } = useLocale();
  const c = t.code;
  const [pickerOpen, setPickerOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const selected = useMemo(() => {
    if (modelId === "auto" || !modelId) return null;
    return STUDIO_MODELS.find((m) => m.id === modelId) ?? null;
  }, [modelId]);

  const modelLabel = modelId === "auto" || !modelId ? c.modelAuto : selected?.name ?? modelId;

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setPickerOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const workflows: { id: CodeWorkflowMode; label: string; hint: string }[] = [
    { id: "agent", label: c.modeAgent, hint: c.modeAgentHint },
    { id: "plan", label: c.modePlan, hint: c.modePlanHint },
  ];

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-mimo-border/70 bg-transparent px-3 py-1.5">
      <span className="text-[10px] font-medium uppercase tracking-wide text-mimo-muted">{c.workflowLabel}</span>
      <div className="inline-flex rounded-lg border border-mimo-border bg-mimo-warm/40 p-0.5">
        {workflows.map((m) => (
          <button
            key={m.id}
            type="button"
            title={m.hint}
            className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition ${
              mode === m.id
                ? "bg-white text-mimo-text shadow-sm ring-1 ring-mimo-border/60"
                : "text-mimo-muted hover:text-mimo-text"
            }`}
            onClick={() => onModeChange(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>

      <span className="ml-1 text-[10px] font-medium uppercase tracking-wide text-mimo-muted">{c.modelLabel}</span>
      <div ref={rootRef} className="relative">
        <button
          type="button"
          className="inline-flex max-w-[200px] items-center gap-1 rounded-lg border border-mimo-border px-2 py-1 text-[11px] text-mimo-text hover:bg-mimo-warm"
          onClick={() => setPickerOpen((v) => !v)}
        >
          <span className="truncate">{modelLabel}</span>
          <ChevronDown size={12} className={`shrink-0 opacity-50 ${pickerOpen ? "rotate-180" : ""}`} />
        </button>
        {pickerOpen && (
          <div className="absolute right-0 top-full z-50 mt-1.5 w-56 min-w-[14rem] overflow-visible rounded-xl border border-mimo-border bg-white py-1 shadow-lg">
            <button
              type="button"
              className={`w-full px-3 py-2 text-left text-xs hover:bg-mimo-warm ${
                modelId === "auto" || !modelId ? "font-medium text-mimo-accent" : "text-mimo-muted"
              }`}
              onClick={() => {
                onModelChange("auto");
                setPickerOpen(false);
              }}
            >
              <span className="block">{c.modelAuto}</span>
              <span className="mt-0.5 block text-[10px] font-normal leading-snug opacity-70">{c.modelAutoHint}</span>
            </button>
            <div className="border-t border-mimo-border px-3 py-1.5 text-[10px] font-medium uppercase tracking-wide text-mimo-muted">
              {c.modelPick}
            </div>
            <StudioModelPicker
              embedded
              flyoutSide="left"
              open
              modelId={modelId === "auto" ? "" : modelId}
              onSelect={(id) => {
                onModelChange(id);
                setPickerOpen(false);
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
