import type { Locale, MessageTree } from "./types";
import { zh } from "./zh";
import { en } from "./en";

export type { Locale, MessageTree };

export const MESSAGES: Record<Locale, MessageTree> = { zh, en };

export function getMessage(locale: Locale): MessageTree {
  return MESSAGES[locale];
}

/** Replace `{key}` placeholders in translated strings */
export function formatMsg(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? ""));
}
