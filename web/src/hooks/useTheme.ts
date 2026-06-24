import { useEffect, useState } from "react";

export type ThemeMode = "light" | "dark" | "system";

export function useTheme() {
  const [mode, setModeState] = useState<ThemeMode>(
    () => (localStorage.getItem("theme") as ThemeMode) || "system"
  );

  useEffect(() => {
    const root = document.documentElement;
    const apply = (dark: boolean) => {
      root.classList.toggle("dark", dark);
    };
    if (mode === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      apply(mq.matches);
      const fn = () => apply(mq.matches);
      mq.addEventListener("change", fn);
      return () => mq.removeEventListener("change", fn);
    }
    apply(mode === "dark");
  }, [mode]);

  const setMode = (m: ThemeMode) => {
    localStorage.setItem("theme", m);
    setModeState(m);
  };

  const toggle = () => setMode(mode === "dark" ? "light" : "dark");

  return { mode, setMode, toggle };
}
