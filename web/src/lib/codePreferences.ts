import type { CodeWorkflowMode } from "@/components/code/CodeAgentToolbar";

const PREFIX = "sensehub_code_prefs";

function key(scope: string): string {
  return `${PREFIX}::${scope}`;
}

export type CodePreferences = {
  mode: CodeWorkflowMode;
  modelId: string;
};

const DEFAULT: CodePreferences = {
  mode: "agent",
  modelId: "auto",
};

export function loadCodePreferences(scope: string): CodePreferences {
  try {
    const raw = localStorage.getItem(key(scope));
    if (!raw) return { ...DEFAULT };
    const data = JSON.parse(raw) as Partial<CodePreferences> & { mode?: string };
    const modelId = typeof data.modelId === "string" ? data.modelId : DEFAULT.modelId;
    const m = data.mode;
    if (m === "agent" || m === "plan") {
      return { mode: m, modelId };
    }
    // 旧版把 auto 当成工作流，迁移为 agent + Auto 模型
    if (m === "auto") {
      return { mode: "agent", modelId: modelId || "auto" };
    }
    return { ...DEFAULT, modelId };
  } catch {
    return { ...DEFAULT };
  }
}

export function saveCodePreferences(scope: string, prefs: CodePreferences): void {
  localStorage.setItem(key(scope), JSON.stringify(prefs));
}
