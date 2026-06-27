/** 当前页面是否在本机访问 SenseHub（非局域网远程客户端） */
export function isLocalSenseHubHost(): boolean {
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1" || host === "[::1]" || host === "::1";
}
