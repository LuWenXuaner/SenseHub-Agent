export type TierId = "lite" | "pro" | "max";

export type TierPlan = {
  id: TierId;
  name: string;
  tagline: string;
  price: string;
  priceNote: string;
  highlights: string[];
  limits: string;
};

/** 档位展示文案（对齐 docs/TIERS.md，UI 参考 MiMo 订阅卡片） */
export const TIER_PLANS: TierPlan[] = [
  {
    id: "lite",
    name: "Lite",
    tagline: "本地试用 · 自带 API Key",
    price: "免费",
    priceNote: "文本指令 20 次/日",
    highlights: ["桌面自动化", "摄像头预览", "L2 确认门控", "规则 ≤3 条"],
    limits: "需自行配置 OpenAI / DeepSeek / 硅基等兼容 API",
  },
  {
    id: "pro",
    name: "Pro",
    tagline: "多模态 · 局域网 · 无限指令",
    price: "订阅",
    priceNote: "文本指令不限",
    highlights: ["语音 + 手势规则", "安全中心 / 白名单", "Playwright 流程", "规则 ≤50 条"],
    limits: "适合个人深度使用与局域网控制台",
  },
  {
    id: "max",
    name: "Max",
    tagline: "虚拟屏 · 多脑协作 · 自主 Agent",
    price: "订阅",
    priceNote: "全能力解锁",
    highlights: ["虚拟屏空中点击", "AgentRuntime 多步 FC", "无限规则", "多脑 / 自主模式"],
    limits: "对标 OpenClaw / MiMo Claw 类 Agent 工作流",
  },
];

export const CAPABILITY_MATRIX = [
  { name: "文本 / 语音指令", lite: "20/日", pro: "无限", max: "无限" },
  { name: "LLM 提供商", lite: "自填 Key", pro: "自填 Key", max: "自填 Key" },
  { name: "桌面 + 浏览器自动化", lite: "✓", pro: "✓", max: "✓" },
  { name: "摄像头 / 规则", lite: "基础", pro: "完整", max: "完整" },
  { name: "虚拟屏", lite: "—", pro: "—", max: "✓" },
  { name: "审计 / 白名单", lite: "—", pro: "✓", max: "✓" },
];
