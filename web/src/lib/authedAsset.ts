import { getToken, clearToken } from "@/lib/api";

let unauthorizedHandler: (() => void) | null = null;

export function setAuthedAssetUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

function onUnauthorized() {
  clearToken();
  if (unauthorizedHandler) unauthorizedHandler();
  else window.location.href = "/login";
}

/** 带 JWT 拉取二进制资源，返回 object URL（调用方应在适当时机 revokeObjectURL）. */
export async function fetchAuthedBlobUrl(path: string): Promise<string> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { headers });
  if (res.status === 401) {
    onUnauthorized();
    throw new Error("未登录");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    const msg =
      typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : res.statusText;
    throw new Error(msg || "请求失败");
  }
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export function siteOrigin(): string {
  if (typeof window !== "undefined" && window.location?.origin) {
    return window.location.origin;
  }
  return "";
}
