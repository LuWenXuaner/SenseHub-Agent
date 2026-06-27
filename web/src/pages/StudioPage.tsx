import { FormEvent, useMemo, useRef, useState } from "react";
import { Loader2, Paperclip, SendHorizonal, X } from "lucide-react";
import { api, type ChatTurn } from "@/lib/api";
import { formatUserFacingError } from "@/lib/thinkingTrace";
import {
  AgentStudioAvatar,
  StudioAvatarPlaceholder,
  UserStudioAvatar,
} from "@/components/chat/StudioChatAvatar";
import { ChatMessageContent } from "@/components/chat/ChatMessageContent";
import { MessageCopyButton } from "@/components/chat/MessageCopyButton";
import { useStudio } from "@/context/StudioContext";
import { useLocale } from "@/context/LocaleContext";

const EXAMPLE_PROMPTS_ZH = [
  "列出 5 个主打夏季穿搭的帖子标题",
  "给我的一条金毛起个霸气的名字",
  "我想吃点好的，10 块钱怎么吃",
];

const EXAMPLE_PROMPTS_EN = [
  "List 5 post titles for summer outfits",
  "Give my golden retriever a bold name",
  "What can I eat well with $2?",
];

type Attachment = { name: string; preview: string };

async function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(new Error("read failed"));
    reader.readAsText(file);
  });
}

