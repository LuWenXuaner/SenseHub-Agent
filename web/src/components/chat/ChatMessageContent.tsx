import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type ChatMessageContentProps = {
  text: string;
  variant?: "default" | "studio";
};

export function ChatMessageContent({ text, variant = "default" }: ChatMessageContentProps) {
  const isStudio = variant === "studio";
  const rootClass = isStudio
    ? "chat-markdown chat-markdown-studio min-w-0 flex-1 text-mimo-text"
    : "chat-markdown min-w-0 flex-1 pt-1 leading-relaxed text-text-primary";

  return (
    <div className={rootClass}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => (
            <p className={isStudio ? "mb-3.5 last:mb-0 leading-[1.85]" : "mb-2 last:mb-0"}>{children}</p>
          ),
          ul: ({ children }) => (
            <ul
              className={
                isStudio
                  ? "mb-4 list-disc space-y-2 pl-5 last:mb-0 leading-[1.85]"
                  : "mb-2 list-disc space-y-1 pl-5 last:mb-0"
              }
            >
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol
              className={
                isStudio
                  ? "mb-4 list-decimal space-y-2 pl-5 last:mb-0 leading-[1.85]"
                  : "mb-2 list-decimal space-y-1 pl-5 last:mb-0"
              }
            >
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className={isStudio ? "leading-[1.85] pl-0.5" : "leading-relaxed"}>{children}</li>
          ),
          strong: ({ children }) => (
            <strong className={isStudio ? "font-semibold text-mimo-text" : "font-semibold text-text-primary"}>
              {children}
            </strong>
          ),
          h1: ({ children }) => (
            <h1 className={isStudio ? "mb-3 mt-1 text-base font-bold leading-snug" : "mb-2 text-base font-semibold"}>
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className={isStudio ? "mb-2.5 mt-3 text-sm font-bold leading-snug" : "mb-2 text-sm font-semibold"}>
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className={isStudio ? "mb-2 mt-2.5 text-sm font-semibold leading-snug" : "mb-1 text-sm font-medium"}>
              {children}
            </h3>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              className="text-primary underline-offset-2 hover:underline"
              target="_blank"
              rel="noreferrer"
            >
              {children}
            </a>
          ),
          code: ({ className, children }) => {
            const inline = !className;
            if (inline) {
              return (
                <code
                  className={
                    isStudio
                      ? "rounded bg-black/[0.04] px-1.5 py-0.5 text-[0.9em]"
                      : "rounded bg-surface-elevated px-1 py-0.5 text-[0.9em]"
                  }
                >
                  {children}
                </code>
              );
            }
            return (
              <code
                className={
                  isStudio
                    ? "block overflow-x-auto rounded-lg bg-black/[0.04] p-2.5 text-xs leading-relaxed"
                    : "block overflow-x-auto rounded-lg bg-surface-elevated p-2 text-xs"
                }
              >
                {children}
              </code>
            );
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
