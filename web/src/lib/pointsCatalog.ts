/** 积分规则与兑换目录 */

export const POINTS = {
  signInDaily: 20,
  signInStreakBonus: 50,
  signInStreakDays: 7,
  inviteRegister: 100,
  inviteMax: 30,
  inviteRebatePercent: 10,
  friendFirstRedeemDiscountPercent: 10,
  rebateValidDays: 40,
} as const;

export const EXCHANGE_CATALOG = [
  {
    id: "tier-lite",
    cost: 800,
    labelKey: "exchangeTierLite" as const,
    category: "tier" as const,
    descZh: "Lite 档位 7 天体验 · Console 基础执行",
    descEn: "Lite tier for 7 days · basic Console execution",
  },
  {
    id: "tier-pro",
    cost: 5000,
    labelKey: "exchangeTierPro" as const,
    category: "tier" as const,
    descZh: "Pro 档位 30 天 · 多模态 + 安全中心",
    descEn: "Pro tier for 30 days · multimodal + security",
  },
  {
    id: "tier-max",
    cost: 20000,
    labelKey: "exchangeTierMax" as const,
    category: "tier" as const,
    descZh: "Max 档位 30 天 · 多脑协作 + 自主 Agent",
    descEn: "Max tier for 30 days · multi-agent + autonomous",
  },
  {
    id: "api-qwen",
    cost: 800,
    labelKey: "exchangeApiQwen" as const,
    category: "api" as const,
    descZh: "Qwen3 系列 100 万 Token · Chat / Console",
    descEn: "1M tokens · Qwen3 for Chat / Console",
  },
  {
    id: "api-doubao",
    cost: 600,
    labelKey: "exchangeApiDoubao" as const,
    category: "api" as const,
    descZh: "Doubao 系列 100 万 Token · 规划脑",
    descEn: "1M tokens · Doubao for planner",
  },
  {
    id: "api-deepseek",
    cost: 700,
    labelKey: "exchangeApiDeepSeek" as const,
    category: "api" as const,
    descZh: "DeepSeek-V3 80 万 Token · 推理与代码",
    descEn: "800K tokens · DeepSeek-V3 reasoning & code",
  },
  {
    id: "api-qwen-vl",
    cost: 1200,
    labelKey: "exchangeApiQwenVL" as const,
    category: "api" as const,
    descZh: "Qwen2.5-VL 50 万 Token · 视觉理解",
    descEn: "500K tokens · Qwen2.5-VL vision",
  },
  {
    id: "api-whisper",
    cost: 500,
    labelKey: "exchangeApiWhisper" as const,
    category: "api" as const,
    descZh: "语音识别 120 分钟 · Console 语音指令",
    descEn: "120 min ASR · Console voice commands",
  },
  {
    id: "code-agent-boost",
    cost: 1500,
    labelKey: "exchangeCodeBoost" as const,
    category: "product" as const,
    descZh: "Code Agent 加量包 · 额外 500 次文件修改",
    descEn: "Code Agent boost · 500 extra file edits",
  },
  {
    id: "plugin-web",
    cost: 900,
    labelKey: "exchangePluginWeb" as const,
    category: "product" as const,
    descZh: "联网插件 30 天 · 搜索与网页解析",
    descEn: "Web plugin 30 days · search & page parse",
  },
  {
    id: "storage-workspace",
    cost: 400,
    labelKey: "exchangeStorage" as const,
    category: "product" as const,
    descZh: "工作区扩容 5 GB · 沙箱与日志",
    descEn: "Workspace +5 GB · sandbox & logs",
  },
  {
    id: "api-tts",
    cost: 450,
    labelKey: "exchangeApiTts" as const,
    category: "api" as const,
    descZh: "语音合成 30 万字符 · 执行反馈播报",
    descEn: "300K chars TTS · execution feedback",
  },
] as const;

export function formatPoints(n: number, locale: "zh" | "en"): string {
  return locale === "zh" ? `${n.toLocaleString()} 积分` : `${n.toLocaleString()} pts`;
}
