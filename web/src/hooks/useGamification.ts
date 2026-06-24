import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, type GamificationSummary } from "@/lib/api";

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
      setData(await api.gamificationSummary());
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
      }
      return res;
    },
    []
  );

  return { data, loading, refresh, spinWheel, updateProfile };
}

export function applyStoredConsoleTheme() {
  const theme = localStorage.getItem("sensehub-console-theme");
  if (theme) document.documentElement.dataset.consoleTheme = theme;
}
