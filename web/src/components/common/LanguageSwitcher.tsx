import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useLocale } from "@/context/LocaleContext";
import type { Locale } from "@/lib/i18n";

const OPTIONS: { id: Locale; label: string }[] = [
  { id: "zh", label: "中文" },
  { id: "en", label: "English" },
];

export function LanguageSwitcher({ className = "" }: { className?: string }) {
  const { locale, setLocale } = useLocale();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const current = OPTIONS.find((o) => o.id === locale)?.label ?? "中文";

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        type="button"
        className="mimo-nav-link inline-flex items-center gap-0.5"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {current}
        <ChevronDown size={14} className={`opacity-50 transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="mimo-lang-menu">
          {OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              className={`mimo-lang-option ${locale === opt.id ? "mimo-lang-option-active" : ""}`}
              onClick={() => {
                setLocale(opt.id);
                setOpen(false);
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
