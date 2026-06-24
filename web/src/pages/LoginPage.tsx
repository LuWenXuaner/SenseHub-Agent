import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Eye, EyeOff, Loader2, Lock, Mail, Moon, Sparkles, Sun, User } from "lucide-react";
import { NebulaBackground } from "@/components/auth/NebulaBackground";
import { api, getRememberMe } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/hooks/useTheme";
import { useLocale } from "@/context/LocaleContext";

type Mode = "login" | "register" | "forgot";

function isValidUsername(name: string) {
  return /^[a-zA-Z0-9_]{3,20}$/.test(name);
}

export function LoginPage() {
  const [mode, setMode] = useState<Mode>("login");
  const [inviteCode, setInviteCode] = useState("");
  const [account, setAccount] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [rememberMe, setRememberMe] = useState(getRememberMe);
  const [error, setError] = useState("");
  const [hint, setHint] = useState("");
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const { login, register } = useAuth();
  const { toggle, mode: themeMode } = useTheme();
  const { t, fmt } = useLocale();
  const L = t.login;
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTo = searchParams.get("redirect");
  const afterAuth = redirectTo?.startsWith("/") ? redirectTo : "/";

  useEffect(() => {
    document.title =
      mode === "login" ? L.pageLogin : mode === "register" ? L.pageRegister : L.pageForgot;
  }, [mode, L.pageLogin, L.pageRegister, L.pageForgot]);

  useEffect(() => {
    const invite = searchParams.get("invite");
    if (invite) {
      setInviteCode(invite.trim().toUpperCase());
      setMode("register");
      setHint(fmt(L.inviteHint, { code: invite.trim().toUpperCase() }));
    }
  }, [searchParams, L.inviteHint, fmt]);

  useEffect(() => {
    api.authStatus().catch(() => setError(L.errConnect));
  }, [L.errConnect]);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError("");
    setHint("");
    setCode("");
    setConfirm("");
  };

  const sendCode = async (purpose: "register" | "reset") => {
    const addr = email.trim().toLowerCase();
    if (!addr.includes("@")) {
      setError(L.errEmail);
      return;
    }
    setSendingCode(true);
    setError("");
    try {
      const res = await api.sendEmailCode(addr, purpose);
      setHint(
        res.dev_code
          ? fmt(L.hintCodeDev, { code: res.dev_code, min: Math.floor(res.expires_in / 60) })
          : L.hintCodeSent
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : L.errSend);
    } finally {
      setSendingCode(false);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setHint("");

    if (mode === "login") {
      const id = account.trim();
      if (!id) {
        setError(L.errAccount);
        return;
      }
      setLoading(true);
      try {
        await login(id, password, rememberMe);
        navigate(afterAuth);
      } catch (err) {
        setError(err instanceof Error ? err.message : L.errLogin);
      } finally {
        setLoading(false);
      }
      return;
    }

    const addr = email.trim().toLowerCase();
    if (!addr.includes("@")) {
      setError(L.errEmail);
      return;
    }

    if (mode === "forgot") {
      if (!code.trim()) {
        setError(L.errCode);
        return;
      }
      if (password !== confirm) {
        setError(L.errPasswordMatch);
        return;
      }
      if (password.length < 6) {
        setError(L.errPasswordLen);
        return;
      }
      setLoading(true);
      try {
        await api.resetPassword({ email: addr, code: code.trim(), new_password: password });
        setHint(L.hintResetOk);
        switchMode("login");
        setPassword("");
        setConfirm("");
      } catch (err) {
        setError(err instanceof Error ? err.message : L.errReset);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (mode === "register") {
      const uname = username.trim().toLowerCase();
      if (uname && !isValidUsername(uname)) {
        setError(L.errUsername);
        return;
      }
      if (!code.trim()) {
        setError(L.errCode);
        return;
      }
      if (password !== confirm) {
        setError(L.errPasswordMatch);
        return;
      }
      if (password.length < 6) {
        setError(L.errPasswordLen);
        return;
      }
      setLoading(true);
      try {
        await register({
          email: addr,
          code: code.trim(),
          password,
          username: uname || undefined,
          invite_code: inviteCode.trim() || undefined,
        });
        navigate(afterAuth);
      } catch (err) {
        setError(err instanceof Error ? err.message : L.errRegister);
      } finally {
        setLoading(false);
      }
    }
  };

  const heading = mode === "login" ? L.loginTitle : mode === "register" ? L.registerTitle : L.forgotTitle;

  return (
    <div className="relative flex min-h-screen flex-col bg-background">
      <NebulaBackground />

      <button
        type="button"
        className="auth-theme-toggle"
        onClick={toggle}
        aria-label={L.toggleTheme}
      >
        {themeMode === "dark" ? <Sun size={20} /> : <Moon size={20} />}
      </button>

      <main className="relative z-10 flex flex-1 items-center justify-center px-4 py-10 sm:px-6">
        <div className="auth-card w-full max-w-[420px]">
          <div className="mb-8 flex items-center justify-center gap-2">
            <Sparkles className="text-primary" size={22} aria-hidden />
            <span className="text-sm font-semibold text-text-secondary">{L.brand}</span>
          </div>

          <header className="mb-8 text-center">
            <h1 className="text-3xl font-bold tracking-tight text-text-primary sm:text-4xl">
              {heading}
            </h1>
            {mode !== "forgot" && (
              <p className="mt-2 min-h-5 text-sm text-text-secondary">
                {mode === "login" ? L.loginSubtitle : L.registerSubtitle}
              </p>
            )}
            {mode === "forgot" && (
              <p className="mt-2 min-h-5 text-sm text-text-secondary">{L.forgotSubtitle}</p>
            )}
          </header>

          {mode !== "forgot" && (
            <div className="auth-tabs" role="tablist" aria-label="登录或注册">
              <button
                type="button"
                role="tab"
                aria-selected={mode === "login"}
                className={`auth-tab ${mode === "login" ? "auth-tab-active" : ""}`}
                onClick={() => switchMode("login")}
              >
                {L.tabLogin}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === "register"}
                className={`auth-tab ${mode === "register" ? "auth-tab-active" : ""}`}
                onClick={() => switchMode("register")}
              >
                {L.tabRegister}
              </button>
            </div>
          )}

          <form
            onSubmit={submit}
            className={`mt-6 auth-form ${mode === "register" ? "auth-form--register" : "auth-form--login"}`}
            noValidate
          >
            <div className="auth-form-body">
            {mode === "login" && (
              <>
              <div className="auth-field-group">
                <label htmlFor="account" className="auth-field-label">
                  {L.account}
                </label>
                <div className="auth-field-wrap">
                  <User size={18} className="auth-field-icon" aria-hidden />
                  <input
                    id="account"
                    type="text"
                    className="auth-field"
                    value={account}
                    onChange={(e) => setAccount(e.target.value)}
                    autoComplete="username"
                    required
                  />
                </div>
              </div>

            <div className="auth-field-group">
              <label htmlFor="password" className="auth-field-label">
                {L.password}
              </label>
              <div className="auth-field-wrap">
                <Lock size={18} className="auth-field-icon" aria-hidden />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  className="auth-field pr-14"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="auth-icon-btn"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? L.hidePassword : L.showPassword}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

              <div className="flex items-center justify-between gap-4">
                <label className="auth-checkbox">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                  />
                  <span>{L.remember}</span>
                </label>
                <button type="button" className="auth-link" onClick={() => switchMode("forgot")}>
                  {L.forgotLink}
                </button>
              </div>
              </>
            )}

            {mode === "register" && (
              <>
                <div className="auth-field-group">
                  <label htmlFor="username" className="auth-field-label">
                    {L.usernameOptional}
                  </label>
                  <div className="auth-field-wrap">
                    <User size={16} className="auth-field-icon" aria-hidden />
                    <input
                      id="username"
                      type="text"
                      className="auth-field"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      autoComplete="username"
                    />
                  </div>
                </div>

                <div className="auth-field-group">
                  <label htmlFor="inviteCode" className="auth-field-label">
                    {L.inviteCodeOptional}
                  </label>
                  <input
                    id="inviteCode"
                    type="text"
                    className="auth-field px-3"
                    value={inviteCode}
                    onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                    placeholder={L.inviteCodePlaceholder}
                  />
                </div>

                <div className="auth-field-group">
                  <label htmlFor="email" className="auth-field-label">
                    {L.email}
                  </label>
                  <div className="auth-field-wrap">
                    <Mail size={16} className="auth-field-icon" aria-hidden />
                    <input
                      id="email"
                      type="email"
                      className="auth-field"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="email"
                      required
                    />
                  </div>
                </div>

                <div className="auth-field-group">
                  <label htmlFor="code" className="auth-field-label">
                    {L.code}
                  </label>
                  <div className="flex gap-2">
                    <div className="auth-field-wrap min-w-0 flex-1">
                      <input
                        id="code"
                        className="auth-field px-3"
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        required
                      />
                    </div>
                    <button
                      type="button"
                      className="auth-code-btn shrink-0"
                      onClick={() => void sendCode("register")}
                      disabled={sendingCode}
                    >
                      {sendingCode ? (
                        <Loader2 size={14} className="animate-spin" aria-hidden />
                      ) : (
                        L.getCode
                      )}
                    </button>
                  </div>
                </div>

                <div className="auth-field-group">
                  <label htmlFor="password" className="auth-field-label">
                    {L.password}
                  </label>
                  <div className="auth-field-wrap">
                    <Lock size={16} className="auth-field-icon" aria-hidden />
                    <input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      className="auth-field pr-14"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete="new-password"
                      required
                    />
                    <button
                      type="button"
                      className="auth-icon-btn"
                      onClick={() => setShowPassword((v) => !v)}
                      aria-label={showPassword ? L.hidePassword : L.showPassword}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                <div className="auth-field-group">
                  <label htmlFor="confirm" className="auth-field-label">
                    {L.confirmPassword}
                  </label>
                  <div className="auth-field-wrap">
                    <Lock size={16} className="auth-field-icon" aria-hidden />
                    <input
                      id="confirm"
                      type={showConfirm ? "text" : "password"}
                      className="auth-field pr-14"
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      autoComplete="new-password"
                      required
                    />
                    <button
                      type="button"
                      className="auth-icon-btn"
                      onClick={() => setShowConfirm((v) => !v)}
                      aria-label={showConfirm ? L.hidePassword : L.showPassword}
                    >
                      {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
              </>
            )}

            {mode === "forgot" && (
              <>
              <div className="auth-field-group">
                <label htmlFor="email" className="auth-field-label">
                  {L.email}
                </label>
                <div className="auth-field-wrap">
                  <Mail size={18} className="auth-field-icon" aria-hidden />
                  <input
                    id="email"
                    type="email"
                    className="auth-field"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                  />
                </div>
              </div>

              <div className="auth-field-group">
                <label htmlFor="code" className="auth-field-label">
                  {L.code}
                </label>
                <div className="flex gap-2">
                  <div className="auth-field-wrap min-w-0 flex-1">
                    <input
                      id="code"
                      className="auth-field px-4"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      required
                    />
                  </div>
                  <button
                    type="button"
                    className="auth-code-btn shrink-0"
                    onClick={() => void sendCode("reset")}
                    disabled={sendingCode}
                  >
                    {sendingCode ? (
                      <Loader2 size={16} className="animate-spin" aria-hidden />
                    ) : (
                      L.getCode
                    )}
                  </button>
                </div>
              </div>

            <div className="auth-field-group">
              <label htmlFor="password" className="auth-field-label">
                {L.newPassword}
              </label>
              <div className="auth-field-wrap">
                <Lock size={18} className="auth-field-icon" aria-hidden />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  className="auth-field pr-14"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
                <button
                  type="button"
                  className="auth-icon-btn"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? L.hidePassword : L.showPassword}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

              <div className="auth-field-group">
                <label htmlFor="confirm" className="auth-field-label">
                  {L.confirmPassword}
                </label>
                <div className="auth-field-wrap">
                  <Lock size={18} className="auth-field-icon" aria-hidden />
                  <input
                    id="confirm"
                    type={showConfirm ? "text" : "password"}
                    className="auth-field pr-14"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    autoComplete="new-password"
                    required
                  />
                  <button
                    type="button"
                    className="auth-icon-btn"
                    onClick={() => setShowConfirm((v) => !v)}
                    aria-label={showConfirm ? "隐藏密码" : "显示密码"}
                  >
                    {showConfirm ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>
              </>
            )}
            </div>

            <div className="auth-form-footer mt-5 space-y-5">
            {hint && <p className="auth-hint">{hint}</p>}
            {error && (
              <p className="auth-error" role="alert">
                {error}
              </p>
            )}

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" aria-hidden />
                  {L.loading}
                </>
              ) : mode === "register" ? (
                L.submitRegister
              ) : mode === "forgot" ? (
                L.submitReset
              ) : (
                L.submitLogin
              )}
            </button>

            {mode === "forgot" && (
              <p className="text-center text-sm text-text-secondary">
                <button type="button" className="auth-link" onClick={() => switchMode("login")}>
                  {L.backLogin}
                </button>
              </p>
            )}
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
