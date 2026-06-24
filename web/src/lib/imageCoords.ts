/** 将点击坐标转换为图像自然像素坐标（object-contain 布局）. */
export function clickToImageCoords(
  clientX: number,
  clientY: number,
  el: HTMLImageElement | HTMLCanvasElement
): [number, number] | null {
  const rect = el.getBoundingClientRect();
  const nw = el instanceof HTMLCanvasElement ? el.width : el.naturalWidth;
  const nh = el instanceof HTMLCanvasElement ? el.height : el.naturalHeight;
  if (!nw || !nh) return null;

  const scale = Math.min(rect.width / nw, rect.height / nh);
  const dw = nw * scale;
  const dh = nh * scale;
  const ox = (rect.width - dw) / 2;
  const oy = (rect.height - dh) / 2;

  const x = (clientX - rect.left - ox) / scale;
  const y = (clientY - rect.top - oy) / scale;
  if (x < 0 || y < 0 || x > nw || y > nh) return null;
  return [x, y];
}
