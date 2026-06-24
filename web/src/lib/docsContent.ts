import type { MessageTree } from "@/lib/i18n/types";

export type DocsNavItem = {
  id: string;
  label: string;
  to?: string;
  children?: { id: string; label: string; to?: string }[];
};

export function getDocsNav(t: MessageTree): DocsNavItem[] {
  const d = t.docsPage;
  return [
    {
      id: "welcome",
      label: d.navWelcome,
      children: [
        { id: "start", label: d.navFirstApi, to: "/product/api#start" },
        { id: "models", label: d.navModelList, to: "/models" },
      ],
    },
    {
      id: "guide",
      label: d.navGuide,
      children: [
        { id: "text", label: d.navText, to: "/product/api#text" },
        { id: "tools", label: d.navTools, to: "/product/api#tools" },
        { id: "vision", label: d.navVision, to: "/product/api#vision" },
        { id: "voice", label: d.navVoice, to: "/product/api#voice" },
      ],
    },
    {
      id: "multimodal",
      label: d.navMultimodal,
      children: [
        { id: "image", label: d.navImage, to: "/product/api#image" },
        { id: "audio", label: d.navAudio, to: "/product/api#audio" },
      ],
    },
    {
      id: "speech",
      label: d.navSpeech,
      children: [
        { id: "asr", label: d.navAsr, to: "/product/api#asr" },
        { id: "tts", label: d.navTts, to: "/product/api#tts" },
      ],
    },
    {
      id: "faq",
      label: d.navFaq,
      children: [
        { id: "account", label: d.navAccount, to: "/contact" },
        { id: "billing", label: d.navBilling, to: "/product/api#faq" },
      ],
    },
  ];
}

export function getDocsQuickStart(t: MessageTree) {
  const d = t.docsPage;
  return [
    { id: "start", title: d.quickStart, desc: d.quickStartDesc, to: "/product/api#start", icon: "zap" as const },
    { id: "console", title: t.console.title, desc: d.quickConsoleDesc, to: "/console/api-keys", icon: "grid" as const },
    { id: "token", title: t.console.tokenPlan, desc: d.quickTokenDesc, to: "/console/points", icon: "coin" as const },
    { id: "code", title: t.claw.title, desc: d.quickClawDesc, to: "/claw", icon: "code" as const },
    { id: "pricing", title: d.quickPricing, desc: d.quickPricingDesc, to: "/models", icon: "tag" as const },
    { id: "faq", title: d.navFaq, desc: d.quickFaqDesc, to: "/contact", icon: "help" as const },
  ];
}

export function getDocsHeroSlides(t: MessageTree) {
  const d = t.docsPage;
  return [
    {
      title: d.hero1Title,
      desc: d.hero1Desc,
      primary: { label: d.heroCta, to: "/console/points" },
      secondary: { label: d.heroSecondary, to: "/console/token-plan" },
    },
    {
      title: d.hero2Title,
      desc: d.hero2Desc,
      primary: { label: d.heroCta, to: "/claw" },
      secondary: { label: d.heroDocs, to: "/product/api#start" },
    },
  ];
}

/** @deprecated use getDocsNav */
export const DOCS_NAV: DocsNavItem[] = [];

/** @deprecated use getDocsQuickStart */
export const DOCS_QUICK_START = [] as const;

/** @deprecated use getDocsHeroSlides */
export const DOCS_HERO_SLIDES = [] as const;
