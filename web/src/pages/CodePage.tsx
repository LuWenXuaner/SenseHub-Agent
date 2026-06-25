import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Code2,
  FilePlus,
  FolderOpen,
  Loader2,
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
  Save,
  SendHorizonal,
  Sparkles,
  X,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { useCode } from "@/context/CodeContext";
import { ChatMessageContent } from "@/components/chat/ChatMessageContent";
import {
  AgentStudioAvatar,
  StudioAvatarPlaceholder,
  UserStudioAvatar,
} from "@/components/chat/StudioChatAvatar";
import { CodeAgentToolbar } from "@/components/code/CodeAgentToolbar";
import { CodeFileTree } from "@/components/code/CodeFileTree";
import { CodeMonacoEditor } from "@/components/code/CodeMonacoEditor";
import { buildFileTree } from "@/lib/codeFileTree";
import {
  createProjectFile,
  deleteProjectPath,
  listProjectFiles,
  loadLastActivePath,
  loadProjectHandle,
  matchContextFiles,
  readProjectText,
  saveLastActivePath,
  saveProjectHandle,
  supportsCodeProject,
  verifyProjectPermission,
  writeProjectFile,
  getProjectFileHandle,
  type CodeFileEntry,
} from "@/lib/codeProject";
import { api, type ChatTurn } from "@/lib/api";
import { formatUserFacingError } from "@/lib/thinkingTrace";
import { userStorageScope } from "@/lib/userScope";

const AGENT_MIN = 300;
const AGENT_MAX = 560;
const AGENT_DEFAULT = 380;

