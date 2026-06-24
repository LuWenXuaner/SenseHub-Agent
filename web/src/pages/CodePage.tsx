import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronRight,
  FolderOpen,
  Loader2,
  PanelRightClose,
  PanelRightOpen,
  Save,
  SendHorizonal,
  Sparkles,
  X,
} from "lucide-react";
import { useLocale } from "@/context/LocaleContext";
import { useCode } from "@/context/CodeContext";
import { ChatMessageContent } from "@/components/chat/ChatMessageContent";
import { api, type ChatTurn } from "@/lib/api";
import { formatUserFacingError } from "@/lib/thinkingTrace";

type FileEntry = { path: string; handle: FileSystemFileHandle };
type DirHandle = FileSystemDirectoryHandle;

const MAX_CONTEXT_FILE_BYTES = 48_000;
const AGENT_MIN = 300;
const AGENT_MAX = 560;
const AGENT_DEFAULT = 380;

async function listFiles(dir: DirHandle, prefix = ""): Promise<FileEntry[]> {
  const out: FileEntry[] = [];
  const iter = (dir as unknown as { entries: () => AsyncIterableIterator<[string, FileSystemHandle]> }).entries();
  for await (const [name, entry] of iter) {
    const path = prefix ? `${prefix}/${name}` : name;
    if (entry.kind === "file") {
      out.push({ path, handle: entry as FileSystemFileHandle });
    } else if (entry.kind === "directory" && out.length < 300) {
      out.push(...(await listFiles(entry as FileSystemDirectoryHandle, path)));
    }
    if (out.length >= 300) break;
  }
  return out.sort((a, b) => a.path.localeCompare(b.path));
}

async function writeFile(handle: FileSystemFileHandle, content: string) {
  const writable = await handle.createWritable();
  await writable.write(content);
  await writable.close();
}

async function readText(handle: FileSystemFileHandle, maxBytes = MAX_CONTEXT_FILE_BYTES) {
  const file = await handle.getFile();
  if (file.size > maxBytes) {
    const slice = file.slice(0, maxBytes);
    return (await slice.text()) + "\n\n…(文件过大，已截断)";
  }
  return file.text();
}

function matchContextFiles(text: string, files: FileEntry[], activePath: string) {
  const lower = text.toLowerCase();
  return files
    .filter((f) => {
      if (f.path === activePath) return false;
      const base = f.path.split("/").pop()?.toLowerCase() ?? "";
      return lower.includes(f.path.toLowerCase()) || (base.length > 2 && lower.includes(base));
    })
    .slice(0, 4);
}