export function StudioPage() {
  const { selectedModel, modelId, messages, persistMessages, sessions, sessionId } = useStudio();
  const { locale, t } = useLocale();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const endRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const prompts = locale === "en" ? EXAMPLE_PROMPTS_EN : EXAMPLE_PROMPTS_ZH;
  const canSend = useMemo(
    () => (input.trim().length > 0 || attachments.length > 0) && !loading,
    [input, loading, attachments.length]
  );
  const showWelcome = messages.length === 0 && !loading;

  const showAvatarFor = (role: "user" | "assistant", idx: number) => {
    if (idx === 0) return true;
    return messages[idx - 1]?.role !== role;
  };

  const loadingShowsAvatar =
    messages.length === 0 || messages[messages.length - 1]?.role !== "assistant";

  const scrollEnd = () => {
    requestAnimationFrame(() => endRef.current?.scrollIntoView({ behavior: "smooth" }));
  };

  const onPickFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    const next: Attachment[] = [];
    for (const file of Array.from(files).slice(0, 3)) {
      if (file.size > 512_000) continue;
      try {
        const text = await readFileAsText(file);
        const snippet = text.length > 4000 ? `${text.slice(0, 4000)}\n…` : text;
        next.push({ name: file.name, preview: snippet });
      } catch {
        next.push({ name: file.name, preview: `[${file.name}]` });
      }
    }
    setAttachments((prev) => [...prev, ...next].slice(0, 3));
    if (fileRef.current) fileRef.current.value = "";
  };

  const buildUserText = (text: string) => {
    if (!attachments.length) return text;
    const blocks = attachments.map((a) => `【${a.name}】\n${a.preview}`).join("\n\n");
    return text ? `${text}\n\n${blocks}` : blocks;
  };

  const onSend = async (e?: FormEvent, preset?: string) => {
    e?.preventDefault();
    const raw = (preset ?? input).trim();
    if ((!raw && !attachments.length) || loading) return;
    const text = buildUserText(raw);
    setInput("");
    setAttachments([]);
    const userMsg = { role: "user" as const, content: text };
    const nextMsgs = [...messages, userMsg];
    persistMessages(nextMsgs);
    setLoading(true);
    scrollEnd();
    try {
      const history: ChatTurn[] = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));
      const session = sessions.find((s) => s.id === sessionId);
      const res = await api.studioChat(
        text,
        undefined,
        history,
        session?.serverId ?? "",
        modelId
      );
      const reply = (res.reply || t.common.noData).trim();
      persistMessages([...nextMsgs, { role: "assistant", content: reply }]);
      if (res.session_id && session && !session.serverId) {
        session.serverId = res.session_id;
      }
    } catch (err) {
      persistMessages([
        ...nextMsgs,
        {
          role: "assistant",
          content: formatUserFacingError(err instanceof Error ? err.message : t.common.noData),
        },
      ]);
    } finally {
      setLoading(false);
      scrollEnd();
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      {showWelcome ? (
        <div className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-6 py-8 text-center md:px-12">
          <p className="text-xs text-mimo-muted">
            {selectedModel.name}
            {selectedModel.badge ? ` · ${selectedModel.badge}` : ""}
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-mimo-text md:text-3xl">
            {t.studio.title}
          </h1>
          <p className="mt-2 max-w-md text-sm leading-6 text-mimo-muted">{t.studio.tagline}</p>

          <p className="mt-8 text-xs text-mimo-muted">{t.studio.promptsTitle}</p>
          <div className="mt-3 grid w-full max-w-2xl gap-2 sm:grid-cols-3">
            {prompts.map((p) => (
              <button
                key={p}
                type="button"
                className="mimo-studio-prompt-card text-left text-sm"
                onClick={() => void onSend(undefined, p)}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <div className="mimo-studio-chat-area">
            {messages.map((m, idx) => {
              const showAvatar = showAvatarFor(m.role, idx);
              const continued = !showAvatar;
              return (
                <article
                  key={`${m.role}-${idx}`}
                  className={`mimo-studio-chat-row ${
                    m.role === "user" ? "mimo-studio-chat-row-user" : ""
                  } ${continued ? "mimo-studio-chat-row-continued" : ""}`}
                >
                  {showAvatar ? (
                    m.role === "user" ? (
                      <UserStudioAvatar />
                    ) : (
                      <AgentStudioAvatar />
                    )
                  ) : (
                    <StudioAvatarPlaceholder />
                  )}
                  <div
                    className={`mimo-studio-chat-bubble ${
                      m.role === "user"
                        ? "mimo-studio-chat-bubble-user"
                        : "mimo-studio-chat-bubble-assistant"
                    }`}
                  >
                    {m.role === "assistant" && (
                      <div className="mb-1 flex justify-end">
                        <MessageCopyButton text={m.content} />
                      </div>
                    )}
                    <ChatMessageContent text={m.content} variant={m.role === "assistant" ? "studio" : "default"} />
                  </div>
                </article>
              );
            })}
            {loading && (
              <article
                className={`mimo-studio-chat-row ${
                  loadingShowsAvatar ? "" : "mimo-studio-chat-row-continued"
                }`}
              >
                {loadingShowsAvatar ? <AgentStudioAvatar /> : <StudioAvatarPlaceholder />}
                <div className="mimo-studio-chat-bubble mimo-studio-chat-bubble-assistant">
                  <div className="inline-flex items-center gap-2 text-sm text-mimo-muted">
                    <Loader2 size={14} className="animate-spin" />
                    {t.studio.thinking}
                  </div>
                </div>
              </article>
            )}
            <div ref={endRef} />
          </div>
        </div>
      )}

      <div className="shrink-0 border-t border-mimo-border bg-mimo-surface px-4 py-3 md:px-8">
        {attachments.length > 0 && (
          <div className="mx-auto mb-2 flex max-w-3xl flex-wrap gap-2">
            {attachments.map((a) => (
              <span
                key={a.name}
                className="inline-flex items-center gap-1 rounded-full border border-mimo-border bg-mimo-warm px-2 py-0.5 text-xs"
              >
                <Paperclip size={12} />
                {a.name}
                <button
                  type="button"
                  className="rounded p-0.5 hover:bg-black/5"
                  onClick={() => setAttachments((prev) => prev.filter((x) => x.name !== a.name))}
                  aria-label={t.common.cancel}
                >
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
        <form onSubmit={onSend} className="mx-auto flex max-w-3xl items-end gap-2">
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            multiple
            accept=".txt,.md,.json,.csv,.py,.ts,.tsx,.js,.jsx,.yaml,.yml,.xml,.html,.css"
            onChange={(e) => void onPickFiles(e.target.files)}
          />
          <div className="mimo-studio-input-wrap flex-1">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="mimo-studio-input"
              placeholder={t.studio.inputPlaceholder}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (canSend) void onSend();
                }
              }}
            />
            <button
              type="button"
              className="mimo-studio-input-addon"
              aria-label={t.studio.attach}
              onClick={() => fileRef.current?.click()}
            >
              <Paperclip size={16} />
            </button>
          </div>
          <button type="submit" className="mimo-studio-send-btn" disabled={!canSend} aria-label={t.studio.send}>
            <SendHorizonal size={16} />
          </button>
        </form>
        <p className="mx-auto mt-2 max-w-3xl text-center text-[10px] leading-4 text-mimo-muted">
          {t.studio.disclaimer}
        </p>
      </div>
    </div>
  );
}
