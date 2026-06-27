import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { useLocale } from "@/context/LocaleContext";

type Props = {
  text: string;
  className?: string;
};

export function MessageCopyButton({ text, className = "" }: Props) {
  const { t } = useLocale();
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    const value = text.trim();
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* ignore */
    }
  };

  return (
    <button
      type="button"
      className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] text-text-secondary transition hover:bg-border/50 hover:text-text-primary ${className}`}
      onClick={() => void onCopy()}
      title={t.common.copy}
      aria-label={t.common.copy}
    >
      {copied ? <Check size={12} aria-hidden /> : <Copy size={12} aria-hidden />}
      <span>{copied ? t.common.copied : t.common.copy}</span>
    </button>
  );
}
