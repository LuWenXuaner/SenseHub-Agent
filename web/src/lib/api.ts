const TOKEN_KEY = "sensehub_token";
const REMEMBER_KEY = "sensehub_remember";

export function getRememberMe(): boolean {
  return localStorage.getItem(REMEMBER_KEY) === "1";
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string, remember = true) {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  if (remember) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(REMEMBER_KEY, "1");
  } else {
    sessionStorage.setItem(TOKEN_KEY, token);
    localStorage.removeItem(REMEMBER_KEY);
  }
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REMEMBER_KEY);
}

let unauthorizedHandler: (() => void) | null = null;

/** 由 AuthProvider 注册，401 时走 React 路由而非整页刷新。 */
export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

function handleUnauthorized() {
  clearToken();
  if (unauthorizedHandler) {
    unauthorizedHandler();
  } else {
    window.location.href = "/login";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("未登录");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    const msg =
      typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : res.statusText;
    throw new Error(msg || "请求失败");
  }
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  authStatus: () => request<{ needs_setup: boolean; user_count: number }>("/api/auth/status"),
  oauthStatus: () =>
    request<{ github: boolean; qq: boolean; wechat: boolean }>("/api/auth/oauth/status"),
  sendEmailCode: (email: string, purpose = "register") =>
    request<{ email: string; sent: boolean; dev_code?: string; expires_in: number }>(
      "/api/auth/email/send-code",
      { method: "POST", body: JSON.stringify({ email, purpose }) }
    ),
  login: (account: string, password: string, rememberMe = false) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ account, password, remember_me: rememberMe }),
    }),
  resetPassword: (body: { email: string; code: string; new_password: string }) =>
    request<{ status: string }>("/api/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  register: (body: {
    email: string;
    code: string;
    password: string;
    username?: string;
    display_name?: string;
    invite_code?: string;
  }) =>
    request<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  oauthStart: (provider: "github" | "qq" | "wechat") =>
    request<{ url: string; provider: string }>(`/api/auth/oauth/${provider}/start`),
  me: () => request<UserProfile>("/api/auth/me"),
  changePassword: (old_password: string, new_password: string) =>
    request<{ status: string }>("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ old_password, new_password }),
    }),
  walletSummary: () => request<WalletSummary>("/api/wallet"),
  walletPlans: () =>
    fetch("/api/wallet/plans")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("failed"))))
      .then((d: { items: SubscriptionPlanRow[] }) => d),
  walletCheckin: () =>
    request<{ ok: boolean; earned: number; balance: number; streak?: number; weekend_double?: boolean }>(
      "/api/wallet/checkin",
      { method: "POST" }
    ),
  walletLedger: (filter: "all" | "earn" | "spend" = "all") =>
    request<{ items: PointsLedgerRow[] }>(`/api/wallet/ledger?filter=${filter}`),
  walletExchanges: () => request<{ items: ExchangeRow[] }>("/api/wallet/exchanges"),
  walletRedeem: (item_id: string) =>
    request<{
      ok: boolean;
      label: string;
      cost: number;
      balance: number;
      tier?: string;
      tier_expires_at?: string | null;
      tier_action?: string;
      subscription_active?: boolean;
    }>("/api/wallet/redeem", {
      method: "POST",
      body: JSON.stringify({ item_id }),
    }),
  walletSubscribe: (plan: string) =>
    request<{
      ok: boolean;
      label: string;
      cost: number;
      balance: number;
      tier?: string;
      tier_expires_at?: string | null;
      tier_action?: string;
      subscription_active?: boolean;
    }>("/api/wallet/subscribe", {
      method: "POST",
      body: JSON.stringify({ plan }),
    }),
  walletBills: () => request<{ summary: BillsSummary; items: BillRow[] }>("/api/wallet/bills"),
  walletTokenUsage: (days = 30) =>
    request<TokenUsageSummary>(`/api/wallet/token-usage?days=${days}`),
  gamificationSummary: () => request<GamificationSummary>("/api/gamification"),
  gamificationLeaderboard: (limit = 20) =>
    request<{ items: LeaderboardRow[] }>(`/api/gamification/leaderboard?limit=${limit}`),
  gamificationWheelSpin: () =>
    request<WheelSpinResult>("/api/gamification/wheel/spin", { method: "POST" }),
  gamificationUpdateProfile: (body: { profile_bg?: string; profile_theme?: string }) =>
    request<GamificationSummary>("/api/gamification/profile", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  invitesOverview: () => request<{ stats: InviteStats; items: InviteRow[] }>("/api/invites"),
  achievementShare: (achievementId: string, origin: string) =>
    request<AchievementShareResult>(
      `/api/gamification/achievements/${encodeURIComponent(achievementId)}/share`,
      { method: "POST", body: JSON.stringify({ origin }) }
    ),
  achievementSharePublic: (token: string) =>
    request<AchievementSharePublicView>(
      `/api/gamification/share/achievement/${encodeURIComponent(token)}`
    ),
  pluginsList: () => request<{ items: PluginRow[] }>("/api/plugins"),
  adminSearchUsers: (q = "") =>
    request<{ items: AdminUserRow[] }>(`/api/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  adminGrantPoints: (user_id: string, amount: number, note = "") =>
    request<{ ok: boolean; username: string; amount: number; balance: number }>(
      `/api/admin/users/${encodeURIComponent(user_id)}/grant-points`,
      { method: "POST", body: JSON.stringify({ amount, note }) },
    ),
  pluginToggle: (plugin_id: string, enabled: boolean) =>
    request<{ id: string; enabled: boolean }>(`/api/plugins/${plugin_id}`, {
      method: "PUT",
      body: JSON.stringify({ enabled }),
    }),
  getApiConfig: () => request<ApiConfigPublic>("/api/settings/api"),
  saveApiConfig: (body: Partial<ApiConfigUpdate>) =>
    request<ApiConfigPublic>("/api/settings/api", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  resetApiConfig: () => request<ApiConfigPublic>("/api/settings/api", { method: "DELETE" }),
  getConsoleSettings: () =>
    request<{ default_save_path: string; workspace: string }>("/api/settings/console"),
  saveConsoleSettings: (body: { default_save_path?: string }) =>
    request<{ default_save_path: string; workspace: string }>("/api/settings/console", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  pickConsoleSaveFolder: () =>
    request<{ cancelled: boolean; default_save_path?: string; workspace?: string; error?: string }>(
      "/api/settings/console/pick-folder",
      { method: "POST" }
    ),
  hubCommand: (text: string, signal?: AbortSignal, history?: ChatTurn[], sessionId?: string) =>
    request<HubCommandResult>("/api/hub/command", {
      method: "POST",
      body: JSON.stringify({ text, history: history ?? [], session_id: sessionId ?? "", channel: "hub" }),
      signal,
    }),
  studioChat: (
    text: string,
    signal?: AbortSignal,
    history?: ChatTurn[],
    sessionId?: string,
    modelId?: string
  ) =>
    request<{
      reply: string;
      session_id?: string;
      action: string;
      model_id?: string | null;
      model_used?: string | null;
      harness_trace?: import("@/lib/harnessTrace").HarnessTrace;
    }>("/api/studio/chat", {
      method: "POST",
      body: JSON.stringify({
        text,
        history: history ?? [],
        session_id: sessionId ?? "",
        model_id: modelId ?? "",
        channel: "studio",
      }),
      signal,
    }),
  codeAssist: (
    text: string,
    opts: {
      projectRoot?: string;
      projectFiles?: string[];
      filePath?: string;
      fileContent?: string;
      contextFiles?: { path: string; content: string }[];
      history?: ChatTurn[];
      modelId?: string;
      mode?: "agent" | "plan";
    } = {},
    signal?: AbortSignal
  ) =>
    request<{ reply: string; edits: { path: string; content: string }[]; action: string }>("/api/code/assist", {
      method: "POST",
      body: JSON.stringify({
        text,
        project_root: opts.projectRoot ?? "",
        project_files: opts.projectFiles ?? [],
        file_path: opts.filePath ?? "",
        file_content: opts.fileContent ?? "",
        context_files: opts.contextFiles ?? [],
        history: opts.history ?? [],
        model_id: opts.modelId ?? "",
        mode: opts.mode ?? "agent",
      }),
      signal,
    }),
  listSessions: (channel?: "hub" | "studio") =>
    request<{ sessions: ServerSession[] }>(
      channel ? `/api/sessions?channel=${channel}` : "/api/sessions"
    ),
  createSession: (title?: string, channel: "hub" | "studio" = "hub") =>
    request<{ session_id: string; title: string; channel?: string }>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ title: title ?? "", channel }),
    }),
  getSession: (sessionId: string) =>
    request<{ session: ServerSession; messages: ServerMessage[] }>(`/api/sessions/${sessionId}`),
  deleteSession: (sessionId: string) =>
    request<{ ok: boolean }>(`/api/sessions/${sessionId}`, { method: "DELETE" }),
  hubAutonomous: (text: string) =>
    request<HubCommandResult>("/api/hub/autonomous", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  virtualSessionStatus: () => request<VirtualSessionStatus>("/api/virtual-screen/session"),
  virtualSessionStart: () =>
    request<VirtualSessionStatus>("/api/virtual-screen/session/start", { method: "POST" }),
  virtualSessionStop: () =>
    request<VirtualSessionStatus>("/api/virtual-screen/session/stop", { method: "POST" }),
  virtualKeyboardToggle: (enabled: boolean) =>
    request<VirtualSessionStatus>(
      `/api/virtual-screen/keyboard/toggle?enabled=${enabled}`,
      { method: "POST" }
    ),
  virtualKeyboardKey: (key: string) =>
    request<{ ok: boolean }>("/api/virtual-screen/keyboard/key", {
      method: "POST",
      body: JSON.stringify({ key }),
    }),
  modelsConfig: () =>
    request<{
      chat: Record<string, string>;
      vision: Record<string, string>;
      planner: Record<string, string>;
      paths: Record<string, string>;
      inference_device: string;
      use_cuda: boolean;
    }>("/api/models/config"),
  createTask: (text: string) =>
    request<Task>("/api/tasks", { method: "POST", body: JSON.stringify({ text }) }),
  listTasks: () => request<Task[]>("/api/tasks"),
  getTask: (id: string) => request<Task>(`/api/tasks/${id}`),
  confirmTask: (id: string) =>
    request<Task>(`/api/tasks/${id}/confirm`, { method: "POST" }),
  cancelTask: (id: string) =>
    request<Task>(`/api/tasks/${id}/cancel`, { method: "POST" }),
  killSwitch: () => request<{ status: string }>("/api/kill-switch", { method: "POST" }),
  sandboxStatus: () =>
    request<{
      workspace: string;
      writable_roots: string[];
      readable_roots: string[];
      runtime_grants: string[];
      policy_whitelist: string[];
    }>("/api/security/sandbox"),
  grantSandboxPath: (path: string) =>
    request<{ ok: boolean; path: string; workspace: string }>("/api/security/sandbox/grant", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),
  license: () => request<LicenseInfo>("/api/license"),
  audit: () => request<AuditEntry[]>("/api/audit"),
  perceptionStatus: () => request<CameraStatus>("/api/perception/status"),
  cameraStart: () =>
    request<CameraStatus>("/api/perception/camera/start", { method: "POST" }),
  cameraStop: () =>
    request<CameraStatus>("/api/perception/camera/stop", { method: "POST" }),
  perceptionEvents: () => request<PerceptionEvent[]>("/api/perception/events"),
  listRules: () => request<Rule[]>("/api/rules"),
  createRule: (body: RuleCreate) =>
    request<Rule>("/api/rules", { method: "POST", body: JSON.stringify(body) }),
  updateRule: (id: string, body: RuleCreate) =>
    request<Rule>(`/api/rules/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteRule: (id: string) =>
    request<{ status: string }>(`/api/rules/${id}`, { method: "DELETE" }),
  transcribeVoice: async (blob: Blob) => {
    const token = getToken();
    const form = new FormData();
    form.append("audio", blob, "recording.webm");
    const res = await fetch("/api/voice/transcribe", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (res.status === 401) {
      handleUnauthorized();
      throw new Error("未登录");
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    return res.json() as Promise<VoiceTranscribeResult>;
  },
  voiceCommand: async (blob: Blob) => {
    const token = getToken();
    const form = new FormData();
    form.append("audio", blob, "recording.webm");
    const res = await fetch("/api/voice/command", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (res.status === 401) {
      handleUnauthorized();
      throw new Error("未登录");
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    return res.json() as Promise<VoiceCommandResult>;
  },
  voiceRunText: (text: string, signal?: AbortSignal, history?: ChatTurn[], sessionId?: string) =>
    request<VoiceCommandResult>("/api/voice/run", {
      method: "POST",
      body: JSON.stringify({ text, history: history ?? [], session_id: sessionId ?? "" }),
      signal,
    }),
  securityStatus: () =>
    request<{
      tier: string;
      allow_lan: boolean;
      ip_whitelist: string[];
      lan_access: boolean;
    }>("/api/security/status"),
  updateWhitelist: (ips: string[]) =>
    request<{ ips: string[] }>("/api/security/whitelist", {
      method: "PUT",
      body: JSON.stringify({ ips }),
    }),
  auditSummary: () =>
    request<{ count: number; recent: AuditEntry[] }>("/api/security/audit-summary"),
  ttsSpeak: (text: string) =>
    request<{ url?: string; skipped?: string; text?: string }>("/api/tts/speak", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  getVirtualCalibration: () =>
    request<VirtualCalibration>("/api/virtual-screen/calibration"),
  getVirtualCalibGrid: () =>
    request<{ points: number[][] }>("/api/virtual-screen/calib-grid"),
  saveVirtualCalibration: (
    screen_points: number[][],
    camera_points: number[][],
    frame_width = 0,
    frame_height = 0
  ) =>
    request<VirtualCalibration>("/api/virtual-screen/calibration", {
      method: "POST",
      body: JSON.stringify({ screen_points, camera_points, frame_width, frame_height }),
    }),
  previewVirtualMap: () =>
    request<{ ok: boolean; screen_x?: number; screen_y?: number; error?: string }>(
      "/api/virtual-screen/preview-map",
      { method: "POST" }
    ),
  perceptionConfig: () => request<Record<string, unknown>>("/api/perception/config"),
  patchPerceptionConfig: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/perception/config", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  perceptionContext: () => request<Record<string, unknown>>("/api/perception/context"),
  airClick: () =>
    request<{ x: number; y: number }>("/api/virtual-screen/air-click", { method: "POST" }),
  tunnelStatus: () =>
    request<{ enabled: boolean; status: string; message: string }>("/api/tunnel/status"),
  createMultiAgentTask: (text: string) =>
    request<Task>("/api/tasks/multi-agent", { method: "POST", body: JSON.stringify({ text }) }),
};

export interface PlanStep {
  step_id: number;
  tool: string;
  params: Record<string, unknown>;
  risk_level: string;
  description?: string;
}

export interface StepResult {
  step_id: number;
  success: boolean;
  output?: {
    method?: string;
    browser?: string;
    url?: string;
    query?: string;
    search?: string;
    message?: string;
    steps?: Array<{ step: number; action: string; thought?: string }>;
  };
  screenshot_path?: string;
  error?: string;
}

export interface Task {
  task_id: string;
  status: string;
  intent_text: string;
  summary?: string;
  plan_steps: PlanStep[];
  current_step: number;
  step_results: StepResult[];
  error?: string;
  needs_confirm?: boolean;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  task?: {
    task_id: string;
    intent_text: string;
    summary?: string;
    status?: string;
    plan_steps: PlanStep[];
    step_results: StepResult[];
  };
}

export interface LicenseInfo {
  tier: "lite" | "pro" | "max";
  text_commands_used: number;
  text_commands_limit: number | null;
  features: Record<string, boolean | number | null>;
  tier_expires_at?: string | null;
  subscription_active?: boolean;
  text_commands_unlimited?: boolean;
}

export interface CameraStatus {
  running: boolean;
  camera_index: number;
  detector_ready: boolean;
  yolo_weights: string;
  inference_device?: string;
  last_error?: string | null;
  fps: number;
}

export interface DetectionBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  confidence: number;
  label: string;
}

export interface PerceptionEvent {
  id?: number;
  timestamp: string;
  event_type: string;
  source: string;
  rule_id?: string | null;
  message: string;
  payload: Record<string, unknown>;
}

export interface RuleTrigger {
  type: string;
  event?: string;
  confidence_min?: number;
  match?: string;
  bypass_llm?: boolean;
}

export interface RuleAction {
  type: string;
  message?: string;
  steps?: Array<{ tool: string; params: Record<string, unknown> }>;
}

export interface Rule {
  rule_id: string;
  name: string;
  enabled: boolean;
  tier_min: string;
  trigger: RuleTrigger;
  action: RuleAction;
}

export interface RuleCreate {
  name: string;
  enabled: boolean;
  tier_min: string;
  trigger: RuleTrigger;
  action: RuleAction;
}

export interface VoiceTranscribeResult {
  text: string;
  duration_ms: number;
}

export interface VoiceCommandResult {
  text: string;
  matched: boolean;
  task_id?: string | null;
  session_id?: string;
  message: string;
  action?: string;
  reply?: string | null;
  agents?: Array<Record<string, unknown>>;
}

export interface AuditEntry {
  id: number;
  timestamp: string;
  input_text: string;
  action: string;
  result: string;
}

export interface VirtualCalibration {
  calibrated: boolean;
  screen_points: number[][];
  camera_points: number[][];
  matrix: number[][];
}

export interface UserProfile {
  username: string;
  display_name?: string;
  email?: string;
  public_id?: string;
  invite_code?: string;
  points_balance?: number;
}

export interface SubscriptionPlanRow {
  id: string;
  effective_tier: string;
  tier_rank: number;
  monthly_item_id: string;
  yearly_item_id: string;
  monthly_cost: number;
  yearly_cost: number;
  yearly_save: number;
  monthly_days: number;
  yearly_days: number;
  tier: string;
  monthly_label: string;
  yearly_label: string;
}

export interface WalletSummary {
  public_id: string;
  invite_code: string;
  balance: number;
  total_earned: number;
  total_spent: number;
  can_checkin: boolean;
  checkin_streak: number;
  tier: string;
  tier_expires_at?: string | null;
  subscription_active?: boolean;
  tier_rank?: number;
}

export interface LevelProgress {
  level: number;
  xp: number;
  current_floor: number;
  next_cap: number;
  progress_pct: number;
  rating_id: string;
  rating_name: string;
  max_level: number;
}

export interface AchievementRow {
  id: string;
  name: string;
  desc: string;
  icon: string;
  unlocked: boolean;
  unlocked_at?: string | null;
}

export interface CosmeticRow {
  id: string;
  name: string;
  unlocked: boolean;
  accent?: string;
}

export interface WheelStatus {
  free_spins_left: number;
  spin_cost: number;
  balance: number;
  prizes: { id: string; label: string; points: number }[];
}

export interface LeaderboardRow {
  rank: number;
  public_id: string;
  display_name: string;
  total_earned: number;
  level: number;
  rating_name: string;
}

export interface GamificationSummary {
  progress: LevelProgress;
  milestones: { level: number; points: number; label: string }[];
  achievements: AchievementRow[];
  backgrounds: CosmeticRow[];
  themes: CosmeticRow[];
  profile: { profile_bg: string; profile_theme: string };
  season: { id: string; name: string; active: boolean; start?: string; end?: string };
  weekend_double: boolean;
  wheel: WheelStatus;
  leaderboard_preview: LeaderboardRow[];
}

export interface WheelSpinResult {
  prize: { id: string; label: string; points: number };
  cost: number;
  balance: number;
}

export interface AchievementShareResult {
  token: string;
  share_url: string;
  share_text: string;
  card_url: string;
  achievement: { id: string; name: string; desc: string; icon: string };
}

export interface AchievementSharePublicView {
  achievement: {
    id: string;
    name: string;
    desc: string;
    icon: string;
    unlocked_at: string | null;
  };
  user: {
    display_name: string;
    public_id: string;
    level: number;
    rating_name: string;
  };
}

export interface PointsLedgerRow {
  id: number;
  delta: number;
  balance_after: number;
  entry_type: string;
  note: string;
  ref_id: string;
  created_at: string;
}

export interface ExchangeRow {
  id: number;
  item_id: string;
  item_label: string;
  cost: number;
  created_at: string;
}

export interface BillRow {
  id: number;
  bill_date: string;
  category: string;
  description: string;
  amount: number;
  unit: string;
  points_cost: number;
  created_at: string;
}

export interface BillsSummary {
  total_spent: number;
  token_usage: number;
  asr_seconds: number;
  plugin_calls: number;
}

export interface TokenUsageModelRow {
  role: string;
  provider: string;
  model: string;
  total_tokens: number;
  request_count: number;
}

export interface TokenUsageDailyRow {
  day: string;
  total_tokens: number;
  request_count: number;
}

export interface TokenUsageSummary {
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  request_count: number;
  by_model: TokenUsageModelRow[];
  daily: TokenUsageDailyRow[];
  range_days?: number;
}

export interface InviteStats {
  invited: number;
  earned: number;
  pending: number;
  rebate_total: number;
  invite_code: string;
  quota: number;
}

export interface AdminUserRow {
  user_id: string;
  username: string;
  display_name?: string;
  email?: string | null;
  created_at: string;
  public_id?: string | null;
  points_balance?: number | null;
  tier?: string | null;
  tier_expires_at?: string | null;
  invite_code?: string | null;
}

export interface InviteRow {
  id: number;
  invite_code: string;
  status: string;
  invitee_id: string;
  registered_at?: string;
  created_at: string;
}

export interface PluginRow {
  id: string;
  name: string;
  desc: string;
  enabled: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type?: string;
  user?: UserProfile | null;
}

export interface ProviderConfigPublic {
  id: string;
  label: string;
  base_url: string;
  api_key: string;
  configured: boolean;
  source: string;
  roles: string[];
  default_base_url: string;
}

export interface RoleConfigPublic {
  role: string;
  label_zh?: string;
  label_en?: string;
  provider: string;
  provider_label: string;
  model: string;
  default_provider?: string;
  default_model?: string;
  description?: string;
  description_zh?: string;
  description_en?: string;
  configured: boolean;
  user_override?: boolean;
}

export interface BrainPreset {
  id: string;
  label: string;
  provider: string;
  model: string;
}

export interface ApiConfigPublic {
  providers?: ProviderConfigPublic[];
  roles?: RoleConfigPublic[];
  role_routes?: Record<string, { provider: string; model: string }>;
  brain_presets?: BrainPreset[];
  siliconflow_api_key: string;
  volcengine_api_key: string;
  siliconflow_base_url: string;
  volcengine_base_url: string;
  planner_model: string;
  vision_model: string;
  chat_model: string;
  sources: Record<string, string>;
}

export interface ApiConfigUpdate {
  siliconflow_api_key?: string;
  volcengine_api_key?: string;
  siliconflow_base_url?: string;
  volcengine_base_url?: string;
  planner_model?: string;
  vision_model?: string;
  chat_model?: string;
  providers?: Record<string, { base_url?: string; api_key?: string }>;
  role_routes?: Record<string, { provider: string; model: string }>;
}

export interface HubCommandResult {
  handled: boolean;
  action?: string;
  message?: string;
  reply?: string | null;
  task_id?: string;
  session_id?: string;
  status?: VirtualSessionStatus;
  task?: Task;
  plan?: {
    summary?: string;
    steps?: Array<Record<string, unknown>>;
  };
  agents?: Array<Record<string, unknown>>;
}

export interface ServerSession {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ServerMessage {
  id: string;
  role: string;
  content: string;
  task_id?: string;
  meta?: Record<string, unknown>;
  created_at: string;
}

export interface VirtualSessionStatus {
  active: boolean;
  calibrated: boolean;
  mapping_mode?: "direct" | "homography";
  homography_calibrated?: boolean;
  show_keyboard: boolean;
  automation_suspended?: boolean;
  pointer?: { x: number; y: number };
}

export function screenshotUrl(path?: string): string | null {
  if (!path) return null;
  const name = path.split(/[/\\]/).pop();
  return name ? `/screenshots/${name}` : null;
}
