import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api, clearToken, getRememberMe, getToken, setToken, setUnauthorizedHandler, LicenseInfo, UserProfile } from "@/lib/api";

interface AuthCtx {
  token: string | null;
  user: UserProfile | null;
  login: (account: string, password: string, rememberMe?: boolean) => Promise<void>;
  loginWithToken: (accessToken: string) => Promise<void>;
  register: (body: {
    email: string;
    code: string;
    password: string;
    username?: string;
    display_name?: string;
    invite_code?: string;
  }) => Promise<void>;
  logout: () => void;
  license: LicenseInfo | null;
  refreshLicense: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [token, setTok] = useState<string | null>(getToken());
  const [user, setUser] = useState<UserProfile | null>(null);
  const [license, setLicense] = useState<LicenseInfo | null>(null);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setTok(null);
      setLicense(null);
      setUser(null);
      navigate("/login", { replace: true });
    });
    return () => setUnauthorizedHandler(null);
  }, [navigate]);

  const refreshLicense = async () => {
    if (!getToken()) return;
    try {
      setLicense(await api.license());
    } catch {
      /* ignore */
    }
  };

  const refreshUser = async () => {
    if (!getToken()) return;
    try {
      setUser(await api.me());
    } catch {
      setUser(null);
    }
  };

  useEffect(() => {
    if (token) {
      refreshLicense();
      refreshUser();
    }
  }, [token]);

  const applyAuth = (access_token: string, profile?: UserProfile | null, rememberMe = true) => {
    setToken(access_token, rememberMe);
    setTok(access_token);
    if (profile) setUser(profile);
  };

  const login = async (account: string, password: string, rememberMe = getRememberMe()) => {
    const res = await api.login(account, password, rememberMe);
    applyAuth(res.access_token, res.user, rememberMe);
    await refreshLicense();
    if (!res.user) await refreshUser();
  };

  const loginWithToken = async (accessToken: string) => {
    applyAuth(accessToken);
    await refreshLicense();
    await refreshUser();
  };

  const register = async (body: {
    email: string;
    code: string;
    password: string;
    username?: string;
    display_name?: string;
    invite_code?: string;
  }) => {
    const res = await api.register(body);
    applyAuth(res.access_token, res.user);
    await refreshLicense();
  };

  const logout = () => {
    clearToken();
    setTok(null);
    setLicense(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{ token, user, login, loginWithToken, register, logout, license, refreshLicense, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside provider");
  return ctx;
}
