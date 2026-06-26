"""成就分享卡片 PNG."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from sensehub.util.qr_png import qr_png_bytes

_CARD_W = 720
_CARD_H = 960


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\msyhbd.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    )
    for path in candidates:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in (text or "").split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        buf = ""
        for ch in paragraph:
            trial = buf + ch
            if draw.textlength(trial, font=font) <= max_width:
                buf = trial
            else:
                if buf:
                    lines.append(buf)
                buf = ch
        if buf:
            lines.append(buf)
    return lines or [""]


def render_achievement_share_card(
    *,
    display_name: str,
    public_id: str,
    achievement_name: str,
    achievement_desc: str,
    level: int,
    rating_name: str,
    share_url: str,
) -> bytes:
    img = Image.new("RGB", (_CARD_W, _CARD_H), "#0f1117")
    draw = ImageDraw.Draw(img)

    for y in range(_CARD_H):
        t = y / _CARD_H
        r = int(15 + (99 - 15) * t)
        g = int(17 + (102 - 17) * t)
        b = int(23 + (241 * 0.35 - 23) * t)
        draw.line([(0, y), (_CARD_W, y)], fill=(r, g, b))

    gold = "#c9a96e"
    draw.rounded_rectangle((40, 48, _CARD_W - 40, _CARD_H - 48), radius=28, outline=gold, width=3)

    title_font = _load_font(34)
    name_font = _load_font(44)
    body_font = _load_font(26)
    meta_font = _load_font(22)
    brand_font = _load_font(24)

    draw.text((_CARD_W // 2, 96), "灵枢 SenseHub", fill=gold, font=brand_font, anchor="mt")
    draw.text((_CARD_W // 2, 148), "成就勋章", fill="#e5e7eb", font=title_font, anchor="mt")

    badge_cy = 300
    draw.ellipse((280, badge_cy - 80, 440, badge_cy + 80), fill="#1f2937", outline=gold, width=4)
    draw.text((_CARD_W // 2, badge_cy), "★", fill=gold, font=_load_font(72), anchor="mm")

    ach_name = (achievement_name or "成就").strip()[:20]
    draw.text((_CARD_W // 2, 420), ach_name, fill="#ffffff", font=name_font, anchor="mt")

    desc_lines = _wrap_text(draw, (achievement_desc or "").strip()[:120], body_font, _CARD_W - 160)
    y = 500
    for line in desc_lines[:3]:
        draw.text((_CARD_W // 2, y), line, fill="#9ca3af", font=body_font, anchor="mt")
        y += 36

    user = (display_name or public_id or "灵枢用户").strip()[:24]
    draw.text((_CARD_W // 2, 640), f"获得者 · {user}", fill="#d1d5db", font=meta_font, anchor="mt")
    draw.text(
        (_CARD_W // 2, 682),
        f"Lv.{max(1, int(level))} · {rating_name or '—'}",
        fill=gold,
        font=meta_font,
        anchor="mt",
    )

    qr_size = 168
    qr_raw = qr_png_bytes(share_url, box_size=6, border=2)
    qr_img = Image.open(io.BytesIO(qr_raw)).convert("RGB").resize((qr_size, qr_size), Image.Resampling.NEAREST)
    qr_x = (_CARD_W - qr_size) // 2
    qr_y = _CARD_H - 48 - qr_size - 56
    draw.rounded_rectangle((qr_x - 12, qr_y - 12, qr_x + qr_size + 12, qr_y + qr_size + 12), radius=12, fill="#ffffff")
    img.paste(qr_img, (qr_x, qr_y))
    draw.text((_CARD_W // 2, qr_y + qr_size + 20), "扫码查看成就", fill="#6b7280", font=meta_font, anchor="mt")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
