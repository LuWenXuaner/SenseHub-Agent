import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function ChatMessageContent({ text }: { text: string }) {
  return (
    <div className="chat-markdown min-w-0 flex-1 pt-1 leading-relaxed text-text-primary">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        strong: ({ children }) => <strong className="font-semibold text-text-primary">{children}</strong>,
        h1: ({ children }) => <h1 className="mb-2 text-base font-semibold">{children}</h1>,
        h2: ({ children }) => <h2 className="mb-2 text-sm font-semibold">{children}</h2>,
        h3: ({ children }) => <h3 className="mb-1 text-sm font-medium">{children}</h3>,
        a: ({ href, children }) => (
          <a href={href} className="text-primary underline-offset-2 hover:underline" target="_blank" rel="noreferrer">
            {children}
          </a>
        ),
        code: ({ className, children }) => {
          const inline = !className;
          if (inline) {
            return <code className="rounded bg-surface-elevated px-1 py-0.5 text-[0.9em]">{children}</code>;
          }
          return (
            <code className="block overflow-x-auto rounded-lg bg-surface-elevated p-2 text-xs">{children}</code>
          );
        },
      }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
