/** 官网内容 — 面向客户的正式商业文案 */

import {
  STUDIO_MODELS,
  getStudioModelBrandLabel,
  groupStudioModels,
  buildFlagshipApiModels,
  type StudioModelBrand,
  type StudioModelItem,
} from './modelCatalog';

export {
  STUDIO_MODELS,
  getStudioModelBrandLabel,
  groupStudioModels,
  type StudioModelBrand,
  type StudioModelItem,
};


export type NewsItem = {
  slug: string;
  title: string;
  summary: string;
  cta: string;
  ctaTo: string;
  date: string;
  body: string[];
};

export type FlagshipApiModel = {
  id: string;
  name: string;
  description: string;
  imageUrl: string;
  imageFallback: string;
  pricing: { label: string; value: string }[];
  badge?: string;
};

export type ProductMatrixItem = {
  id: string;
  title: string;
  summary: string;
  landingPath: string;
  appPath: string;
  cta: string;
  ctaStyle: "outline" | "primary";
};

export type EcosystemPartner = {
  id: string;
  name: string;
  fallback: string;
  iconUrl?: string;
  iconLocal?: boolean;
};

export type VoiceTag = {
  id: string;
  label: string;
  tier: 1 | 2;
  x: number;
  y: number;
  parentId?: string;
  driftX: number;
  driftY: number;
  delay: number;
  duration: number;
};

const brandLogo = (brand: "qwen" | "deepseek" | "doubao" | "glm" | "zhipu" | "audio") => {
  const logos: Record<string, string> = {
    qwen: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/qwen-color.png",
    deepseek: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/deepseek-color.png",
    doubao: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/doubao-color.png",
    glm: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/zhipu-color.png",
    zhipu: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/zhipu-color.png",
    audio: "https://www.google.com/s2/favicons?domain=siliconflow.cn&sz=256",
  };
  return logos[brand];
};

const favicon = (domain: string) =>
  `https://www.google.com/s2/favicons?domain=${domain}&sz=256`;

export const FLAGSHIP_API_MODELS = buildFlagshipApiModels();

export const PRODUCT_MATRIX: ProductMatrixItem[] = [
  {
    id: "code",
    title: "灵枢 Code",
    summary:
      "企业级本地编程助手。支持项目目录绑定、Agent / Plan 双工作流与自然语言改码，适用于日常研发协作。",
    landingPath: "/product/code",
    appPath: "/code",
    cta: "了解详情",
    ctaStyle: "outline",
  },
  {
    id: "console",
    title: "灵枢 Console",
    summary:
      "智能体工作台。以自然语言驱动桌面与浏览器自动化，覆盖日程、文件、网页等复杂任务的安全执行与全程审计。",
    landingPath: "/product/console",
    appPath: "/claw",
    cta: "立即体验",
    ctaStyle: "outline",
  },
  {
    id: "studio",
    title: "灵枢 Studio",
    summary:
      "多模态对话产品。支持文字、语音与视觉上下文，对接代采旗舰模型，满足创作、问答与业务沟通场景。",
    landingPath: "/product/studio",
    appPath: "/studio",
    cta: "立即体验",
    ctaStyle: "outline",
  },
  {
    id: "api",
    title: "灵枢 API",
    summary:
      "面向企业与开发者的模型接入服务。兼容 OpenAI / Anthropic 协议，稳定推理、透明计费、文档完备。",
    landingPath: "/product/api",
    appPath: "/console/api-keys",
    cta: "查看文档",
    ctaStyle: "outline",
  },
];

export const ECOSYSTEM_PARTNERS: EcosystemPartner[] = [
  { id: "sensehub", name: "灵枢 Code", fallback: "灵", iconLocal: true },
  { id: "opencode", name: "OpenCode", fallback: "OC", iconUrl: favicon("opencode.ai") },
  { id: "openclaw", name: "OpenClaw", fallback: "OC", iconUrl: favicon("openclaw.ai") },
  { id: "langgraph", name: "LangGraph", fallback: "LG", iconUrl: favicon("langchain.com") },
  { id: "cline", name: "Cline", fallback: "CL", iconUrl: favicon("cline.bot") },
  { id: "playwright", name: "Playwright", fallback: "PW", iconUrl: favicon("playwright.dev") },
  { id: "cherry", name: "Cherry Studio", fallback: "CS", iconUrl: favicon("cherry-ai.com") },
  { id: "qwen", name: "Qwen", fallback: "QW", iconUrl: favicon("qwen.ai") },
  { id: "deepseek", name: "DeepSeek", fallback: "DS", iconUrl: favicon("deepseek.com") },
  { id: "openai", name: "OpenAI", fallback: "AI", iconUrl: favicon("openai.com") },
];

