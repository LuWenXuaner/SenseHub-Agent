/** 官网内容 — 面向客户的正式商业文案 */

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

export const FLAGSHIP_API_MODELS: FlagshipApiModel[] = [
  {
    id: "qwen3-8b",
    name: "Qwen3-8B",
    badge: "热销",
    imageUrl: brandLogo("qwen"),
    imageFallback: favicon("qwen.ai"),
    description: "轻量高效文本模型，适合日常对话、办公自动化与高频指令场景。",
    pricing: [
      { label: "输入（灵枢价）", value: "60 积分 / 百万 Token" },
      { label: "输出（灵枢价）", value: "120 积分 / 百万 Token" },
      { label: "能力类型", value: "语言理解" },
    ],
  },
  {
    id: "qwen-vl",
    name: "Qwen2.5-VL-7B",
    badge: "视觉",
    imageUrl: brandLogo("qwen"),
    imageFallback: favicon("qwen.ai"),
    description: "视觉理解大模型，支持截图分析、屏幕识别与图文混合问答。",
    pricing: [
      { label: "输入（灵枢价）", value: "150 积分 / 百万 Token" },
      { label: "输出（灵枢价）", value: "300 积分 / 百万 Token" },
      { label: "能力类型", value: "视觉理解" },
    ],
  },
  {
    id: "qwen-72b",
    name: "Qwen2.5-72B",
    badge: "旗舰",
    imageUrl: brandLogo("qwen"),
    imageFallback: favicon("qwen.ai"),
    description: "大规模文本模型，擅长复杂推理、长文档理解与专业写作。",
    pricing: [
      { label: "输入（灵枢价）", value: "200 积分 / 百万 Token" },
      { label: "输出（灵枢价）", value: "400 积分 / 百万 Token" },
      { label: "能力类型", value: "语言理解" },
    ],
  },
  {
    id: "deepseek-v3",
    name: "DeepSeek-V3",
    badge: "推理",
    imageUrl: brandLogo("deepseek"),
    imageFallback: favicon("deepseek.com"),
    description: "强推理能力，适合复杂任务规划、代码生成与深度分析。",
    pricing: [
      { label: "输入（灵枢价）", value: "100 积分 / 百万 Token" },
      { label: "输出（灵枢价）", value: "200 积分 / 百万 Token" },
      { label: "能力类型", value: "语言理解" },
    ],
  },
  {
    id: "glm-4",
    name: "GLM-4-9B",
    badge: "语言",
    imageUrl: brandLogo("glm"),
    imageFallback: favicon("zhipuai.cn"),
    description: "智谱 GLM 系列，中文理解出色，适合办公文案与知识问答。",
    pricing: [
      { label: "输入（灵枢价）", value: "80 积分 / 百万 Token" },
      { label: "输出（灵枢价）", value: "160 积分 / 百万 Token" },
      { label: "能力类型", value: "语言理解" },
    ],
  },
  {
    id: "sensevoice",
    name: "SenseVoice",
    badge: "语音",
    imageUrl: brandLogo("audio"),
    imageFallback: favicon("siliconflow.cn"),
    description: "高精度语音识别模型，支持多语种转写与实时听写场景。",
    pricing: [
      { label: "计费（灵枢价）", value: "50 积分 / 分钟" },
      { label: "能力类型", value: "语音识别 ASR" },
      { label: "供应商", value: "硅基流动" },
    ],
  },
  {
    id: "cosyvoice",
    name: "CosyVoice",
    badge: "语音",
    imageUrl: brandLogo("audio"),
    imageFallback: favicon("siliconflow.cn"),
    description: "自然流畅的语音合成，支持多音色播报与对话朗读。",
    pricing: [
      { label: "计费（灵枢价）", value: "100 积分 / 万字符" },
      { label: "能力类型", value: "语音合成 TTS" },
      { label: "供应商", value: "硅基流动" },
    ],
  },
  {
    id: "doubao-lite",
    name: "Doubao Lite",
    badge: "高性价比",
    imageUrl: brandLogo("doubao"),
    imageFallback: favicon("volcengine.com"),
    description: "火山方舟高性价比模型，长上下文、响应快，适合日常批量任务。",
    pricing: [
      { label: "输入（灵枢价）", value: "30 积分 / 百万 Token" },
      { label: "输出（灵枢价）", value: "60 积分 / 百万 Token" },
      { label: "能力类型", value: "语言理解" },
    ],
  },
  {
    id: "doubao-pro",
    name: "Doubao 1.5 Pro",
    badge: "旗舰",
    imageUrl: brandLogo("doubao"),
    imageFallback: favicon("volcengine.com"),
    description: "火山方舟旗舰文本模型，综合能力强，适合复杂业务场景。",
    pricing: [
      { label: "输入（灵枢价）", value: "120 积分 / 百万 Token" },
      { label: "输出（灵枢价）", value: "240 积分 / 百万 Token" },
      { label: "能力类型", value: "语言理解" },
    ],
  },
  {
    id: "doubao-vision",
    name: "Doubao Vision",
    badge: "视觉",
    imageUrl: brandLogo("doubao"),
    imageFallback: favicon("volcengine.com"),
    description: "火山方舟视觉模型，支持图像理解、OCR 与多模态问答。",
    pricing: [
      { label: "输入（灵枢价）", value: "180 积分 / 百万 Token" },
      { label: "输出（灵枢价）", value: "360 积分 / 百万 Token" },
      { label: "能力类型", value: "视觉理解" },
    ],
  },
  {
    id: "doubao-embedding",
    name: "Doubao Embedding",
    badge: "向量",
    imageUrl: brandLogo("doubao"),
    imageFallback: favicon("volcengine.com"),
    description: "文本向量化模型，适用于语义检索、知识库与相似度匹配。",
    pricing: [
      { label: "计费（灵枢价）", value: "10 积分 / 百万 Token" },
      { label: "能力类型", value: "向量嵌入" },
      { label: "供应商", value: "火山方舟" },
    ],
  },
  {
    id: "doubao-tts",
    name: "Doubao TTS",
    badge: "语音",
    imageUrl: brandLogo("doubao"),
    imageFallback: favicon("volcengine.com"),
    description: "火山方舟语音合成，多种音色可选，适合播报与智能客服。",
    pricing: [
      { label: "计费（灵枢价）", value: "80 积分 / 万字符" },
      { label: "能力类型", value: "语音合成 TTS" },
      { label: "供应商", value: "火山方舟" },
    ],
  },
];

