import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { getMessage, formatMsg, type Locale, type MessageTree } from "@/lib/i18n";

const LOCALE_KEY = "sensehub-locale";

type LocaleCtx = {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: MessageTree;
  fmt: typeof formatMsg;
};

const LocaleContext = createContext<LocaleCtx | null>(null);

function readLocale(): Locale {
  const v = localStorage.getItem(LOCALE_KEY);
  return v === "en" ? "en" : "zh";
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(readLocale);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    localStorage.setItem(LOCALE_KEY, l);
    document.documentElement.lang = l === "zh" ? "zh-CN" : "en";
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
  }, [locale]);

  const t = getMessage(locale);

  return (
    <LocaleContext.Provider value={{ locale, setLocale, t, fmt: formatMsg }}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within LocaleProvider");
  return ctx;
}