/** Token Plan 编程工具 — 与首页生态图标同源（favicon） */
export const TOKEN_PLAN_CODING_TOOLS: EcosystemPartner[] = [
  { id: "opencode", name: "OpenCode", fallback: "OC", iconUrl: favicon("opencode.ai") },
  { id: "openclaw", name: "OpenClaw", fallback: "OC", iconUrl: favicon("openclaw.ai") },
  { id: "claude-code", name: "Claude Code", fallback: "CC", iconUrl: favicon("anthropic.com") },
  { id: "kilo", name: "Kilo Code", fallback: "KC", iconUrl: favicon("kilocode.ai") },
  { id: "cline", name: "Cline", fallback: "CL", iconUrl: favicon("cline.bot") },
  { id: "cherry", name: "Cherry Studio", fallback: "CS", iconUrl: favicon("cherry-ai.com") },
  { id: "qwen-code", name: "Qwen Code", fallback: "QW", iconUrl: favicon("qwen.ai") },
  { id: "cursor", name: "Cursor", fallback: "CU", iconUrl: favicon("cursor.com") },
];

export const VOICE_TAGS: VoiceTag[] = [
  { id: "hub-1", label: "强推理", tier: 1, x: 24, y: 36, driftX: 6, driftY: -5, delay: 0, duration: 5.5 },
  { id: "hub-2", label: "精准代码生成", tier: 1, x: 50, y: 18, driftX: -4, driftY: 6, delay: 0.4, duration: 6 },
  { id: "hub-3", label: "效率翻倍", tier: 1, x: 76, y: 32, driftX: 5, driftY: 4, delay: 0.8, duration: 5.2 },
  { id: "hub-4", label: "流畅体验", tier: 1, x: 68, y: 70, driftX: -6, driftY: -4, delay: 1.2, duration: 6.5 },
  { id: "hub-5", label: "超高性价比", tier: 1, x: 28, y: 72, driftX: 4, driftY: 5, delay: 0.6, duration: 5.8 },

  { id: "c-1", label: "理解业务", tier: 2, x: 10, y: 24, parentId: "hub-1", driftX: 3, driftY: -3, delay: 0.2, duration: 4.5 },
  { id: "c-2", label: "上下文精准", tier: 2, x: 12, y: 48, parentId: "hub-1", driftX: -3, driftY: 4, delay: 0.7, duration: 5 },
  { id: "c-3", label: "智能体工程", tier: 2, x: 8, y: 62, parentId: "hub-1", driftX: 4, driftY: 2, delay: 1.1, duration: 4.8 },

  { id: "c-4", label: "快速重构", tier: 2, x: 36, y: 8, parentId: "hub-2", driftX: -2, driftY: 3, delay: 0.3, duration: 5.2 },
  { id: "c-5", label: "批量修复", tier: 2, x: 58, y: 6, parentId: "hub-2", driftX: 3, driftY: -2, delay: 0.9, duration: 4.6 },
  { id: "c-6", label: "长任务稳定", tier: 2, x: 62, y: 22, parentId: "hub-2", driftX: -4, driftY: 3, delay: 1.4, duration: 5.5 },

  { id: "c-7", label: "极速生成", tier: 2, x: 90, y: 16, parentId: "hub-3", driftX: 2, driftY: 4, delay: 0.5, duration: 4.9 },
  { id: "c-8", label: "多任务协作", tier: 2, x: 92, y: 38, parentId: "hub-3", driftX: -3, driftY: -3, delay: 1.0, duration: 5.3 },
  { id: "c-9", label: "效率倍增", tier: 2, x: 84, y: 50, parentId: "hub-3", driftX: 4, driftY: 2, delay: 1.6, duration: 4.7 },

  { id: "c-10", label: "大上下文", tier: 2, x: 86, y: 58, parentId: "hub-4", driftX: -2, driftY: 5, delay: 0.4, duration: 5.6 },
  { id: "c-11", label: "多模态准确", tier: 2, x: 88, y: 78, parentId: "hub-4", driftX: 3, driftY: -4, delay: 0.8, duration: 4.4 },
  { id: "c-12", label: "长对话稳定", tier: 2, x: 54, y: 86, parentId: "hub-4", driftX: -5, driftY: 2, delay: 1.3, duration: 5.1 },

  { id: "c-13", label: "稳定低价", tier: 2, x: 10, y: 84, parentId: "hub-5", driftX: 3, driftY: -3, delay: 0.6, duration: 4.8 },
  { id: "c-14", label: "代采优惠", tier: 2, x: 16, y: 58, parentId: "hub-5", driftX: -4, driftY: 4, delay: 1.1, duration: 5.4 },
  { id: "c-15", label: "透明计费", tier: 2, x: 6, y: 72, parentId: "hub-5", driftX: 2, driftY: -5, delay: 1.7, duration: 4.6 },
];

