import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, type WalletSummary } from "@/lib/api";

export function useWallet() {
  const { token, refreshLicense, refreshUser } = useAuth();
  const [summary, setSummary] = useState<WalletSummary | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) {
      setSummary(null);
      return;
    }
    setLoading(true);
    try {
      setSummary(await api.walletSummary());
    } catch {
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const refreshAll = useCallback(async () => {
    await refresh();
    await Promise.all([refreshLicense(), refreshUser()]);
  }, [refresh, refreshLicense, refreshUser]);

  const checkIn = useCallback(async () => {
    const res = await api.walletCheckin();
    await refresh();
    return res;
  }, [refresh]);

  const redeem = useCallback(
    async (itemId: string) => {
      const res = await api.walletRedeem(itemId);
      await refreshAll();
      return res;
    },
    [refreshAll],
  );

  const subscribe = useCallback(
    async (plan: string) => {
      const res = await api.walletSubscribe(plan);
      await refreshAll();
      return res;
    },
    [refreshAll],
  );

  return {
    summary,
    loading,
    refresh,
    checkIn,
    redeem,
    subscribe,
    balance: summary?.balance ?? 0,
    totalEarned: summary?.total_earned ?? 0,
    canCheckIn: summary?.can_checkin ?? false,
  };
}
