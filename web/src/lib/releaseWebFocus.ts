/** 桌面任务执行后避免 Hub 网页抢回系统焦点 */
export function releaseWebFocus() {
  const active = document.activeElement;
  if (active instanceof HTMLElement && active !== document.body) {
    active.blur();
  }
  try {
    window.blur();
  } catch {
    // ignore
  }
}
