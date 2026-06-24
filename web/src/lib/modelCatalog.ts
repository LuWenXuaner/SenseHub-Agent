/** Chat 可选模型目录 + 产品页旗舰模型生成 */

export type StudioModelBrand =
  | "qwen"
  | "deepseek"
  | "doubao"
  | "openai"
  | "claude"
  | "grok"
  | "gemini"
  | "audio";

export type StudioModelItem = {
  id: string;
  name: string;
  badge?: string;
  description: string;
  brand: StudioModelBrand;
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

export const STUDIO_MODEL_BRAND_ORDER: StudioModelBrand[] = [
  "qwen",
  "deepseek",
  "doubao",
  "openai",
  "claude",
  "grok",
  "gemini",
  "audio",
];

const BRAND_LABELS: Record<StudioModelBrand, { zh: string; en: string }> = {
  qwen: { zh: "通义千问 Qwen", en: "Qwen" },
  deepseek: { zh: "DeepSeek", en: "DeepSeek" },
  doubao: { zh: "豆包 Doubao", en: "Doubao" },
  openai: { zh: "OpenAI GPT", en: "OpenAI GPT" },
  claude: { zh: "Anthropic Claude", en: "Anthropic Claude" },
  grok: { zh: "xAI Grok", en: "xAI Grok" },
  gemini: { zh: "Google Gemini", en: "Google Gemini" },
  audio: { zh: "语音能力", en: "Voice" },
};

const brandLogo = (brand: StudioModelBrand) => {
  const map: Record<StudioModelBrand, string> = {
    qwen: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/qwen-color.png",
    deepseek: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/deepseek-color.png",
    doubao: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/doubao-color.png",
    openai: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/openai-color.png",
    claude: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/claude-color.png",
    grok: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/grok-color.png",
    gemini: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/gemini-color.png",
    audio: "https://www.google.com/s2/favicons?domain=siliconflow.cn&sz=256",
  };
  return map[brand];
};

const brandFavicon = (brand: StudioModelBrand) => {
  const map: Record<StudioModelBrand, string> = {
    qwen: "https://www.google.com/s2/favicons?domain=qwen.ai&sz=256",
    deepseek: "https://www.google.com/s2/favicons?domain=deepseek.com&sz=256",
    doubao: "https://www.google.com/s2/favicons?domain=volcengine.com&sz=256",
    openai: "https://www.google.com/s2/favicons?domain=openai.com&sz=256",
    claude: "https://www.google.com/s2/favicons?domain=anthropic.com&sz=256",
    grok: "https://www.google.com/s2/favicons?domain=x.ai&sz=256",
    gemini: "https://www.google.com/s2/favicons?domain=google.com&sz=256",
    audio: "https://www.google.com/s2/favicons?domain=siliconflow.cn&sz=256",
  };
  return map[brand];
};

const VENDOR: Record<StudioModelBrand, string> = {
  qwen: "通义千问",
  deepseek: "DeepSeek",
  doubao: "火山方舟",
  openai: "OpenAI",
  claude: "Anthropic",
  grok: "xAI",
  gemini: "Google",
  audio: "硅基流动",
};

export function getStudioModelBrandLabel(brand: StudioModelBrand, locale: "zh" | "en"): string {
  return BRAND_LABELS[brand][locale];
}

export function groupStudioModels(): { brand: StudioModelBrand; models: StudioModelItem[] }[] {
  const map = new Map<StudioModelBrand, StudioModelItem[]>();
  for (const brand of STUDIO_MODEL_BRAND_ORDER) map.set(brand, []);
  for (const model of STUDIO_MODELS) {
    map.get(model.brand)?.push(model);
  }
  return STUDIO_MODEL_BRAND_ORDER.map((brand) => ({
    brand,
    models: map.get(brand) ?? [],
  })).filter((g) => g.models.length > 0);
}

const LIVE_PRICING: Record<string, FlagshipApiModel["pricing"]> = {
  "qwen3-8b": [
    { label: "输入（灵枢价）", value: "60 积分 / 百万 Token" },
    { label: "输出（灵枢价）", value: "120 积分 / 百万 Token" },
    { label: "能力类型", value: "语言理解" },
  ],
  "qwen-vl": [
    { label: "输入（灵枢价）", value: "150 积分 / 百万 Token" },
    { label: "输出（灵枢价）", value: "300 积分 / 百万 Token" },
    { label: "能力类型", value: "视觉理解" },
  ],
  "deepseek-v3": [
    { label: "输入（灵枢价）", value: "100 积分 / 百万 Token" },
    { label: "输出（灵枢价）", value: "200 积分 / 百万 Token" },
    { label: "能力类型", value: "语言理解" },
  ],
  "deepseek-v4-flash": [
    { label: "输入（灵枢价）", value: "40 积分 / 百万 Token" },
    { label: "输出（灵枢价）", value: "80 积分 / 百万 Token" },
    { label: "能力类型", value: "语言理解 · 高速" },
  ],
  "deepseek-v4": [
    { label: "输入（灵枢价）", value: "120 积分 / 百万 Token" },
    { label: "输出（灵枢价）", value: "240 积分 / 百万 Token" },
    { label: "能力类型", value: "语言理解 · 旗舰" },
  ],
  "doubao-pro": [
    { label: "输入（灵枢价）", value: "120 积分 / 百万 Token" },
    { label: "输出（灵枢价）", value: "240 积分 / 百万 Token" },
    { label: "能力类型", value: "语言理解" },
  ],
  sensevoice: [
    { label: "计费（灵枢价）", value: "50 积分 / 分钟" },
    { label: "能力类型", value: "语音识别 ASR" },
    { label: "供应商", value: "硅基流动" },
  ],
  cosyvoice: [
    { label: "计费（灵枢价）", value: "100 积分 / 万字符" },
    { label: "能力类型", value: "语音合成 TTS" },
    { label: "供应商", value: "硅基流动" },
  ],
};

function capabilityType(badge?: string): string {
  if (badge === "视觉") return "视觉理解";
  if (badge === "语音") return "语音";
  if (badge === "代码") return "代码生成";
  if (badge === "长文本") return "长上下文";
  if (badge === "推理" || badge === "联网") return "深度推理";
  return "语言理解";
}

export function studioModelToFlagship(m: StudioModelItem): FlagshipApiModel {
  const pricing = LIVE_PRICING[m.id] ?? [
    { label: "状态", value: "即将上线" },
    { label: "能力类型", value: capabilityType(m.badge) },
    { label: "供应商", value: VENDOR[m.brand] },
  ];
  return {
    id: m.id,
    name: m.name,
    badge: m.badge,
    description: m.description,
    imageUrl: brandLogo(m.brand),
    imageFallback: brandFavicon(m.brand),
    pricing,
  };
}

export const STUDIO_MODELS: StudioModelItem[] = [
  // Qwen
  { id: "qwen3-7-max", name: "Qwen3-32B", badge: "旗舰", brand: "qwen", description: "通义千问 3 系列 32B，强推理与长上下文（硅基流动）" },
  { id: "qwen3-7-long", name: "Qwen3.7 Long", badge: "长文本", brand: "qwen", description: "200 万超长文档精读与摘要" },
  { id: "qwen3-7-coder", name: "Qwen3.7 Coder", badge: "代码", brand: "qwen", description: "代码专用，支持工程级调试" },
  { id: "qwen3-7-vl-ultra", name: "Qwen3.7-VL Ultra", badge: "视觉", brand: "qwen", description: "新一代多模态，识图 / 图表 / OCR" },
  { id: "qwen3-audio", name: "Qwen3 Audio", badge: "语音", brand: "qwen", description: "原生实时语音对话" },
  { id: "qwen3-8b", name: "Qwen3-8B", badge: "推荐", brand: "qwen", description: "轻量高效，日常对话与办公自动化首选" },
  { id: "qwen-vl", name: "Qwen2.5-VL", badge: "视觉", brand: "qwen", description: "全模态理解，支持图文混合问答" },
  // DeepSeek
  { id: "deepseek-v4", name: "DeepSeek-V4 Pro", badge: "旗舰", brand: "deepseek", description: "V4 旗舰版，复杂推理与深度分析" },
  { id: "deepseek-v4-flash", name: "DeepSeek-V4 Flash", badge: "推荐", brand: "deepseek", description: "V4 高速版，低延迟日常对话" },
  { id: "deepseek-r1", name: "DeepSeek-R1 深度思考版", badge: "推理", brand: "deepseek", description: "强化深度推理，适合复杂解题" },
  { id: "deepseek-coder-v2.5", name: "DeepSeek-Coder V2.5", badge: "代码", brand: "deepseek", description: "超长代码库解析与重构" },
  { id: "deepseek-vl2", name: "DeepSeek-VL2", badge: "视觉", brand: "deepseek", description: "多模态图文理解与问答" },
  { id: "deepseek-v3", name: "DeepSeek-V3", badge: "推理", brand: "deepseek", description: "强推理能力，适合复杂分析与创作" },
  // Doubao
  { id: "doubao-2-pro", name: "Doubao 2.0 Pro", badge: "推荐", brand: "doubao", description: "均衡旗舰，日常创作与办公" },
  { id: "doubao-long-200w", name: "Doubao Long 200W", badge: "长文本", brand: "doubao", description: "百万字长文档精读" },
  { id: "doubao-vl-4", name: "Doubao-VL 4.0", badge: "视觉", brand: "doubao", description: "图文理解、PPT 解析" },
  { id: "doubao-code", name: "Doubao Code", badge: "代码", brand: "doubao", description: "前端 / 后端工程开发" },
  { id: "doubao-pro", name: "Doubao 1.5 Pro", badge: "旗舰", brand: "doubao", description: "火山方舟旗舰模型，综合能力强" },
  // OpenAI
  { id: "gpt-5.5-thinking", name: "GPT-5.5 Thinking", badge: "推理", brand: "openai", description: "深度思考增强版" },
  { id: "gpt-5.5-pro", name: "GPT-5.5 Pro", badge: "旗舰", brand: "openai", description: "综合旗舰，图文 / 音频全能" },
  { id: "gpt-4o-audio-realtime", name: "GPT-4o Audio Realtime", badge: "语音", brand: "openai", description: "实时语音对话" },
  { id: "gpt-5.5-mini-turbo", name: "GPT-5.5 Mini Turbo", badge: "轻量化", brand: "openai", description: "轻量高速，低成本调用" },
  { id: "gpt-4.1", name: "GPT-4.1", badge: "即将上线", brand: "openai", description: "OpenAI 旗舰文本模型" },
  { id: "gpt-4.1-mini", name: "GPT-4.1 mini", badge: "即将上线", brand: "openai", description: "轻量高效，高频对话" },
  { id: "o3", name: "OpenAI o3", badge: "即将上线", brand: "openai", description: "深度推理系列旗舰" },
  { id: "o4-mini", name: "OpenAI o4-mini", badge: "即将上线", brand: "openai", description: "新一代轻量推理" },
  // Claude
  { id: "claude-opus-4.5", name: "Claude Opus 4.5", badge: "旗舰", brand: "claude", description: "2026 新旗舰，百万上下文，复杂文档分析" },
  { id: "claude-sonnet-4.5", name: "Claude Sonnet 4.5", badge: "推荐", brand: "claude", description: "均衡性价比，日常主力" },
  { id: "claude-haiku-4.5-flash", name: "Claude Haiku 4.5 Flash", badge: "轻量化", brand: "claude", description: "极速轻量，低 Token 消耗" },
  { id: "claude-opus-4", name: "Claude Opus 4", badge: "即将上线", brand: "claude", description: "Anthropic 旗舰，长文档与复杂写作" },
  { id: "claude-sonnet-4", name: "Claude Sonnet 4", badge: "即将上线", brand: "claude", description: "均衡之选，企业知识问答" },
  { id: "claude-3.7-sonnet", name: "Claude 3.7 Sonnet", badge: "即将上线", brand: "claude", description: "混合推理，分析与创作兼顾" },
  // Grok
  { id: "grok-4.5-expert", name: "Grok 4.5 Expert", badge: "联网", brand: "grok", description: "实时联网深度分析" },
  { id: "grok-4.5-auto", name: "Grok 4.5 Auto", badge: "推荐", brand: "grok", description: "自动切换快慢模式" },
  { id: "grok-4.5-fast", name: "Grok 4.5 Fast", badge: "轻量化", brand: "grok", description: "极速响应，低成本" },
  { id: "grok-4.3", name: "Grok 4.3", badge: "即将上线", brand: "grok", description: "xAI 旗舰对话模型" },
  { id: "grok-4.3-mini", name: "Grok 4.3 mini", badge: "即将上线", brand: "grok", description: "低延迟轻量版" },
  // Gemini
  { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", badge: "即将上线", brand: "gemini", description: "Google 旗舰多模态，长上下文推理" },
  { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", badge: "即将上线", brand: "gemini", description: "高速版，大规模对话" },
  { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", badge: "即将上线", brand: "gemini", description: "轻量高速，实时对话" },
  // Voice
  { id: "sensevoice", name: "SenseVoice", badge: "语音", brand: "audio", description: "高精度语音识别，多语种转写" },
  { id: "cosyvoice", name: "CosyVoice", badge: "语音", brand: "audio", description: "自然流畅语音合成，多音色" },
];

const FLAGSHIP_EXTRAS: FlagshipApiModel[] = [
  {
    id: "qwen-72b",
    name: "Qwen2.5-72B",
    badge: "旗舰",
    imageUrl: brandLogo("qwen"),
    imageFallback: brandFavicon("qwen"),
    description: "大规模文本模型，擅长复杂推理、长文档理解与专业写作。",
    pricing: [
      { label: "输入（灵枢价）", value: "200 积分 / 百万 Token" },
      { label: "输出（灵枢价）", value: "400 积分 / 百万 Token" },
      { label: "能力类型", value: "语言理解" },
    ],
  },
  {
    id: "glm-4",
    name: "GLM-4-9B",
    badge: "语言",
    imageUrl: "https://unpkg.com/@lobehub/icons-static-png@1.49.0/light/zhipu-color.png",
    imageFallback: "https://www.google.com/s2/favicons?domain=zhipuai.cn&sz=256",
    description: "智谱 GLM 系列，中文理解出色，适合办公文案与知识问答。",
    pricing: [
      { label: "输入（灵枢价）", value: "80 积分 / 百万 Token" },
      { label: "输出（灵枢价）", value: "160 积分 / 百万 Token" },
      { label: "能力类型", value: "语言理解" },
    ],
  },
  {
    id: "doubao-lite",
    name: "Doubao Lite",
    badge: "高性价比",
    imageUrl: brandLogo("doubao"),
    imageFallback: brandFavicon("doubao"),
    description: "火山方舟高性价比模型，长上下文、响应快。",
    pricing: [
      { label: "输入（灵枢价）", value: "30 积分 / 百万 Token" },
      { label: "输出（灵枢价）", value: "60 积分 / 百万 Token" },
      { label: "能力类型", value: "语言理解" },
    ],
  },
  {
    id: "doubao-vision",
    name: "Doubao Vision",
    badge: "视觉",
    imageUrl: brandLogo("doubao"),
    imageFallback: brandFavicon("doubao"),
    description: "火山方舟视觉模型，图像理解、OCR 与多模态问答。",
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
    imageFallback: brandFavicon("doubao"),
    description: "文本向量化，语义检索与知识库匹配。",
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
    imageFallback: brandFavicon("doubao"),
    description: "火山方舟语音合成，多种音色可选。",
    pricing: [
      { label: "计费（灵枢价）", value: "80 积分 / 万字符" },
      { label: "能力类型", value: "语音合成 TTS" },
      { label: "供应商", value: "火山方舟" },
    ],
  },
];

export function buildFlagshipApiModels(): FlagshipApiModel[] {
  const studioIds = new Set(STUDIO_MODELS.map((m) => m.id));
  return [...STUDIO_MODELS.map(studioModelToFlagship), ...FLAGSHIP_EXTRAS.filter((e) => !studioIds.has(e.id))];
}
