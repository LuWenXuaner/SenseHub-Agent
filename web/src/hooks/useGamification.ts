import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, type GamificationSummary } from "@/lib/api";
import { BG_STYLES } from "@/lib/gamificationCatalog";

export function applyStoredConsoleTheme() {
  const theme = localStorage.getItem("sensehub-console-theme");
  if (theme) document.documentElement.dataset.consoleTheme = theme;
}

export function applyStoredConsoleProfile(summary?: GamificationSummary | null) {
  const bg =
    summary?.profile.profile_bg || localStorage.getItem("sensehub-profile-bg") || "default";
  document.documentElement.dataset.profileBg = bg;
  const style = BG_STYLES[bg] ?? BG_STYLES.default;
  document.documentElement.style.setProperty("--console-profile-bg", style);
  if (summary?.profile.profile_theme) {
    document.documentElement.dataset.consoleTheme = summary.profile.profile_theme;
    localStorage.setItem("sensehub-console-theme", summary.profile.profile_theme);
  }
}

export function useGamification() {
  const { token } = useAuth();
  const [data, setData] = useState<GamificationSummary | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) {
      setData(null);
      return;
    }
    setLoading(true);
    try {
      const res = await api.gamificationSummary();
      setData(res);
      applyStoredConsoleProfile(res);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const spinWheel = useCallback(async () => {
    const res = await api.gamificationWheelSpin();
    await refresh();
    return res;
  }, [refresh]);

  const updateProfile = useCallback(
    async (patch: { profile_bg?: string; profile_theme?: string }) => {
      const res = await api.gamificationUpdateProfile(patch);
      setData(res);
      if (patch.profile_theme) {
        document.documentElement.dataset.consoleTheme = patch.profile_theme;
        localStorage.setItem("sensehub-console-theme", patch.profile_theme);
      }
      if (patch.profile_bg) {
        localStorage.setItem("sensehub-profile-bg", patch.profile_bg);
        document.documentElement.dataset.profileBg = patch.profile_bg;
        document.documentElement.style.setProperty(
          "--console-profile-bg",
          BG_STYLES[patch.profile_bg] ?? BG_STYLES.default
        );
      }
      return res;
    },
    []
  );

  return { data, loading, refresh, spinWheel, updateProfile };
}
