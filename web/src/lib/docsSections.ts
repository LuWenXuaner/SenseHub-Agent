/** 文档中心正文（按锚点 id 组织） */

export type DocBlock = {
  paragraphs: string[];
  bullets?: string[];
  steps?: string[];
  code?: string;
  note?: string;
  link?: { label: string; to: string };
};

export type DocSectionMap = Record<string, DocBlock>;

const zh: DocSectionMap = {
  start: {
    paragraphs: [
      "灵枢提供 OpenAI 兼容的 Chat Completions 接口。您在控制台配置 Provider 密钥并兑换 Token Plan 后，即可用任意 HTTP 客户端或 SDK 调用代采模型。",
      "Base URL 与专属 Token Plan Key 可在「Token Plan」页复制；也可使用自有硅基流动 / 火山方舟密钥走「API Keys」页配置。",
    ],
    steps: [
      "注册并登录灵枢 SenseHub，进入控制台 → API Keys，填写硅基流动或火山方舟 Base URL 与 API Key。",
      "在积分中心签到或兑换 Token Plan / API 额度，确保账户有足够积分与档位权益。",
      "使用标准 POST /v1/chat/completions 发起请求，model 字段填写文档或模型页所示的模型 ID。",
      "在 Token Plan 或账单明细中查看 Token 消耗与流控配额。",
    ],
    code: `curl https://api.siliconflow.cn/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "Qwen/Qwen3-8B",
    "messages": [{"role": "user", "content": "你好"}]
  }'`,
    link: { label: "前往配置 API Key", to: "/console/api-keys" },
  },
  text: {
    paragraphs: [
      "文本生成适用于对话、写作、摘要、翻译与代码补全。灵枢默认路由 Qwen3、DeepSeek-V3、Doubao 等模型，按角色脑（intent / planner / coder）自动选型。",
      "Studio Chat 与 Console 均基于同一套文本能力：Chat 为纯对话，Console 可进一步触发工具执行与任务规划。",
    ],
    bullets: [
      "支持多轮对话与 system 提示词",
      "支持 temperature、max_tokens 等标准参数",
      "Pro / Max 档位可用更强规划与多脑协作模型",
    ],
    code: `{
  "model": "Qwen/Qwen3-8B",
  "messages": [
    {"role": "system", "content": "你是专业写作助手"},
    {"role": "user", "content": "写一段产品简介"}
  ],
  "temperature": 0.7
}`,
    link: { label: "打开灵枢 Chat", to: "/studio" },
  },
  tools: {
    paragraphs: [
      "工具调用（Function Calling）让模型在对话中结构化输出工具名与参数，由灵枢 Console 执行浏览器、文件、虚拟屏等能力。",
      "Console 会将用户自然语言先经意图脑分类，再生成 ExecutionPlan，逐步调用已注册工具并在界面展示执行过程。",
    ],
    bullets: [
      "wait_confirm：涉及敏感路径时暂停等待用户确认",
      "multi_agent：Max 档位支持多脑协作与自主 Agent",
      "可在插件管理页查看已开通的联网、语音等扩展能力",
    ],
    link: { label: "体验灵枢 Console", to: "/claw" },
  },
  vision: {
    paragraphs: [
      "视觉理解使用 Qwen2.5-VL 等 VLM，对截图、照片或 UI 界面进行 OCR、元素定位与图文问答。",
      "Console 开启摄像头后，可将实时帧送入视觉脑，用于 GUI Agent 与虚拟屏操作验证。",
    ],
    bullets: [
      "输入：base64 图片或 URL（视 Provider 支持而定）",
      "适用：截图问答、表格抽取、界面元素描述",
      "Pro 及以上档位可在 Console 状态栏开启视觉模式",
    ],
    link: { label: "查看模型列表", to: "/models" },
  },
  image: {
    paragraphs: [
      "图片理解是多模态能力的核心场景：单张或多张图片与文本混合输入，模型返回对画面内容的自然语言描述或结构化答案。",
      "推荐在请求中使用 user 消息中的 image_url 或 content 数组（OpenAI 视觉消息格式）。",
    ],
    bullets: [
      "支持 PNG / JPEG / WebP 等常见格式",
      "长图建议压缩后上传，单张建议小于 4MB",
      "Console 视觉模式会自动截取当前画面并送入 VLM",
    ],
    code: `{
  "model": "Qwen/Qwen2.5-VL-7B-Instruct",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "描述这张图片"},
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    ]
  }]
}`,
  },
  audio: {
    paragraphs: [
      "音频理解面向语音片段的内容分析：可结合 ASR 转写结果或直接（在模型支持时）对音频特征进行问答。",
      "典型场景包括会议摘要、客服质检、播客章节标注等。",
    ],
    bullets: [
      "Studio / Console 按住麦克风即可录音并转写",
      "转写文本可继续送入文本模型做摘要或翻译",
      "长音频建议先切片再分批处理",
    ],
  },
  voice: {
    paragraphs: [
      "语音识别（ASR）将用户语音转为文本，是 Console 语音指令与 Studio 语音输入的基础能力。",
      "灵枢集成 SenseVoice 等引擎，支持中文普通话及多种方言场景（以实际部署配置为准）。",
    ],
    bullets: [
      "Console：唤醒词「灵枢」后可说出完整指令",
      "Studio：输入框旁麦克风按钮，松手即发送转写结果",
      "音频格式：浏览器端通常为 webm/opus，服务端自动转换",
    ],
    link: { label: "Console 语音说明", to: "/claw" },
  },
  asr: {
    paragraphs: [
      "SenseVoice 提供高精度、低延迟的流式与非流式识别，适合实时对话与长语音文件转写。",
      "调用方式：Console / Studio 内置；API 用户可通过 /api/voice/transcribe 等端点上传音频（需登录与相应档位）。",
    ],
    bullets: [
      "支持标点恢复与语气词过滤",
      "噪声环境建议靠近麦克风或使用耳机",
      "识别结果会写入会话上下文供后续模型使用",
    ],
  },
  tts: {
    paragraphs: [
      "语音合成（TTS）将模型回复或任务摘要转为自然语音，用于 Console 执行反馈与无障碍场景。",
      "CosyVoice / Doubao TTS 支持多音色；Max 档位可开启任务完成后的自动播报。",
    ],
    bullets: [
      "在 Console 执行完成后可选朗读摘要",
      "可在插件管理中开通 TTS 插件",
      "积分可兑换 TTS 字符额度包",
    ],
    link: { label: "兑换 TTS 额度", to: "/console/points" },
  },
  faq: {
    paragraphs: [
      "以下为文档中心常见问题摘要；更多账户、法务问题请见页脚链接或联系我们。",
    ],
    bullets: [
      "账户与认证：个人中心可查看灵枢 ID、档位；API Key 请勿泄露或提交至公开仓库。",
      "积分与兑换：每日签到、邀请好友得积分；可兑换 Lite/Pro/Max 档位与 API 额度。",
      "限速说明：各档位有 Token 流控与并发上限，详见模型页与 Token Plan 用量面板。",
      "Code Agent：在 Code 工作台选择本地项目根目录，通过 Agent 对话直接修改文件（需 Chrome/Edge）。",
    ],
    link: { label: "联系支持", to: "/contact" },
  },
};