export function CodePage() {
  const { t } = useLocale();
  const c = t.code;
  const { user } = useAuth();
  const scope = userStorageScope(user?.username);
  const { messages, persistMessages, sessionId, mode, setMode, modelId, setModelId } = useCode();

  const [dirName, setDirName] = useState("");
  const [files, setFiles] = useState<CodeFileEntry[]>([]);
  const [activePath, setActivePath] = useState("");
  const [content, setContent] = useState("");
  const [activeHandle, setActiveHandle] = useState<FileSystemFileHandle | null>(null);
  const [saved, setSaved] = useState(false);
  const [aiInput, setAiInput] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiNotice, setAiNotice] = useState("");
  const [agentOpen, setAgentOpen] = useState(true);
  const [agentWidth, setAgentWidth] = useState(AGENT_DEFAULT);
  const [projectLoading, setProjectLoading] = useState(true);
  const [projectBound, setProjectBound] = useState(false);

  const dirHandleRef = useRef<FileSystemDirectoryHandle | null>(null);
  const aiEndRef = useRef<HTMLDivElement>(null);
  const layoutRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    aiEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, aiLoading]);

  const refreshFiles = useCallback(async () => {
    const root = dirHandleRef.current;
    if (!root) return [];
    const next = await listProjectFiles(root);
    setFiles(next);
    return next;
  }, []);

  const openFile = useCallback(
    async (path: string, handle: FileSystemFileHandle) => {
      const text = await readProjectText(handle, 512_000);
      setActivePath(path);
      setActiveHandle(handle);
      setContent(text);
      setSaved(false);
      saveLastActivePath(scope, path);
    },
    [scope]
  );

  const closeFile = useCallback(() => {
    setActivePath("");
    setActiveHandle(null);
    setContent("");
    setSaved(false);
    saveLastActivePath(scope, "");
  }, [scope]);

  const bindProject = useCallback(
    async (dir: FileSystemDirectoryHandle, notice?: string) => {
      dirHandleRef.current = dir;
      setDirName(dir.name);
      setProjectBound(true);
      const listed = await listProjectFiles(dir);
      setFiles(listed);
      closeFile();
      setAiNotice(notice || "");
      await saveProjectHandle(scope, dir);

      const lastPath = loadLastActivePath(scope);
      if (lastPath) {
        const entry = listed.find((f) => f.path === lastPath);
        if (entry) {
          await openFile(entry.path, entry.handle);
        }
      }
    },
    [closeFile, openFile, scope]
  );

  useEffect(() => {
    let cancelled = false;
    dirHandleRef.current = null;
    setProjectBound(false);
    setDirName("");
    setFiles([]);
    closeFile();
    setProjectLoading(true);

    (async () => {
      if (!supportsCodeProject()) {
        if (!cancelled) setProjectLoading(false);
        return;
      }
      try {
        const handle = await loadProjectHandle(scope);
        if (!handle || cancelled) return;
        const ok = await verifyProjectPermission(handle);
        if (!ok) {
          if (!cancelled) {
            setAiNotice(c.projectRestoreFailed);
            setTimeout(() => setAiNotice(""), 4000);
          }
          return;
        }
        if (!cancelled) {
          await bindProject(handle, c.projectRestored);
          setTimeout(() => setAiNotice(""), 3000);
        }
      } catch {
        if (!cancelled) {
          setAiNotice(c.projectRestoreFailed);
          setTimeout(() => setAiNotice(""), 4000);
        }
      } finally {
        if (!cancelled) setProjectLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [bindProject, closeFile, c.projectRestoreFailed, c.projectRestored, scope]);

  const pickFolder = async () => {
    if (!supportsCodeProject()) {
      alert(c.pickFolderHint);
      return;
    }
    try {
      const dir = await (
        window as unknown as Window & { showDirectoryPicker: () => Promise<FileSystemDirectoryHandle> }
      ).showDirectoryPicker();
      const ok = await verifyProjectPermission(dir);
      if (!ok) {
        alert(c.projectRestoreFailed);
        return;
      }
      await bindProject(dir);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      throw err;
    }
  };

  const saveFile = useCallback(async () => {
    if (!activeHandle) return;
    await writeProjectFile(activeHandle, content);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }, [activeHandle, content]);

  const createFile = async () => {
    const root = dirHandleRef.current;
    if (!root) return;
    const raw = window.prompt(c.newFilePrompt);
    if (!raw?.trim()) return;
    try {
      const entry = await createProjectFile(root, raw.trim(), "");
      const next = await refreshFiles();
      const found = next.find((f) => f.path === entry.path) ?? entry;
      await openFile(found.path, found.handle);
    } catch (err) {
      const code = err instanceof Error ? err.message : "";
      if (code === "exists") alert(c.newFileExists);
      else if (code === "invalid_path") alert(c.newFileInvalid);
      else throw err;
    }
  };

  const deletePath = useCallback(
    async (path: string, type: "file" | "dir") => {
      const root = dirHandleRef.current;
      if (!root) return;
      const msg =
        type === "dir"
          ? c.confirmDeleteFolder.replace("{path}", path)
          : c.confirmDeleteFile.replace("{path}", path);
      if (!window.confirm(msg)) return;

      try {
        await deleteProjectPath(root, path, type === "dir");
        if (type === "file" && activePath === path) {
          closeFile();
        } else if (type === "dir" && activePath && (activePath === path || activePath.startsWith(`${path}/`))) {
          closeFile();
        }
        await refreshFiles();
      } catch (err) {
        if (err instanceof DOMException && err.name === "NotAllowedError") {
          alert(c.projectRestoreFailed);
          return;
        }
        throw err;
      }
    },
    [activePath, c.confirmDeleteFile, c.confirmDeleteFolder, c.projectRestoreFailed, closeFile, refreshFiles]
  );

  const applyEdits = useCallback(
    async (edits: { path: string; content: string }[]) => {
      const root = dirHandleRef.current;
      if (!root) return;

      let applied = 0;
      for (const edit of edits) {
        let entry = files.find((f) => f.path === edit.path);
        if (!entry) {
          try {
            const handle = await getProjectFileHandle(root, edit.path, true);
            await writeProjectFile(handle, edit.content);
            applied += 1;
            if (activePath === edit.path) {
              setContent(edit.content);
              setSaved(true);
              setTimeout(() => setSaved(false), 2000);
            }
            continue;
          } catch {
            continue;
          }
        }
        await writeProjectFile(entry.handle, edit.content);
        applied += 1;
        if (activePath === edit.path) {
          setContent(edit.content);
          setSaved(true);
          setTimeout(() => setSaved(false), 2000);
        }
      }

      if (applied > 0) {
        await refreshFiles();
        setAiNotice(c.aiApplied.replace("{count}", String(applied)));
        setTimeout(() => setAiNotice(""), 3000);
      }
    },
    [activePath, c.aiApplied, files, refreshFiles]
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
    if (!dirHandleRef.current || !dirName) {
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
        contextFiles.push({ path: entry.path, content: await readProjectText(entry.handle) });
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
        mode,
        modelId: modelId === "auto" ? "" : modelId,
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

  const hasProject = projectBound && Boolean(dirName);
  const fileTree = useMemo(() => buildFileTree(files), [files]);

  const showAvatarFor = (role: "user" | "assistant", idx: number) => {
    if (idx === 0) return true;
    return messages[idx - 1]?.role !== role;
  };

  const loadingShowsAvatar =
    messages.length === 0 || messages[messages.length - 1]?.role !== "assistant";

  if (projectLoading && !hasProject) {
    return (
      <div className="flex h-full items-center justify-center bg-mimo-warm text-sm text-mimo-muted">
        <Loader2 size={18} className="mr-2 animate-spin text-mimo-accent" />
        {c.loadingProject}
      </div>
    );
  }

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
        {aiNotice && !hasProject && (
          <span className="truncate text-[11px] text-mimo-accent">{aiNotice}</span>
        )}
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
          <aside className="flex w-[240px] shrink-0 flex-col border-r border-mimo-border bg-white">
            <div className="flex items-center gap-1 border-b border-mimo-border px-2 py-2">
              <p className="min-w-0 flex-1 truncate text-[11px] font-medium uppercase tracking-wide text-mimo-muted">
                {c.files}
              </p>
              <button
                type="button"
                className="rounded p-1 text-mimo-muted hover:bg-mimo-warm hover:text-mimo-text"
                title={c.newFile}
                aria-label={c.newFile}
                onClick={() => void createFile()}
              >
                <FilePlus size={14} />
              </button>
              <button
                type="button"
                className="rounded p-1 text-mimo-muted hover:bg-mimo-warm hover:text-mimo-text"
                title={c.refreshFiles}
                aria-label={c.refreshFiles}
                onClick={() => void refreshFiles()}
              >
                <RefreshCw size={14} />
              </button>
            </div>
            {files.length === 0 ? (
              <p className="px-3 py-4 text-center text-mimo-muted">{c.emptyProject}</p>
            ) : (
              <CodeFileTree
                nodes={fileTree}
                activePath={activePath}
                onOpenFile={(path, handle) => void openFile(path, handle)}
                onDeletePath={(path, type) => void deletePath(path, type)}
                deleteFileLabel={c.deleteFile}
                deleteFolderLabel={c.deleteFolder}
              />
            )}
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
                <div className="min-h-0 flex-1">
                  <CodeMonacoEditor path={activePath} value={content} onChange={setContent} />
                </div>
              </>
            ) : (
              <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-8 text-center">
                <p className="text-sm text-mimo-muted">{c.emptyEditor}</p>
                <p className="mt-2 max-w-sm text-xs leading-5 text-mimo-muted">{c.agentHint}</p>
                <button
                  type="button"
                  className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-mimo-border px-3 py-1.5 text-xs hover:bg-mimo-warm"
                  onClick={() => void createFile()}
                >
                  <FilePlus size={14} />
                  {c.newFile}
                </button>
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
                className="code-agent-panel flex min-h-0 shrink-0 flex-col"
                style={{ width: agentWidth }}
              >
                <div className="code-agent-header flex items-center gap-2.5 px-3 py-2.5">
                  <span className="code-agent-header-icon" aria-hidden>
                    <Code2 size={15} strokeWidth={2} />
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[13px] font-semibold tracking-tight text-mimo-text">
                    {c.agentPanel}
                  </span>
                  <button
                    type="button"
                    className="code-agent-icon-btn"
                    aria-label={c.collapseAgent}
                    onClick={() => setAgentOpen(false)}
                  >
                    <PanelRightClose size={15} />
                  </button>
                </div>

                <CodeAgentToolbar
                  mode={mode}
                  modelId={modelId}
                  onModeChange={setMode}
                  onModelChange={setModelId}
                />

                <div className="code-agent-chat-scroll min-h-0 flex-1 overflow-y-auto px-3 py-3">
                  {messages.length === 0 && !aiLoading && (
                    <div className="code-agent-empty">
                      <span className="code-agent-empty-icon" aria-hidden>
                        <Code2 size={20} strokeWidth={1.5} />
                      </span>
                      <p className="text-[13px] font-medium text-mimo-text">{c.aiTitle}</p>
                      <p className="mt-1.5 text-[12px] leading-[1.65] text-mimo-muted">{c.agentHint}</p>
                    </div>
                  )}
                  <div className="code-agent-chat-list">
                    {messages.map((m, i) => {
                      const showAvatar = showAvatarFor(m.role, i);
                      const continued = !showAvatar;
                      return (
                        <article
                          key={`${sessionId}-${i}`}
                          className={`code-agent-chat-row ${
                            m.role === "user" ? "code-agent-chat-row-user" : ""
                          } ${continued ? "code-agent-chat-row-continued" : ""}`}
                        >
                          <div className="code-agent-avatar">
                            {showAvatar ? (
                              m.role === "user" ? (
                                <UserStudioAvatar />
                              ) : (
                                <AgentStudioAvatar />
                              )
                            ) : (
                              <StudioAvatarPlaceholder />
                            )}
                          </div>
                          <div
                            className={`code-agent-bubble ${
                              m.role === "user"
                                ? "code-agent-bubble-user"
                                : "code-agent-bubble-assistant"
                            }`}
                          >
                            {m.role === "assistant" ? (
                              <ChatMessageContent text={m.content} variant="studio" />
                            ) : (
                              <p className="whitespace-pre-wrap text-[13px] leading-[1.7]">{m.content}</p>
                            )}
                          </div>
                        </article>
                      );
                    })}
                    {aiLoading && (
                      <article
                        className={`code-agent-chat-row ${
                          loadingShowsAvatar ? "" : "code-agent-chat-row-continued"
                        }`}
                      >
                        <div className="code-agent-avatar">
                          {loadingShowsAvatar ? <AgentStudioAvatar /> : <StudioAvatarPlaceholder />}
                        </div>
                        <div className="code-agent-bubble code-agent-bubble-assistant">
                          <div className="inline-flex items-center gap-2 text-[13px] text-mimo-muted">
                            <Loader2 size={14} className="animate-spin text-mimo-accent" />
                            {c.aiThinking}
                          </div>
                        </div>
                      </article>
                    )}
                  </div>
                  <div ref={aiEndRef} />
                </div>

                {aiNotice && (
                  <p className="code-agent-notice border-t border-mimo-border/70 px-3 py-2 text-[11px] text-mimo-accent">
                    {aiNotice}
                  </p>
                )}

                <form className="code-agent-compose" onSubmit={(e) => void sendAi(e)}>
                  <div className="code-agent-input-wrap">
                    <textarea
                      className="code-agent-input"
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
                    <button
                      type="submit"
                      disabled={aiLoading || !aiInput.trim()}
                      className="code-agent-send-btn"
                      aria-label={c.aiSend}
                      title={c.aiSend}
                    >
                      {aiLoading ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <SendHorizonal size={16} />
                      )}
                    </button>
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
