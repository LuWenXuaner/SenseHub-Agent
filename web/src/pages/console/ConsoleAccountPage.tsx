import { Link } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { ConsolePageFrame } from "@/components/mimo/ConsolePageFrame";
import { useLocale } from "@/context/LocaleContext";
import { useWallet } from "@/hooks/useWallet";
import { useGamification } from "@/hooks/useGamification";
import { BG_STYLES, RATING_COLORS } from "@/lib/gamificationCatalog";
import { Medal } from "lucide-react";

export function ConsoleAccountPage() {
  const { user, license, logout } = useAuth();
  const { t } = useLocale();
  const { summary } = useWallet();
  const { data: game } = useGamification();
  const [oldPwd, setOldPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [pwdMsg, setPwdMsg] = useState("");
  const [pwdErr, setPwdErr] = useState("");

  const onChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdErr("");
    setPwdMsg("");
    if (newPwd !== confirmPwd) {
      setPwdErr(t.login.errPasswordMatch);
      return;
    }
    if (newPwd.length < 6) {
      setPwdErr(t.login.errPasswordLen);
      return;
    }
    try {
      await api.changePassword(oldPwd, newPwd);
      setPwdMsg(t.console.passwordChanged);
      setOldPwd("");
      setNewPwd("");
      setConfirmPwd("");
    } catch (err) {
      setPwdErr(err instanceof Error ? err.message : t.console.passwordFailed);
    }
  };

  const publicId = user?.public_id || summary?.public_id || "—";
  const email = user?.email || "—";
  const profileBg = game?.profile.profile_bg ?? localStorage.getItem("sensehub-profile-bg") ?? "default";
  const cardBg = BG_STYLES[profileBg] ?? BG_STYLES.default;
  const ratingColor = game ? RATING_COLORS[game.progress.rating_id] ?? "#c9a96e" : "#c9a96e";

  return (
    <ConsolePageFrame title={t.console.personalCenter} subtitle={t.console.accountSubtitle} centered>
      <div className="mimo-account-card" style={{ background: cardBg }}>
        {game && (
          <div className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-mimo-border/60 bg-white/70 px-3 py-2">
            <div className="flex items-center gap-2">
              <Medal size={18} style={{ color: ratingColor }} aria-hidden />
              <span className="text-sm font-medium">
                {game.progress.rating_name} Lv.{game.progress.level}
              </span>
            </div>
            <Link to="/console/engagement" className="text-xs text-[#1677ff] hover:underline">
              {t.gamification.hubLink}
            </Link>
          </div>
        )}
        <dl className="mimo-account-rows">
          <div className="mimo-account-row">
            <dt>{t.console.sensehubId}</dt>
            <dd>{publicId}</dd>
          </div>
          <div className="mimo-account-row">
            <dt>{t.console.email}</dt>
            <dd>{email}</dd>
          </div>
          <div className="mimo-account-row">
            <dt>{t.console.username}</dt>
            <dd>{user?.username ?? "—"}</dd>
          </div>
          <div className="mimo-account-row">
            <dt>{t.console.currentTier}</dt>
            <dd>{license?.tier?.toUpperCase() ?? summary?.tier?.toUpperCase() ?? "LITE"}</dd>
          </div>
        </dl>

        <form className="mt-8 space-y-3 border-t border-mimo-border pt-6 text-left" onSubmit={(e) => void onChangePassword(e)}>
          <h3 className="text-sm font-medium">{t.console.changePassword}</h3>
          <input
            className="mimo-console-input"
            type="password"
            placeholder={t.console.oldPassword}
            value={oldPwd}
            onChange={(e) => setOldPwd(e.target.value)}
          />
          <input
            className="mimo-console-input"
            type="password"
            placeholder={t.console.newPassword}
            value={newPwd}
            onChange={(e) => setNewPwd(e.target.value)}
          />
          <input
            className="mimo-console-input"
            type="password"
            placeholder={t.console.confirmPassword}
            value={confirmPwd}
            onChange={(e) => setConfirmPwd(e.target.value)}
          />
          {pwdMsg && <p className="text-sm text-mimo-accent">{pwdMsg}</p>}
          {pwdErr && <p className="text-sm text-danger">{pwdErr}</p>}
          <button type="submit" className="mimo-console-primary-btn mimo-btn-block">
            {t.console.savePassword}
          </button>
        </form>

        <div className="mimo-account-actions">
          <Link to="/console/token-plan" className="mimo-console-primary-btn mimo-btn-block">
            {t.console.viewDetail}
          </Link>
          <button type="button" className="mimo-console-outline-btn mimo-btn-block" onClick={() => logout()}>
            {t.common.logout}
          </button>
        </div>
      </div>
    </ConsolePageFrame>
  );
}