const en: DocSectionMap = {
  start: {
    paragraphs: [
      "SenseHub exposes OpenAI-compatible Chat Completions. Configure provider keys and redeem a Token Plan to call resold models from any HTTP client or SDK.",
      "Copy Base URL and Token Plan key from Token Plan, or use your own SiliconFlow / Volcengine keys under API Keys.",
    ],
    steps: [
      "Sign in → Console → API Keys: set Base URL and API Key.",
      "Check in or redeem points for Token Plan / API quota.",
      "POST /v1/chat/completions with the model ID from docs or Models page.",
      "Track usage under Token Plan or Bills.",
    ],
    code: `curl https://api.siliconflow.cn/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"Qwen/Qwen3-8B","messages":[{"role":"user","content":"Hello"}]}'`,
    link: { label: "Configure API Keys", to: "/console/api-keys" },
  },
  text: {
    paragraphs: [
      "Text generation covers chat, writing, summarization, translation, and code. SenseHub routes Qwen3, DeepSeek-V3, Doubao by brain role (intent / planner / coder).",
      "Studio Chat is dialog-only; Console can plan and execute tools on top of the same models.",
    ],
    bullets: ["Multi-turn + system prompts", "Standard temperature / max_tokens", "Stronger models on Pro / Max"],
    link: { label: "Open Chat", to: "/studio" },
  },
  tools: {
    paragraphs: [
      "Tool calling lets models emit structured tool names and args; Console runs browser, file, virtual screen tools from an ExecutionPlan.",
      "Sensitive steps pause at wait_confirm until you approve.",
    ],
    bullets: ["wait_confirm for protected paths", "Multi-agent on Max tier", "Plugins for web search & voice"],
    link: { label: "Try Console", to: "/claw" },
  },
  vision: {
    paragraphs: [
      "Vision uses Qwen2.5-VL for screenshots, OCR, UI understanding. Enable camera in Console for live frames.",
    ],
    bullets: ["Base64 or URL images", "Screenshot Q&A & table extract", "Vision toggle in Console status bar (Pro+)"],
    link: { label: "Models", to: "/models" },
  },
  image: {
    paragraphs: [
      "Image understanding mixes one or more images with text; models return descriptions or answers about visual content.",
    ],
    bullets: ["PNG / JPEG / WebP", "Keep images under ~4MB when possible", "Console vision sends live frames to VLM"],
    code: `{"model":"Qwen/Qwen2.5-VL-7B-Instruct","messages":[{"role":"user","content":[{"type":"text","text":"Describe this"},{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}]}]}`,
  },
  audio: {
    paragraphs: [
      "Audio understanding covers spoken content analysis—often paired with ASR transcripts for summarization or QA.",
    ],
    bullets: ["Hold-to-talk in Studio / Console", "Chain ASR → text model for summaries", "Split long audio before batching"],
  },
  voice: {
    paragraphs: [
      "ASR converts speech to text for Console voice commands and Studio mic input.",
    ],
    bullets: ["Wake word in Console", "Mic button in Studio", "Typical browser audio: webm/opus"],
    link: { label: "Console", to: "/claw" },
  },
  asr: {
    paragraphs: [
      "SenseVoice offers accurate transcription for realtime and file upload flows.",
    ],
    bullets: ["Punctuation restore", "Use a clear mic in noisy rooms", "Transcripts feed session context"],
  },
  tts: {
    paragraphs: [
      "TTS speaks replies or task summaries—useful for Console feedback and accessibility.",
    ],
    bullets: ["Optional speak-after-task on Max", "TTS plugin in plugin center", "Redeem TTS quota with points"],
    link: { label: "Redeem points", to: "/console/points" },
  },
  faq: {
    paragraphs: ["Quick FAQ summary—see Contact for more."],
    bullets: [
      "Account: profile & tier in console; never leak API keys.",
      "Points: check-in, invites, redeem tiers & API packs.",
      "Rate limits: per tier—see Models & Token Plan.",
      "Code Agent: pick a local folder in Code and edit via Agent chat.",
    ],
    link: { label: "Contact", to: "/contact" },
  },
};

export function getDocSection(locale: "zh" | "en", id: string): DocBlock | undefined {
  const map = locale === "zh" ? zh : en;
  return map[id];
}

export const DOC_SECTION_IDS = [
  "start",
  "text",
  "tools",
  "vision",
  "image",
  "audio",
  "voice",
  "asr",
  "tts",
  "faq",
] as const;