export const STUDIO_MODELS = [
  {
    id: "qwen3-8b",
    name: "Qwen3-8B",
    badge: "推荐",
    description: "轻量高效，日常对话与办公自动化首选",
  },
  {
    id: "qwen-vl",
    name: "Qwen2.5-VL",
    badge: "视觉",
    description: "全模态理解大模型，支持图文混合问答",
  },
  {
    id: "deepseek-v3",
    name: "DeepSeek-V3",
    badge: "推理",
    description: "强推理能力，适合复杂分析与创作",
  },
  {
    id: "doubao-pro",
    name: "Doubao 1.5 Pro",
    badge: "旗舰",
    description: "火山方舟旗舰模型，综合能力强",
  },
  {
    id: "sensevoice",
    name: "SenseVoice",
    badge: "语音",
    description: "语音识别大模型，支持多语种转写",
  },
  {
    id: "cosyvoice",
    name: "CosyVoice",
    badge: "语音",
    description: "语音合成大模型，自然流畅多音色",
  },
] as const;

export const PRODUCT_MATRIX: ProductMatrixItem[] = [
  {
    id: "code",
    title: "灵枢 Code",
    summary:
      "智能编程助手，帮助您更高效地阅读代码、生成方案与完成协作，让开发工作事半功倍。",
    landingPath: "/product/code",
    appPath: "/code",
    cta: "查看详情",
    ctaStyle: "outline",
  },
  {
    id: "console",
    title: "灵枢 Console",
    summary:
      "一站式智能体工作台。可帮您完成日程安排、文件整理、网页操作等复杂任务，真正替你执行。",
    landingPath: "/product/console",
    appPath: "/claw",
    cta: "立即体验",
    ctaStyle: "outline",
  },
  {
    id: "studio",
    title: "灵枢 Studio",
    summary:
      "零门槛对话体验。支持文字、语音与视觉多模态交互，随时感受灵枢的智能回复与理解能力。",
    landingPath: "/product/studio",
    appPath: "/studio",
    cta: "立即体验",
    ctaStyle: "outline",
  },
  {
    id: "api",
    title: "灵枢 API",
    summary:
      "面向企业与开发者的模型接入服务。标准接口、稳定推理、完整文档，快速集成至您的业务系统。",
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
    title: "灵枢 Studio 多模态体验升级",
    summary:
      "Studio 现已支持语音与视觉交互，零门槛感受灵枢的对话与理解能力。",
    cta: "立即体验",
    ctaTo: "/studio",
    date: "2026-06-20",
    body: ["适合快速体验、演示汇报与话术验证，无需复杂配置即可开始对话。"],
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
