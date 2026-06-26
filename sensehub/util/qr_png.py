"""二维码 PNG 生成."""

from __future__ import annotations

import io

import qrcode


def qr_png_bytes(data: str, *, box_size: int = 8, border: int = 2) -> bytes:
    text = (data or "").strip()
    if not text:
        raise ValueError("二维码内容不能为空")
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=max(4, min(box_size, 16)),
        border=max(1, min(border, 6)),
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#111827", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