export const SITE_NEWS: NewsItem[] = [
  {
    slug: "api-key-reseller",
    title: "旗舰模型 API 代采服务上线",
    summary:
      "订阅 Token Plan 即可使用灵枢代采的模型接口，价格低于官方渠道，按量透明计费。",
    cta: "了解详情",
    ctaTo: "/models",
    date: "2026-06-22",
    body: [
      "灵枢为企业与个人用户提供 Qwen、DeepSeek、Doubao 等主流模型的代采服务。",
      "无需分别注册多家供应商，一个账户即可调用，账单清晰可查。",
    ],
  },
  {
    slug: "console-launch",
    title: "灵枢 Console 正式发布",
    summary:
      "一站式智能体工作台上线，可帮您完成日程、文件、网页等多类日常任务的自动执行。",
    cta: "立即体验",
    ctaTo: "/console",
    date: "2026-06-21",
    body: [
      "Console 支持自然语言下达指令，灵枢将为您规划步骤并安全执行。",
      "敏感操作需您确认后才会进行，全程可查看执行记录。",
    ],
  },
  {
    slug: "studio-multimodal",
    title: "灵枢 Chat 多模态体验升级",
    summary:
      "Chat 现已支持语音与视觉交互，零门槛感受灵枢的对话与理解能力。",
    cta: "立即体验",
    ctaTo: "/studio",
    date: "2026-06-20",
    body: ["适合快速体验、演示汇报与话术验证，无需复杂配置即可开始对话。"],
  },
  {
    slug: "model-lineup-2026",
    title: "2026 旗舰模型矩阵全面扩容",
    summary:
      "新增 Qwen3.7、DeepSeek-V4、GPT-5.5、Claude 4.5、Grok 4.5 等主流系列，Chat 与模型广场同步上架。",
    cta: "查看模型",
    ctaTo: "/models",
    date: "2026-06-19",
    body: [
      "覆盖文本、代码、视觉、语音与长文档等场景，代采接入筹备中。",
      "已上线模型可立即在 Chat 中选择体验，其余型号标注即将上线。",
    ],
  },
  {
    slug: "chat-ui-upgrade",
    title: "灵枢 Chat 对话体验优化",
    summary: "全新头像与气泡样式、按品牌分组的模型选择器，对话区更清晰易读。",
    cta: "打开 Chat",
    ctaTo: "/studio",
    date: "2026-06-18",
    body: [
      "用户与 AI 消息视觉区分更明显，长文排版与段落间距已优化。",
      "模型菜单支持悬浮二级列表，快速切换不同厂商系列。",
    ],
  },
  {
    slug: "points-invite",
    title: "积分签到与邀请奖励上线",
    summary: "每日签到领积分，邀请好友注册双方均可获得奖励，可用于兑换档位与 API 额度。",
    cta: "积分中心",
    ctaTo: "/console/points",
    date: "2026-06-17",
    body: [
      "在控制台积分中心完成签到或分享邀请链接即可累积积分。",
      "积分可兑换 Lite / Pro / Max 档位及 API Token 包。",
    ],
  },
  {
    slug: "code-agent-beta",
    title: "灵枢 Code 本地项目助手公测",
    summary: "选择本地文件夹，用自然语言描述需求，Agent 直接修改项目文件。",
    cta: "体验 Code",
    ctaTo: "/code",
    date: "2026-06-16",
    body: [
      "支持 Chrome / Edge 本地目录访问，适合快速原型与脚本整理。",
      "对话历史按账号隔离，任务可多次迭代直至满意。",
    ],
  },
  {
    slug: "session-privacy",
    title: "会话数据隔离与安全加固",
    summary: "Chat、Console 历史会话按用户严格隔离，防止跨账号数据泄露。",
    cta: "了解详情",
    ctaTo: "/product/api",
    date: "2026-06-15",
    body: [
      "后端会话 API 全面校验用户归属，前端本地缓存按账号分桶存储。",
      "建议定期清理浏览器缓存并妥善保管登录凭证。",
    ],
  },
  {
    slug: "token-plan",
    title: "Token Plan 档位计划发布",
    summary:
      "Lite / Pro / Max 三档方案，覆盖从个人试用到企业级多模态的完整需求。",
    cta: "查看方案",
    ctaTo: "/console/points",
    date: "2026-06-18",
    body: [
      "Lite 适合初次体验；Pro 解锁语音与安全能力；Max 提供完整智能体与虚拟屏体验。",
    ],
  },
];

export const SHOWCASE_MODELS = FLAGSHIP_API_MODELS;

export function getNewsBySlug(slug: string): NewsItem | undefined {
  return SITE_NEWS.find((n) => n.slug === slug);
}