export function CodePage() {
  const { t } = useLocale();
  const c = t.code;
  const { messages, persistMessages, sessionId } = useCode();
  const [dirName, setDirName] = useState("");
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [activePath, setActivePath] = useState("");
  const [content, setContent] = useState("");
  const [activeHandle, setActiveHandle] = useState<FileSystemFileHandle | null>(null);
  const [saved, setSaved] = useState(false);
  const [aiInput, setAiInput] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiNotice, setAiNotice] = useState("");
  const [agentOpen, setAgentOpen] = useState(true);
  const [agentWidth, setAgentWidth] = useState(AGENT_DEFAULT);
  const aiEndRef = useRef<HTMLDivElement>(null);
  const layoutRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    aiEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, aiLoading]);

  const pickFolder = async () => {
    if (!("showDirectoryPicker" in window)) {
      alert(c.pickFolderHint);
      return;
    }
    try {
      const dir = await (window as Window & { showDirectoryPicker: () => Promise<DirHandle> }).showDirectoryPicker();
      setDirName(dir.name);
      setFiles(await listFiles(dir));
      closeFile();
      setAiNotice("");
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      throw err;
    }
  };

  const openFile = async (path: string, handle: FileSystemFileHandle) => {
    const text = await readText(handle, 512_000);
    setActivePath(path);
    setActiveHandle(handle);
    setContent(text);
    setSaved(false);
  };

  const closeFile = useCallback(() => {
    setActivePath("");
    setActiveHandle(null);
    setContent("");
    setSaved(false);
  }, []);

  const saveFile = useCallback(async () => {
    if (!activeHandle) return;
    await writeFile(activeHandle, content);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }, [activeHandle, content]);

  const applyEdits = useCallback(
    async (edits: { path: string; content: string }[]) => {
      let applied = 0;
      for (const edit of edits) {
        const entry = files.find((f) => f.path === edit.path);
        if (!entry) continue;
        await writeFile(entry.handle, edit.content);
        applied += 1;
        if (activePath === edit.path) {
          setContent(edit.content);
          setSaved(true);
          setTimeout(() => setSaved(false), 2000);
        }
      }
      if (applied > 0) {
        setAiNotice(c.aiApplied.replace("{count}", String(applied)));
        setTimeout(() => setAiNotice(""), 3000);
      }
    },
    [activePath, c.aiApplied, files]
  );

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = agentWidth;
    const onMove = (ev: MouseEvent) => {
      const next = Math.min(AGENT_MAX, Math.max(AGENT_MIN, startW + (startX - ev.clientX)));
      setAgentWidth(next);
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  const sendAi = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const text = aiInput.trim();
    if (!text || aiLoading) return;
    if (!dirName || files.length === 0) {
      setAiNotice(c.aiNoProject);
      setTimeout(() => setAiNotice(""), 2500);
      return;
    }

    const userMsg = { role: "user" as const, content: text };
    const nextMsgs = [...messages, userMsg];
    persistMessages(nextMsgs, dirName);
    setAiInput("");
    setAiLoading(true);
    setAiNotice("");

    const history: ChatTurn[] = messages.map((m) => ({ role: m.role, content: m.content }));
    const contextFiles: { path: string; content: string }[] = [];
    if (activePath && activeHandle) {
      contextFiles.push({ path: activePath, content });
    }
    for (const entry of matchContextFiles(text, files, activePath)) {
      try {
        contextFiles.push({ path: entry.path, content: await readText(entry.handle) });
      } catch {
        /* skip */
      }
    }

    try {
      const res = await api.codeAssist(text, {
        projectRoot: dirName,
        projectFiles: files.map((f) => f.path),
        filePath: activePath,
        fileContent: activePath ? content : "",
        contextFiles,
        history,
      });
      const reply = (res.reply || t.common.noData).trim();
      persistMessages([...nextMsgs, { role: "assistant" as const, content: reply }], dirName);
      if (res.edits?.length) await applyEdits(res.edits);
    } catch (err) {
      const msg = formatUserFacingError(err instanceof Error ? err.message : t.common.noData);
      persistMessages([...nextMsgs, { role: "assistant" as const, content: msg }], dirName);
    } finally {
      setAiLoading(false);
    }
  };

  const hasProject = Boolean(dirName && files.length);

  return (
    <div className="code-workspace flex h-full min-h-0 flex-col bg-mimo-warm">
      <div className="flex shrink-0 items-center gap-2 border-b border-mimo-border bg-white px-3 py-2">
        <button
          type="button"
          className="mimo-btn-cta mimo-btn-sm inline-flex items-center gap-1.5"
          onClick={() => void pickFolder()}
        >
          <FolderOpen size={14} />
          {c.openProject}
        </button>
        <span className="truncate text-xs text-mimo-muted">{dirName || c.noFolder}</span>
        {!agentOpen && (
          <button
            type="button"
            className="ml-auto inline-flex items-center gap-1 rounded-lg border border-mimo-border px-2 py-1 text-xs text-mimo-muted hover:bg-mimo-warm"
            onClick={() => setAgentOpen(true)}
          >
            <PanelRightOpen size={14} />
            {c.expandAgent}
          </button>
        )}
      </div>

      {!hasProject ? (
        <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white shadow-sm ring-1 ring-mimo-border">
            <Sparkles size={32} className="text-mimo-accent" strokeWidth={1.25} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-mimo-text">{c.welcomeTitle}</h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-mimo-muted">{c.welcomeDesc}</p>
          </div>
          <button
            type="button"
            className="mimo-btn-cta inline-flex items-center gap-2 px-4 py-2 text-sm"
            onClick={() => void pickFolder()}
          >
            <FolderOpen size={16} />
            {c.openProject}
          </button>
        </div>
      ) : (
        <div ref={layoutRef} className="flex min-h-0 flex-1">
          <aside className="flex w-[220px] shrink-0 flex-col border-r border-mimo-border bg-white">
            <p className="border-b border-mimo-border px-3 py-2 text-[11px] font-medium uppercase tracking-wide text-mimo-muted">
              {c.files}
            </p>
            <ul className="min-h-0 flex-1 overflow-y-auto text-xs">
              {files.map((f) => (
                <li key={f.path}>
                  <button
                    type="button"
                    className={`flex w-full items-center gap-1 truncate px-3 py-1.5 text-left hover:bg-mimo-warm ${
                      activePath === f.path ? "bg-mimo-warm font-medium text-mimo-text" : "text-mimo-muted"
                    }`}
                    onClick={() => void openFile(f.path, f.handle)}
                  >
                    <ChevronRight size={12} className="shrink-0 opacity-40" />
                    {f.path}
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
            {activePath ? (
              <>
                <div className="flex items-center gap-1 border-b border-mimo-border bg-mimo-warm/50 px-2 py-1">
                  <div className="flex min-w-0 flex-1 items-center gap-2 rounded-md bg-white px-2 py-1 text-xs ring-1 ring-mimo-border">
                    <span className="truncate font-mono">{activePath}</span>
                    <button
                      type="button"
                      className="shrink-0 rounded p-0.5 text-mimo-muted hover:bg-mimo-warm hover:text-mimo-text"
                      aria-label={c.closeFile}
                      title={c.closeFile}
                      onClick={closeFile}
                    >
                      <X size={14} />
                    </button>
                  </div>
                  <button
                    type="button"
                    className="inline-flex shrink-0 items-center gap-1 rounded-md border border-mimo-border px-2 py-1 text-xs hover:bg-mimo-warm"
                    onClick={() => void saveFile()}
                  >
                    <Save size={12} />
                    {saved ? c.saved : c.save}
                  </button>
                </div>
                <textarea
                  className="min-h-0 flex-1 resize-none border-0 bg-[#fafafa] p-4 font-mono text-xs leading-6 text-mimo-text outline-none"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  spellCheck={false}
                />
              </>
            ) : (
              <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-8 text-center">
                <p className="text-sm text-mimo-muted">{c.emptyEditor}</p>
                <p className="mt-2 max-w-sm text-xs leading-5 text-mimo-muted">{c.agentHint}</p>
              </div>
            )}
          </div>

          {agentOpen && (
            <>
              <div
                className="code-agent-resize w-1 shrink-0 cursor-col-resize bg-mimo-border hover:bg-mimo-accent/40"
                onMouseDown={startResize}
                role="separator"
                aria-orientation="vertical"
              />
              <aside
                className="flex min-h-0 shrink-0 flex-col border-l border-mimo-border bg-white"
                style={{ width: agentWidth }}
              >
                <div className="flex items-center gap-2 border-b border-mimo-border px-3 py-2">
                  <Sparkles size={14} className="text-mimo-accent" />
                  <span className="min-w-0 flex-1 truncate text-xs font-medium">{c.agentPanel}</span>
                  <button
                    type="button"
                    className="rounded p-1 text-mimo-muted hover:bg-mimo-warm"
                    aria-label={c.collapseAgent}
                    onClick={() => setAgentOpen(false)}
                  >
                    <PanelRightClose size={16} />
                  </button>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
                  {messages.length === 0 && (
                    <div className="rounded-xl border border-dashed border-mimo-border bg-mimo-warm/50 px-4 py-6 text-center">
                      <p className="text-xs leading-6 text-mimo-muted">{c.agentHint}</p>
                    </div>
                  )}
                  <div className="space-y-4">
                    {messages.map((m, i) => (
                      <div
                        key={`${sessionId}-${i}`}
                        className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`max-w-[95%] rounded-2xl px-3.5 py-2.5 text-xs leading-6 ${
                            m.role === "user"
                              ? "bg-mimo-cta text-white"
                              : "bg-mimo-warm text-mimo-text ring-1 ring-mimo-border/60"
                          }`}
                        >
                          {m.role === "assistant" ? (
                            <ChatMessageContent text={m.content} />
                          ) : (
                            m.content
                          )}
                        </div>
                      </div>
                    ))}
                    {aiLoading && (
                      <div className="flex items-center gap-2 text-xs text-mimo-muted">
                        <Loader2 size={14} className="animate-spin text-mimo-accent" />
                        {c.aiThinking}
                      </div>
                    )}
                  </div>
                  <div ref={aiEndRef} />
                </div>

                {aiNotice && (
                  <p className="border-t border-mimo-border px-3 py-2 text-[11px] text-mimo-accent">{aiNotice}</p>
                )}

                <form
                  className="border-t border-mimo-border bg-mimo-warm/30 p-3"
                  onSubmit={(e) => void sendAi(e)}
                >
                  <div className="rounded-xl border border-mimo-border bg-white shadow-sm focus-within:ring-2 focus-within:ring-mimo-accent/25">
                    <textarea
                      className="w-full resize-none border-0 bg-transparent px-3 py-2.5 text-xs leading-5 outline-none"
                      rows={3}
                      placeholder={c.aiPlaceholder}
                      value={aiInput}
                      onChange={(e) => setAiInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          void sendAi();
                        }
                      }}
                    />
                    <div className="flex justify-end border-t border-mimo-border/60 px-2 py-1.5">
                      <button
                        type="submit"
                        disabled={aiLoading || !aiInput.trim()}
                        className="inline-flex items-center gap-1 rounded-lg bg-mimo-cta px-3 py-1.5 text-xs font-medium text-white disabled:opacity-40"
                      >
                        {aiLoading ? <Loader2 size={14} className="animate-spin" /> : <SendHorizonal size={14} />}
                        {c.aiSend}
                      </button>
                    </div>
                  </div>
                </form>
              </aside>
            </>
          )}
        </div>
      )}
    </div>
  );
}
