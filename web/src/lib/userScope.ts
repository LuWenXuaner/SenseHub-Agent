/** 按登录用户隔离 localStorage 会话缓存键 */

export function userStorageScope(username?: string | null): string {
  const u = username?.trim().toLowerCase();
  return u || "guest";
}
